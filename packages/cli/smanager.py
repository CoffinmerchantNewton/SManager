#!/usr/bin/env python3
from __future__ import annotations

import argparse
import getpass
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any


DEFAULT_API = "http://localhost:8000/api/v1"
TOKEN_ENV = "SMANAGER_TOKEN"
TOKEN_FILE = Path.home() / ".smanager" / "token.json"
AUTH_TOKEN: str | None = None


def request_json(method: str, url: str, payload: dict[str, Any] | None = None) -> Any:
    data = None
    headers = {}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    if AUTH_TOKEN:
        headers["Authorization"] = f"Bearer {AUTH_TOKEN}"
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            text = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        text = exc.read().decode("utf-8", errors="ignore")
        raise SystemExit(f"HTTP {exc.code}: {text}") from exc
    return json.loads(text) if text else {}


def download_file(url: str, output: Path) -> None:
    headers = {"Authorization": f"Bearer {AUTH_TOKEN}"} if AUTH_TOKEN else {}
    request = urllib.request.Request(url, headers=headers, method="GET")
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            data = response.read()
    except urllib.error.HTTPError as exc:
        text = exc.read().decode("utf-8", errors="ignore")
        raise SystemExit(f"HTTP {exc.code}: {text}") from exc
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(data)


def print_json(data: Any) -> None:
    json.dump(data, sys.stdout, ensure_ascii=False, indent=2, sort_keys=True)
    sys.stdout.write("\n")


def print_result(data: Any) -> int:
    print_json(data)
    if isinstance(data, dict) and data.get("ok") is False:
        return 1
    return 0


def api_url(args, path: str) -> str:
    return args.api.rstrip("/") + path


