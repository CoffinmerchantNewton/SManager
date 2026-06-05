#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from lib.diagnostics import diagnose as diagnose_run
from lib.fnl import scan_fnl
from lib.jsonio import read_json, read_jsonl, write_json_atomic
from lib.paths import FlowPaths
from lib.preflight import run_preflight
from lib.slurm import cancel_job, node_script, sbatch_available, scancel_available, submit_sbatch
from lib.state import (
    initialize_run,
    list_runs,
    load_node_status,
    load_spec,
    load_workflow,
    node_names,
    refresh_workflow,
    update_node_status,
    write_event,
)
from lib.timeutils import default_run_id, now_iso, parse_cycle


DEFAULT_NODES = [
    "fnl_verify",
    "wps_geogrid",
    "wps_ungrib",
    "wps_metgrid",
    "wrf_setup",
    "real",
    "compute_gdd",
    "prep_pollen",
    "wrf_run",
    "postprocess_eval",
    "product_extract",
    "package_products",
]


def paths() -> FlowPaths:
    return FlowPaths.from_env(SCRIPT_DIR)


def print_json(data: Any) -> None:
    json.dump(data, sys.stdout, ensure_ascii=False, indent=2, sort_keys=True)
    sys.stdout.write("\n")


def load_command_config(path: str | None) -> dict[str, Any]:
    if not path:
        return {}
    config_path = Path(path)
    if not config_path.is_file():
        raise FileNotFoundError(f"commands file not found: {config_path}")
    data = read_json(config_path, default={})
    if not isinstance(data, dict):
        raise ValueError("commands file must contain a JSON object")
    return data


def build_spec(args) -> dict[str, Any]:
    start = parse_cycle(args.start)
    end = parse_cycle(args.end)
    if end < start:
        raise ValueError("--end must be >= --start")
    variant = args.variant or "official"
    domain = args.domain or "neimeng"
    run_id = args.run_id or default_run_id(start, args.period, domain, variant)
    command_config = load_command_config(args.commands_file)
    global_env = command_config.get("env", {})
    slurm_defaults = command_config.get("slurm_defaults", {})
    configured_nodes = command_config.get("nodes", {})
    nodes = []
    for name in DEFAULT_NODES:
        config = configured_nodes.get(name, {})
        env = dict(global_env)
        env.update(config.get("env", {}))
        slurm = dict(slurm_defaults)
        slurm.update(config.get("slurm", {}))
        nodes.append(
            {
                "name": name,
                "command": config.get("command"),
                "cwd": config.get("cwd"),
                "env": env,
                "slurm": slurm,
            }
        )
    return {
        "version": 1,
        "run_id": run_id,
        "start": args.start,
        "end": args.end,
        "period": args.period,
        "domain": domain,
        "variant": variant,
        "met_provider": args.met_provider,
        "created_at": now_iso(),
        "nodes": nodes,
        "command_config_path": args.commands_file,
    }


def cmd_plan(args) -> int:
    flow_paths = paths()
    spec = build_spec(args)
    initialize_run(flow_paths, spec)
    print_json({"ok": True, "run_id": spec["run_id"], "run_dir": str(flow_paths.run_dir(spec["run_id"]))})
    return 0


def cmd_list(args) -> int:
    print_json({"runs": list_runs(paths())})
    return 0


def cmd_status(args) -> int:
    flow_paths = paths()
    data = refresh_workflow(flow_paths, args.run_id)
    if args.json:
        print_json(data)
    else:
        print(f"{data['run_id']} {data['status']} {data['progress']}%")
        for node in data.get("nodes", []):
            print(f"  {node['node']:<18} {node['status']:<10} {node.get('message') or ''}")
    return 0


def cmd_fnl_verify(args) -> int:
    flow_paths = paths()
    if args.run_id:
        spec = load_spec(flow_paths, args.run_id)
        start = parse_cycle(spec["start"])
        end = parse_cycle(spec["end"])
        run_id = args.run_id
    else:
        start = parse_cycle(args.start)
        end = parse_cycle(args.end)
        run_id = None
    manifest = scan_fnl(start, end)
    if run_id:
        write_json_atomic(flow_paths.fnl_manifest(run_id), manifest)
        status = "success" if manifest["ok"] else "error"
        message = "FNL verified" if manifest["ok"] else "FNL missing or invalid"
        update_node_status(
            flow_paths,
            run_id,
            "fnl_verify",
            status,
            message,
            progress=100 if manifest["ok"] else 0,
            error_code=None if manifest["ok"] else "fnl_missing",
            outputs=[str(flow_paths.fnl_manifest(run_id))],
        )
    print_json(manifest)
    return 0 if manifest["ok"] else 2


