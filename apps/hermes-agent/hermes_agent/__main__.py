from __future__ import annotations

import argparse
import json
import sys

from .client import ApiClient


DEFAULT_API = "http://localhost:8000/api/v1"


def cmd_tick(args) -> int:
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
    result = ApiClient(args.api).post("/agent/tick", payload)
    json.dump(result, sys.stdout, ensure_ascii=False, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    return 0 if result.get("ok") else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Hermes-agent one-shot runner")
    parser.add_argument("--api", default=DEFAULT_API)
    sub = parser.add_subparsers(dest="command", required=True)

    tick = sub.add_parser("tick")
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
    tick.set_defaults(func=cmd_tick)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
