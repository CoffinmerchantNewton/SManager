#!/usr/bin/env python3
from __future__ import annotations

import glob
import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


EXCLUDED_DIRS = {"products", "state", "logs", "slurm"}


def main() -> int:
    run_id = require_env("RUN_ID")
    run_dir = Path(require_env("FLOW_RUN_DIR")).resolve()
    products_dir = run_dir / "products"
    output_dir = products_dir / "extracted"
    output_dir.mkdir(parents=True, exist_ok=True)

    sources = discover_sources(run_dir)
    products = []
    for source in sources[:extract_limit()]:
        target = unique_target(output_dir, source.name)
        shutil.copy2(source, target)
        products.append(product_item(run_id, products_dir, target))

    manifest = {
        "run_id": run_id,
        "generated_at": now_iso(),
        "products": products,
    }
    write_json(products_dir / "extracted_manifest.json", manifest)
    print(json.dumps({"ok": True, "run_id": run_id, "count": len(products)}, ensure_ascii=False, sort_keys=True))
    return 0


def discover_sources(run_dir: Path) -> list[Path]:
    patterns = configured_patterns(run_dir)
    found: list[Path] = []
    seen = set()
    for pattern in patterns:
        for raw in glob.glob(pattern, recursive=True):
            path = Path(raw).resolve()
            if not should_include(path, run_dir):
                continue
            key = str(path)
            if key in seen:
                continue
            seen.add(key)
            found.append(path)
    return sorted(found)


def configured_patterns(run_dir: Path) -> list[str]:
    raw = os.environ.get("PRODUCT_SOURCE_GLOB")
    if raw:
        return [item for item in raw.split(os.pathsep) if item]
    return [
        str(run_dir / "**" / "*.nc"),
        str(run_dir / "**" / "wrfout*"),
    ]


def should_include(path: Path, run_dir: Path) -> bool:
    if not path.is_file():
        return False
    try:
        relative = path.relative_to(run_dir)
    except ValueError:
        return True
    return not any(part in EXCLUDED_DIRS for part in relative.parts)


def product_item(run_id: str, products_dir: Path, path: Path) -> dict[str, Any]:
    relative = path.relative_to(products_dir)
    product_type = "wrfout_netcdf" if path.name.startswith("wrfout") else "netcdf"
    return {
        "name": path.name,
        "path": str(relative),
        "server_path": str(path),
        "type": os.environ.get("PRODUCT_TYPE", product_type),
        "mime": os.environ.get("PRODUCT_MIME", "application/x-netcdf"),
        "region": os.environ.get("PRODUCT_REGION", "unknown"),
        "pollen_type": os.environ.get("PRODUCT_POLLEN_TYPE", "unknown"),
        "resolution": os.environ.get("PRODUCT_RESOLUTION", "unknown"),
        "workflow_node": "product_extract",
        "workflow_version": os.environ.get("PRODUCT_WORKFLOW_VERSION", run_id),
    }


def unique_target(directory: Path, name: str) -> Path:
    target = directory / name
    if not target.exists():
        return target
    stem = target.stem
    suffix = target.suffix
    index = 1
    while True:
        candidate = directory / f"{stem}_{index}{suffix}"
        if not candidate.exists():
            return candidate
        index += 1


def extract_limit() -> int:
    return max(1, int(os.environ.get("PRODUCT_EXTRACT_LIMIT", "50")))


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