def node_by_name(spec: dict[str, Any], name: str) -> dict[str, Any]:
    for node in spec.get("nodes", []):
        if node["name"] == name:
            return node
    raise KeyError(f"node not found: {name}")


def cmd_submit(args) -> int:
    flow_paths = paths()
    spec = load_spec(flow_paths, args.run_id)
    if args.dry_run or not sbatch_available():
        write_event(
            flow_paths,
            args.run_id,
            "submit_dry_run",
            "sbatch unavailable or dry-run requested",
            payload={"sbatch_available": sbatch_available(), "dry_run": args.dry_run},
        )
        print_json({"ok": True, "dry_run": True, "sbatch_available": sbatch_available(), "run_id": args.run_id})
        return 0
    missing = [node["name"] for node in spec.get("nodes", []) if not node.get("command")]
    if missing and not args.allow_noop:
        print_json(
            {
                "ok": False,
                "error": "node_commands_missing",
                "message": "Some node commands are not configured. Pass --allow-noop to mark them skipped.",
                "missing_nodes": missing,
            }
        )
        return 2
    previous_job = None
    submitted = []
    for idx, node in enumerate(spec.get("nodes", []), start=1):
        name = node["name"]
        if not node.get("command"):
            update_node_status(
                flow_paths,
                args.run_id,
                name,
                "skipped",
                "node command is not configured",
                progress=100,
                error_code="node_command_missing",
            )
            continue
        script_path = flow_paths.slurm_dir(args.run_id) / f"{idx:02d}_{name}.sbatch"
        node_script(script_path, Path(__file__).resolve(), args.run_id, name, node, flow_paths.logs_dir(args.run_id))
        job_id = submit_sbatch(script_path, dependency=previous_job)
        previous_job = job_id
        submitted.append({"node": name, "job_id": job_id, "script": str(script_path)})
        update_node_status(flow_paths, args.run_id, name, "ready", "submitted to Slurm", slurm_job_id=job_id)
    print_json({"ok": True, "run_id": args.run_id, "submitted": submitted})
    return 0


def cmd_run_node(args) -> int:
    flow_paths = paths()
    spec = load_spec(flow_paths, args.run_id)
    node = node_by_name(spec, args.node)
    command = node.get("command")
    log_path = flow_paths.logs_dir(args.run_id) / f"{args.node}.log"
    update_node_status(
        flow_paths,
        args.run_id,
        args.node,
        "running",
        "node command running",
        progress=1,
        log_files=[str(log_path)],
    )
    if not command:
        update_node_status(
            flow_paths,
            args.run_id,
            args.node,
            "error",
            "node command is not configured",
            progress=0,
            error_code="node_command_missing",
            log_files=[str(log_path)],
        )
        return 2
    cwd = Path(node.get("cwd") or flow_paths.run_dir(args.run_id))
    env = os.environ.copy()
    env.update({str(k): str(v) for k, v in node.get("env", {}).items()})
    env.update({"RUN_ID": args.run_id, "FLOW_RUN_DIR": str(flow_paths.run_dir(args.run_id))})
    with log_path.open("a", encoding="utf-8") as log:
        log.write(f"===== {args.node} start {now_iso()} =====\n")
        result = subprocess.run(command, shell=True, cwd=cwd, env=env, stdout=log, stderr=subprocess.STDOUT)
        log.write(f"===== {args.node} end {now_iso()} code={result.returncode} =====\n")
    if result.returncode == 0:
        update_node_status(
            flow_paths,
            args.run_id,
            args.node,
            "success",
            "node command completed",
            progress=100,
            log_files=[str(log_path)],
        )
    else:
        update_node_status(
            flow_paths,
            args.run_id,
            args.node,
            "error",
            f"node command failed with code {result.returncode}",
            progress=0,
            error_code="node_command_failed",
            log_files=[str(log_path)],
        )
    return result.returncode


def cmd_logs(args) -> int:
    flow_paths = paths()
    log_dir = flow_paths.logs_dir(args.run_id)
    if args.node:
        candidates = sorted(log_dir.glob(f"{args.node}*"))
    else:
        candidates = sorted(log_dir.glob("*"))
    if not candidates:
        print("")
        return 0
    for path in candidates:
        if not path.is_file():
            continue
        if len(candidates) > 1:
            print(f"===== {path.name} =====")
        print_tail(path, args.tail)
    return 0


def cmd_events(args) -> int:
    events = read_jsonl(paths().events(args.run_id), default=[])
    if args.node:
        events = [event for event in events if event.get("node") == args.node]
    if args.level:
        events = [event for event in events if event.get("level") == args.level]
    if args.event_type:
        events = [event for event in events if event.get("event_type") == args.event_type]
    if args.tail:
        events = events[-args.tail :]
    print_json({"ok": True, "run_id": args.run_id, "count": len(events), "events": events})
    return 0