def load_token(args) -> str | None:
    if getattr(args, "token", None):
        return args.token
    if os.environ.get(TOKEN_ENV):
        return os.environ[TOKEN_ENV]
    try:
        data = json.loads(TOKEN_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if data.get("api") and str(data["api"]).rstrip("/") != args.api.rstrip("/"):
        return None
    token = data.get("access_token")
    return str(token) if token else None


def save_token(api: str, payload: dict[str, Any]) -> None:
    TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
    TOKEN_FILE.write_text(
        json.dumps({"api": api.rstrip("/"), **payload}, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def cmd_login(args) -> int:
    password = args.password or getpass.getpass("Password: ")
    payload = {"username": args.username, "password": password}
    data = request_json("POST", api_url(args, "/auth/login"), payload)
    if not args.no_save:
        save_token(args.api, data)
    return print_result({key: value for key, value in data.items() if key != "access_token"} | {"saved": not args.no_save})


def cmd_plan(args) -> int:
    payload = {
        "run_id": args.run_id,
        "start": args.start,
        "end": args.end,
        "period": args.period,
        "domain": args.domain,
        "variant": args.variant,
        "met_provider": args.met_provider,
        "commands_file": args.commands_file,
    }
    return print_result(request_json("POST", api_url(args, "/runs/"), payload))


def cmd_runs(args) -> int:
    query = {"limit": str(args.limit), "sync": "false" if args.no_sync else "true"}
    if args.status:
        query["status"] = args.status
    url = api_url(args, "/runs/") + "?" + urllib.parse.urlencode(query)
    return print_result(request_json("GET", url))


def cmd_status(args) -> int:
    return print_result(request_json("GET", api_url(args, f"/runs/{args.run_id}/status")))


def cmd_fnl_verify(args) -> int:
    return print_result(request_json("POST", api_url(args, f"/runs/{args.run_id}/fnl-verify"), {}))


def cmd_fnl_repair(args) -> int:
    payload = {"run_id": args.run_id, "start": args.start, "end": args.end}
    return print_result(request_json("POST", api_url(args, "/fnl/repair"), payload))


def cmd_fnl_coverage(args) -> int:
    query = {}
    for key in ("start", "end", "status"):
        value = getattr(args, key)
        if value:
            query[key] = value
    if args.repair_only:
        query["needs_repair"] = "true"
    query["limit"] = str(args.limit)
    url = api_url(args, "/fnl/coverage")
    if query:
        url += "?" + urllib.parse.urlencode(query)
    return print_result(request_json("GET", url))


def cmd_submit(args) -> int:
    payload = {"dry_run": args.dry_run, "allow_noop": args.allow_noop}
    return print_result(request_json("POST", api_url(args, f"/runs/{args.run_id}/submit"), payload))


def cmd_logs(args) -> int:
    query = {"tail": str(args.tail)}
    if args.node:
        query["node"] = args.node
    url = api_url(args, f"/runs/{args.run_id}/logs") + "?" + urllib.parse.urlencode(query)
    data = request_json("GET", url)
    print(data.get("logs", ""), end="")
    return 0


def cmd_events(args) -> int:
    query = {"limit": str(args.limit), "sync": "false" if args.no_sync else "true"}
    for key in ("node", "level", "event_type"):
        value = getattr(args, key)
        if value:
            query[key] = value
    url = api_url(args, f"/runs/{args.run_id}/events") + "?" + urllib.parse.urlencode(query)
    return print_result(request_json("GET", url))


def cmd_diagnose(args) -> int:
    data = request_json("GET", api_url(args, f"/runs/{args.run_id}/diagnose"))
    if args.summary:
        payload = data.get("data", data) if isinstance(data, dict) else {}
        return print_result(
            {
                "ok": data.get("ok", True) if isinstance(data, dict) else True,
                "run_id": args.run_id,
                "analysis": payload.get("analysis", {}),
            }
        )
    return print_result(data)


def cmd_collect_context(args) -> int:
    query = {
        "tail": str(args.tail),
        "event_limit": str(args.event_limit),
        "max_logs": str(args.max_logs),
    }
    url = api_url(args, f"/runs/{args.run_id}/context") + "?" + urllib.parse.urlencode(query)
    return print_result(request_json("GET", url))


def cmd_retry_node(args) -> int:
    payload = {"node": args.node, "dry_run": args.dry_run}
    return print_result(request_json("POST", api_url(args, f"/runs/{args.run_id}/retry"), payload))


def cmd_cancel_run(args) -> int:
    payload = {"dry_run": args.dry_run}
    return print_result(request_json("POST", api_url(args, f"/runs/{args.run_id}/cancel"), payload))


def cmd_sync_products(args) -> int:
    return print_result(request_json("POST", api_url(args, f"/runs/{args.run_id}/sync-products"), {}))


def cmd_products(args) -> int:
    query = {}
    for key in ("skip", "limit", "region", "pollen_type", "run_id", "status"):
        value = getattr(args, key)
        if value is not None:
            query[key] = value
    url = api_url(args, "/products")
    if query:
        url += "?" + urllib.parse.urlencode(query)
    return print_result(request_json("GET", url))


def cmd_product_download(args) -> int:
    output = Path(args.output) if args.output else None
    if output is None:
        product = request_json("GET", api_url(args, f"/products/{args.product_id}"))
        file_name = Path(product.get("file_path") or f"product-{args.product_id}").name
        output = Path(file_name or f"product-{args.product_id}")
    download_file(api_url(args, f"/products/{args.product_id}/download"), output)
    print_json({"ok": True, "product_id": args.product_id, "output": str(output)})
    return 0


def cmd_product_content(args) -> int:
    data = request_json("GET", api_url(args, f"/products/{args.product_id}/content"))
    if args.output:
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print_json({"ok": True, "product_id": args.product_id, "output": str(output)})
        return 0
    print_json(data)
    return 0


def cmd_agent_tick(args) -> int:
    payload = {
        "run_id": args.run_id,
        "start": args.start,
        "end": args.end,
        "period": args.period,
        "domain": args.domain,
        "variant": args.variant,
        "met_provider": args.met_provider,
        "commands_file": args.commands_file,
        "repair_fnl": False if args.no_repair_fnl else None,
        "dry_run_submit": args.dry_run_submit,
        "allow_noop": args.allow_noop,
    }
    return print_result(request_json("POST", api_url(args, "/agent/tick"), payload))


def cmd_agent_actions(args) -> int:
    query = {}
    for key in ("run_id", "action_type", "status"):
        value = getattr(args, key)
        if value:
            query[key] = value
    query["limit"] = str(args.limit)
    return print_result(request_json("GET", api_url(args, "/agent/actions") + "?" + urllib.parse.urlencode(query)))


def cmd_tasks(args) -> int:
    query = {"skip": str(args.skip), "limit": str(args.limit)}
    return print_result(request_json("GET", api_url(args, "/tasks") + "?" + urllib.parse.urlencode(query)))


def cmd_task_run(args) -> int:
    payload = {
        "run_id": args.run_id,
        "start": args.start,
        "end": args.end,
        "period": args.period,
        "domain": args.domain,
        "variant": args.variant,
        "met_provider": args.met_provider,
        "commands_file": args.commands_file,
        "repair_fnl": not args.no_repair_fnl,
        "dry_run_submit": args.dry_run_submit,
        "allow_noop": args.allow_noop,
    }
    payload = {key: value for key, value in payload.items() if value is not None}
    return print_result(request_json("POST", api_url(args, f"/tasks/{args.task_id}/run"), payload))


def cmd_doctor(args) -> int:
    return print_result(request_json("GET", api_url(args, "/system/doctor")))


def cmd_preflight(args) -> int:
    query = {}
    if args.commands_file:
        query["commands_file"] = args.commands_file
    url = api_url(args, "/system/preflight")
    if query:
        url += "?" + urllib.parse.urlencode(query)
    return print_result(request_json("GET", url))


def cmd_storage(args) -> int:
    return print_result(request_json("GET", api_url(args, "/system/storage")))


def cmd_storage_cleanup(args) -> int:
    payload = {
        "dry_run": args.dry_run,
        "retention_days": args.retention_days,
        "max_gb": args.max_gb,
    }
    payload = {key: value for key, value in payload.items() if value is not None}
    return print_result(request_json("POST", api_url(args, "/system/storage/cleanup"), payload))


def cmd_config_template(args) -> int:
    data = {
        "env": {
            "ADMIN_USERNAME": "admin",
            "ADMIN_PASSWORD": "change-me",
            "SECRET_KEY": "change-me-to-a-long-random-secret",
            "SERVER_SSH_HOST": "10.40.140.17",
            "SERVER_SSH_USER": "anxq",
            "SERVER_SSH_PASSWORD": "<set locally; do not commit>",
            "SERVER_FLOWCTL_PATH": "/g7/anxq/Zhangjt/workspace/Smanager/server/auto-pollen-flow/flowctl.py",
            "SERVER_FLOW_WORKDIR": "/g7/anxq/Zhangjt/workspace/Smanager/server/auto-pollen-flow",
            "SERVER_FLOW_ROOT": "/g7/anxq/Zhangjt/workspace/Smanager/server/auto-pollen-flow",
            "SERVER_FNL_ROOTS": "/g1/COMMONDATA/glob/fnl:/g7/anxq/Zhangjt/static/fnl",
            "SERVER_FNL_UPLOAD_DIR": "/g7/anxq/Zhangjt/static/fnl",
            "FNL_DOWNLOAD_COMMAND": "<set local download command>",
            "STORAGE_RETENTION_DAYS": "30",
            "STORAGE_MAX_GB": "50",
        },
        "commands_file": "/g7/anxq/Zhangjt/workspace/Smanager/server/auto-pollen-flow/templates/run_spec/commands.auto_pollen.production.json",
        "token_env": TOKEN_ENV,
        "token_file": str(TOKEN_FILE),
    }
    return print_result(data)


def cmd_runs_batch(args) -> int:
    specs = read_json_file(Path(args.file))
    if not isinstance(specs, list):
        raise SystemExit("runs-batch file must contain a JSON array")
    results = []
    for spec in specs:
        if not isinstance(spec, dict):
            results.append({"ok": False, "error": "invalid_spec", "spec": spec})
            continue
        plan_result = request_json("POST", api_url(args, "/runs/"), spec)
        item = {"plan": plan_result}
        run_id = plan_result.get("data", {}).get("run_id") if isinstance(plan_result, dict) else None
        if args.submit_dry_run and run_id:
            item["submit"] = request_json(
                "POST",
                api_url(args, f"/runs/{run_id}/submit"),
                {"dry_run": True, "allow_noop": args.allow_noop},
            )
        results.append(item)
    return print_result({"ok": all(result.get("plan", {}).get("ok", True) for result in results), "results": results})


def cmd_products_batch(args) -> int:
    run_ids = list(args.run_id or [])
    if args.file:
        payload = read_json_file(Path(args.file))
        if isinstance(payload, list):
            run_ids.extend(str(item) for item in payload)
        else:
            raise SystemExit("products-batch file must contain a JSON array of run ids")
    results = []
    for run_id in run_ids:
        result = request_json("POST", api_url(args, f"/runs/{run_id}/sync-products"), {})
        results.append({"run_id": run_id, "result": result})
    return print_result({"ok": all(item["result"].get("ok", True) for item in results), "results": results})


def read_json_file(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Jumpbox CLI for SManager")
    parser.add_argument("--api", default=DEFAULT_API)
    parser.add_argument("--token", help=f"Bearer token. Defaults to ${TOKEN_ENV} or {TOKEN_FILE}")
    sub = parser.add_subparsers(dest="command", required=True)

    login = sub.add_parser("login")
    login.add_argument("--username", default="admin")
    login.add_argument("--password")
    login.add_argument("--no-save", action="store_true")
    login.set_defaults(func=cmd_login)

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

    runs = sub.add_parser("runs")
    runs.add_argument("--status")
    runs.add_argument("--limit", type=int, default=100)
    runs.add_argument("--no-sync", action="store_true")
    runs.set_defaults(func=cmd_runs)

    status = sub.add_parser("status")
    status.add_argument("--run-id", required=True)
    status.set_defaults(func=cmd_status)

    fnl = sub.add_parser("fnl-verify")
    fnl.add_argument("--run-id", required=True)
    fnl.set_defaults(func=cmd_fnl_verify)

    repair = sub.add_parser("fnl-repair")
    repair.add_argument("--run-id")
    repair.add_argument("--start")
    repair.add_argument("--end")
    repair.set_defaults(func=cmd_fnl_repair)

    coverage = sub.add_parser("fnl-coverage")
    coverage.add_argument("--start")
    coverage.add_argument("--end")
    coverage.add_argument("--status")
    coverage.add_argument("--repair-only", action="store_true")
    coverage.add_argument("--limit", type=int, default=500)
    coverage.set_defaults(func=cmd_fnl_coverage)

    submit = sub.add_parser("submit")
    submit.add_argument("--run-id", required=True)
    submit.add_argument("--dry-run", action="store_true")
    submit.add_argument("--allow-noop", action="store_true")
    submit.set_defaults(func=cmd_submit)

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
    events.add_argument("--limit", type=int, default=200)
    events.add_argument("--no-sync", action="store_true")
    events.set_defaults(func=cmd_events)

    diagnose = sub.add_parser("diagnose")
    diagnose.add_argument("--run-id", required=True)
    diagnose.add_argument("--summary", action="store_true")
    diagnose.set_defaults(func=cmd_diagnose)

    context = sub.add_parser("collect-context")
    context.add_argument("--run-id", required=True)
    context.add_argument("--tail", type=int, default=120)
    context.add_argument("--event-limit", type=int, default=100)
    context.add_argument("--max-logs", type=int, default=12)
    context.set_defaults(func=cmd_collect_context)

    retry = sub.add_parser("retry-node")
    retry.add_argument("--run-id", required=True)
    retry.add_argument("--node", required=True)
    retry.add_argument("--dry-run", action="store_true", default=True)
    retry.add_argument("--real", dest="dry_run", action="store_false")
    retry.set_defaults(func=cmd_retry_node)

    cancel = sub.add_parser("cancel-run")
    cancel.add_argument("--run-id", required=True)
    cancel.add_argument("--dry-run", action="store_true", default=True)
    cancel.add_argument("--real", dest="dry_run", action="store_false")
    cancel.set_defaults(func=cmd_cancel_run)

    sync_products = sub.add_parser("sync-products")
    sync_products.add_argument("--run-id", required=True)
    sync_products.set_defaults(func=cmd_sync_products)

    product_list = sub.add_parser("products")
    product_list.add_argument("--skip", type=int, default=0)
    product_list.add_argument("--limit", type=int, default=20)
    product_list.add_argument("--region")
    product_list.add_argument("--pollen-type", dest="pollen_type")
    product_list.add_argument("--run-id")
    product_list.add_argument("--status")
    product_list.set_defaults(func=cmd_products)

    product_download = sub.add_parser("product-download")
    product_download.add_argument("--product-id", type=int, required=True)
    product_download.add_argument("--output")
    product_download.set_defaults(func=cmd_product_download)

    product_content = sub.add_parser("product-content")
    product_content.add_argument("--product-id", type=int, required=True)
    product_content.add_argument("--output")
    product_content.set_defaults(func=cmd_product_content)

    tick = sub.add_parser("agent-tick")
    tick.add_argument("--run-id")
    tick.add_argument("--start", required=True)
    tick.add_argument("--end", required=True)
    tick.add_argument("--period", required=True, choices=["spring", "summer", "autumn"])
    tick.add_argument("--domain", default="neimeng")
    tick.add_argument("--variant", default="official")
    tick.add_argument("--met-provider", default="FNL")
    tick.add_argument("--commands-file")
    tick.add_argument("--dry-run-submit", action="store_true", default=True)
    tick.add_argument("--real-submit", dest="dry_run_submit", action="store_false")
    tick.add_argument("--allow-noop", action="store_true")
    tick.add_argument("--no-repair-fnl", action="store_true")
    tick.set_defaults(func=cmd_agent_tick)

    actions = sub.add_parser("agent-actions")
    actions.add_argument("--run-id")
    actions.add_argument("--action-type")
    actions.add_argument("--status")
    actions.add_argument("--limit", type=int, default=100)
    actions.set_defaults(func=cmd_agent_actions)

    tasks = sub.add_parser("tasks")
    tasks.add_argument("--skip", type=int, default=0)
    tasks.add_argument("--limit", type=int, default=100)
    tasks.set_defaults(func=cmd_tasks)

    task_run = sub.add_parser("task-run")
    task_run.add_argument("--task-id", type=int, required=True)
    task_run.add_argument("--run-id")
    task_run.add_argument("--start")
    task_run.add_argument("--end")
    task_run.add_argument("--period", choices=["spring", "summer", "autumn"])
    task_run.add_argument("--domain")
    task_run.add_argument("--variant")
    task_run.add_argument("--met-provider")
    task_run.add_argument("--commands-file")
    task_run.add_argument("--dry-run-submit", action="store_true", default=True)
    task_run.add_argument("--real-submit", dest="dry_run_submit", action="store_false")
    task_run.add_argument("--allow-noop", action="store_true")
    task_run.add_argument("--no-repair-fnl", action="store_true")
    task_run.set_defaults(func=cmd_task_run)

    doctor = sub.add_parser("doctor")
    doctor.set_defaults(func=cmd_doctor)

    preflight = sub.add_parser("preflight")
    preflight.add_argument("--commands-file")
    preflight.set_defaults(func=cmd_preflight)

    storage = sub.add_parser("storage")
    storage.set_defaults(func=cmd_storage)

    storage_cleanup = sub.add_parser("storage-cleanup")
    storage_cleanup.add_argument("--dry-run", action="store_true", default=True)
    storage_cleanup.add_argument("--real", dest="dry_run", action="store_false")
    storage_cleanup.add_argument("--retention-days", type=int)
    storage_cleanup.add_argument("--max-gb", type=float)
    storage_cleanup.set_defaults(func=cmd_storage_cleanup)

    config_template = sub.add_parser("config-template")
    config_template.set_defaults(func=cmd_config_template)

    runs_batch = sub.add_parser("runs-batch")
    runs_batch.add_argument("--file", required=True)
    runs_batch.add_argument("--submit-dry-run", action="store_true")
    runs_batch.add_argument("--allow-noop", action="store_true")
    runs_batch.set_defaults(func=cmd_runs_batch)

    products_batch = sub.add_parser("products-batch")
    products_batch.add_argument("--run-id", action="append")
    products_batch.add_argument("--file")
    products_batch.set_defaults(func=cmd_products_batch)
    return parser


def main() -> int:
    global AUTH_TOKEN
    parser = build_parser()
    args = parser.parse_args()
    AUTH_TOKEN = None if args.command == "login" else load_token(args)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
