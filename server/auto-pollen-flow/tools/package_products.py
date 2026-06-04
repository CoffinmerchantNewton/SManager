#!/usr/bin/env python3
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def main() -> int:
    run_id = require_env("RUN_ID")
    run_dir = Path(require_env("FLOW_RUN_DIR")).resolve()
    products_dir = run_dir / "products"
    extracted = read_json(products_dir / "extracted_manifest.json", default={"products": []})
    products = extracted.get("products", [])
    manifest = {
        "run_id": run_id,
        "generated_at": now_iso(),
        "products": products,
    }
    write_json(products_dir / "product_manifest.json", manifest)
    print(json.dumps({"ok": True, "run_id": run_id, "count": len(products)}, ensure_ascii=False, sort_keys=True))
    return 0


def read_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def require_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"required env var is missing: {name}")
    return value


if __name__ == "__main__":
    raise SystemExit(main())