def print_tail(path: Path, lines: int) -> None:
    text = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    for line in text[-lines:]:
        print(line)


def cmd_diagnose(args) -> int:
    print_json(diagnose_run(paths(), args.run_id))
    return 0


def cmd_retry(args) -> int:
    flow_paths = paths()
    spec = load_spec(flow_paths, args.run_id)
    node = node_by_name(spec, args.node)
    if args.dry_run or not sbatch_available():
        write_event(
            flow_paths,
            args.run_id,
            "retry_dry_run",
            "retry dry-run requested",
            node=args.node,
            payload={"sbatch_available": sbatch_available(), "dry_run": args.dry_run},
        )
        print_json(
            {
                "ok": True,
                "dry_run": True,
                "sbatch_available": sbatch_available(),
                "run_id": args.run_id,
                "node": args.node,
                "message": "retry validated; sbatch not executed",
            }
        )
        return 0
    script_path = flow_paths.slurm_dir(args.run_id) / f"retry_{args.node}.sbatch"
    node_script(script_path, Path(__file__).resolve(), args.run_id, args.node, node, flow_paths.logs_dir(args.run_id))
    job_id = submit_sbatch(script_path)
    update_node_status(flow_paths, args.run_id, args.node, "ready", "retry submitted to Slurm", slurm_job_id=job_id)
    print_json({"ok": True, "node": args.node, "job_id": job_id})
    return 0


def cmd_cancel(args) -> int:
    flow_paths = paths()
    spec = load_spec(flow_paths, args.run_id)
    active_nodes = []
    job_ids = []
    for node in node_names(spec):
        status = load_node_status(flow_paths, args.run_id, node)
        if status.get("status") in {"success", "error", "skipped", "cancelled"}:
            continue
        item = {
            "node": node,
            "status": status.get("status"),
            "slurm_job_id": status.get("slurm_job_id"),
        }
        active_nodes.append(item)
        if status.get("slurm_job_id"):
            job_ids.append(str(status["slurm_job_id"]))

    if args.dry_run:
        print_json({"ok": True, "dry_run": True, "run_id": args.run_id, "nodes": active_nodes, "job_ids": job_ids})
        return 0

    if not active_nodes:
        print_json({"ok": True, "run_id": args.run_id, "no_op": True, "message": "no active nodes to cancel"})
        return 0

    if job_ids and not scancel_available():
        print_json(
            {
                "ok": False,
                "error": "scancel_unavailable",
                "message": "Active Slurm job ids exist, but scancel is not available.",
                "job_ids": job_ids,
            }
        )
        return 2

    cancelled_jobs = []
    errors = []
    for job_id in job_ids:
        try:
            cancel_job(job_id)
            cancelled_jobs.append(job_id)
        except Exception as exc:
            errors.append({"job_id": job_id, "error": exc.__class__.__name__, "message": str(exc)})

    if errors:
        print_json(
            {
                "ok": False,
                "error": "scancel_failed",
                "run_id": args.run_id,
                "cancelled_jobs": cancelled_jobs,
                "errors": errors,
            }
        )
        return 2

    for item in active_nodes:
        update_node_status(
            flow_paths,
            args.run_id,
            item["node"],
            "cancelled",
            "run cancel requested",
            progress=0,
            error_code="run_cancelled",
            slurm_job_id=item.get("slurm_job_id"),
        )
    write_event(
        flow_paths,
        args.run_id,
        "run_cancelled",
        "run cancel requested",
        payload={"nodes": active_nodes, "cancelled_jobs": cancelled_jobs},
    )
    print_json({"ok": True, "run_id": args.run_id, "cancelled_nodes": active_nodes, "cancelled_jobs": cancelled_jobs})
    return 0


def cmd_products(args) -> int:
    flow_paths = paths()
    manifest = read_json(flow_paths.product_manifest(args.run_id), default={"run_id": args.run_id, "products": []})
    print_json(manifest)
    return 0


def cmd_collect_context(args) -> int:
    flow_paths = paths()
    run_id = args.run_id
    tail = max(1, args.tail)
    event_limit = max(1, args.event_limit)
    max_logs = max(1, args.max_logs)
    context = {
        "ok": True,
        "run_id": run_id,
        "generated_at": now_iso(),
        "flow_root": str(flow_paths.root),
        "run_dir": str(flow_paths.run_dir(run_id)),
        "spec": read_json(flow_paths.run_spec(run_id), default={}),
        "status": refresh_workflow(flow_paths, run_id),
        "diagnose": diagnose_run(flow_paths, run_id),
        "fnl_manifest": read_json(flow_paths.fnl_manifest(run_id), default={}),
        "product_manifest": read_json(
            flow_paths.product_manifest(run_id),
            default={"run_id": run_id, "products": []},
        ),
        "events": read_jsonl(flow_paths.events(run_id), default=[])[-event_limit:],
        "logs": collect_log_tails(flow_paths.logs_dir(run_id), tail=tail, max_logs=max_logs),
    }
    print_json(context)
    return 0


