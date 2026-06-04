#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any


DEFAULT_API = "http://localhost:8000/api/v1"


def request_json(method: str, url: str, payload: dict[str, Any] | None = None) -> Any:
    data = None
    headers = {}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            text = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        text = exc.read().decode("utf-8", errors="ignore")
        raise SystemExit(f"HTTP {exc.code}: {text}") from exc
    return json.loads(text) if text else {}


def download_file(url: str, output: Path) -> None:
    request = urllib.request.Request(url, method="GET")
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


def api_url(args, path: str) -> str:
    return args.api.rstrip("/") + path


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
    print_json(request_json("POST", api_url(args, "/runs/"), payload))
    return 0


def cmd_status(args) -> int:
    print_json(request_json("GET", api_url(args, f"/runs/{args.run_id}/status")))
    return 0


def cmd_fnl_verify(args) -> int:
    print_json(request_json("POST", api_url(args, f"/runs/{args.run_id}/fnl-verify"), {}))
    return 0


def cmd_fnl_repair(args) -> int:
    payload = {"run_id": args.run_id, "start": args.start, "end": args.end}
    print_json(request_json("POST", api_url(args, "/fnl/repair"), payload))
    return 0


def cmd_fnl_coverage(args) -> int:
    query = {}
    for key in ("start", "end", "status"):
        value = getattr(args, key)
        if value:
            query[key] = value
    url = api_url(args, "/fnl/coverage")
    if query:
        url += "?" + urllib.parse.urlencode(query)
    print_json(request_json("GET", url))
    return 0


def cmd_submit(args) -> int:
    payload = {"dry_run": args.dry_run, "allow_noop": args.allow_noop}
    print_json(request_json("POST", api_url(args, f"/runs/{args.run_id}/submit"), payload))
    return 0


def cmd_logs(args) -> int:
    query = {"tail": str(args.tail)}
    if args.node:
        query["node"] = args.node
    url = api_url(args, f"/runs/{args.run_id}/logs") + "?" + urllib.parse.urlencode(query)
    data = request_json("GET", url)
    print(data.get("logs", ""), end="")
    return 0


def cmd_diagnose(args) -> int:
    print_json(request_json("GET", api_url(args, f"/runs/{args.run_id}/diagnose")))
    return 0


def cmd_retry_node(args) -> int:
    payload = {"node": args.node, "dry_run": args.dry_run}
    print_json(request_json("POST", api_url(args, f"/runs/{args.run_id}/retry"), payload))
    return 0


def cmd_sync_products(args) -> int:
    print_json(request_json("POST", api_url(args, f"/runs/{args.run_id}/sync-products"), {}))
    return 0


def cmd_products(args) -> int:
    query = {}
    for key in ("skip", "limit", "region", "pollen_type", "run_id", "status"):
        value = getattr(args, key)
        if value is not None:
            query[key] = value
    url = api_url(args, "/products")
    if query:
        url += "?" + urllib.parse.urlencode(query)
    print_json(request_json("GET", url))
    return 0


def cmd_product_download(args) -> int:
    output = Path(args.output) if args.output else None
    if output is None:
        product = request_json("GET", api_url(args, f"/products/{args.product_id}"))
        file_name = Path(product.get("file_path") or f"product-{args.product_id}").name
        output = Path(file_name or f"product-{args.product_id}")
    download_file(api_url(args, f"/products/{args.product_id}/download"), output)
    print_json({"ok": True, "product_id": args.product_id, "output": str(output)})
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
        "repair_fnl": not args.no_repair_fnl,
        "dry_run_submit": args.dry_run_submit,
        "allow_noop": args.allow_noop,
    }
    print_json(request_json("POST", api_url(args, "/agent/tick"), payload))
    return 0


def cmd_agent_actions(args) -> int:
    query = {}
    for key in ("run_id", "action_type", "status"):
        value = getattr(args, key)
        if value:
            query[key] = value
    query["limit"] = str(args.limit)
    print_json(request_json("GET", api_url(args, "/agent/actions") + "?" + urllib.parse.urlencode(query)))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Jumpbox CLI for SManager")
    parser.add_argument("--api", default=DEFAULT_API)
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

    diagnose = sub.add_parser("diagnose")
    diagnose.add_argument("--run-id", required=True)
    diagnose.set_defaults(func=cmd_diagnose)

    retry = sub.add_parser("retry-node")
    retry.add_argument("--run-id", required=True)
    retry.add_argument("--node", required=True)
    retry.add_argument("--dry-run", action="store_true", default=True)
    retry.add_argument("--real", dest="dry_run", action="store_false")
    retry.set_defaults(func=cmd_retry_node)

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
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