def cmd_preflight(args) -> int:
    command_config = load_command_config(args.commands_file)
    result = run_preflight(paths().root, command_config)
    print_json(result)
    return 0 if result["ok"] else 2


def collect_log_tails(log_dir: Path, tail: int, max_logs: int) -> list[dict[str, Any]]:
    if not log_dir.exists():
        return []
    logs = []
    files = [path for path in log_dir.glob("*") if path.is_file()]
    files.sort(key=lambda path: path.stat().st_mtime, reverse=True)
    for path in files:
        logs.append(
            {
                "name": path.name,
                "path": str(path),
                "size_bytes": path.stat().st_size,
                "tail": read_tail_lines(path, tail),
            }
        )
        if len(logs) >= max_logs:
            break
    return logs


def read_tail_lines(path: Path, lines: int) -> list[str]:
    text = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    return text[-lines:]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Offline WRF-Pollen flow controller")
    sub = parser.add_subparsers(dest="command", required=True)

    plan = sub.add_parser("plan")
    plan.add_argument("--run-id")
    plan.add_argument("--start", required=True)
    plan.add_argument("--end", required=True)
    plan.add_argument("--period", required=True, choices=["spring", "summer", "autumn"])
    plan.add_argument("--domain", default="neimeng")
    plan.add_argument("--variant", default="official")
    plan.add_argument("--met-provider", default="FNL")
    plan.add_argument("--commands-file")
    plan.set_defaults(func=cmd_plan)

    preflight = sub.add_parser("preflight")
    preflight.add_argument("--commands-file")
    preflight.set_defaults(func=cmd_preflight)

    sub.add_parser("list").set_defaults(func=cmd_list)

    status = sub.add_parser("status")
    status.add_argument("--run-id", required=True)
    status.add_argument("--json", action="store_true")
    status.set_defaults(func=cmd_status)

    fnl = sub.add_parser("fnl-verify")
    fnl.add_argument("--run-id")
    fnl.add_argument("--start")
    fnl.add_argument("--end")
    fnl.set_defaults(func=cmd_fnl_verify)

    submit = sub.add_parser("submit")
    submit.add_argument("--run-id", required=True)
    submit.add_argument("--dry-run", action="store_true")
    submit.add_argument("--allow-noop", action="store_true")
    submit.set_defaults(func=cmd_submit)

    run_node = sub.add_parser("run-node")
    run_node.add_argument("--run-id", required=True)
    run_node.add_argument("--node", required=True)
    run_node.set_defaults(func=cmd_run_node)

    logs = sub.add_parser("logs")
    logs.add_argument("--run-id", required=True)
    logs.add_argument("--node")
    logs.add_argument("--tail", type=int, default=200)
    logs.set_defaults(func=cmd_logs)

    events = sub.add_parser("events")
    events.add_argument("--run-id", required=True)
    events.add_argument("--node")
    events.add_argument("--level")
    events.add_argument("--event-type")
    events.add_argument("--tail", type=int, default=200)
    events.set_defaults(func=cmd_events)

    diagnose = sub.add_parser("diagnose")
    diagnose.add_argument("--run-id", required=True)
    diagnose.set_defaults(func=cmd_diagnose)

    retry = sub.add_parser("retry")
    retry.add_argument("--run-id", required=True)
    retry.add_argument("--node", required=True)
    retry.add_argument("--dry-run", action="store_true")
    retry.set_defaults(func=cmd_retry)

    cancel = sub.add_parser("cancel")
    cancel.add_argument("--run-id", required=True)
    cancel.add_argument("--dry-run", action="store_true")
    cancel.set_defaults(func=cmd_cancel)

    products = sub.add_parser("products")
    products.add_argument("--run-id", required=True)
    products.set_defaults(func=cmd_products)

    context = sub.add_parser("collect-context")
    context.add_argument("--run-id", required=True)
    context.add_argument("--tail", type=int, default=120)
    context.add_argument("--event-limit", type=int, default=100)
    context.add_argument("--max-logs", type=int, default=12)
    context.set_defaults(func=cmd_collect_context)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    if args.command == "fnl-verify" and not args.run_id and (not args.start or not args.end):
        parser.error("fnl-verify requires --run-id or both --start and --end")
    try:
        return args.func(args)
    except Exception as exc:
        print_json({"ok": False, "error": exc.__class__.__name__, "message": str(exc)})
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
