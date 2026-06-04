#!/usr/bin/env python3
from __future__ import annotations

import glob
import json
import math
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
        geojson_product = extract_geojson_product(run_id, products_dir, source, output_dir)
        if geojson_product:
            products.append(geojson_product)

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


def extract_geojson_product(
    run_id: str,
    products_dir: Path,
    source: Path,
    output_dir: Path,
) -> dict[str, Any] | None:
    variable = os.environ.get("PRODUCT_GEOJSON_VARIABLE")
    if not variable:
        return None
    try:
        dataset = read_netcdf_points(source, variable)
    except Exception as exc:
        print(
            json.dumps(
                {
                    "warning": "geojson_extract_failed",
                    "source": str(source),
                    "variable": variable,
                    "error": exc.__class__.__name__,
                    "message": str(exc),
                },
                ensure_ascii=False,
                sort_keys=True,
            )
        )
        return None
    if not dataset["features"]:
        return None
    target = unique_target(output_dir, f"{source.stem}_{variable}.geojson")
    write_json(target, {"type": "FeatureCollection", "features": dataset["features"]})
    relative = target.relative_to(products_dir)
    return {
        "name": target.name,
        "path": str(relative),
        "server_path": str(target),
        "type": "geojson",
        "mime": "application/geo+json",
        "region": os.environ.get("PRODUCT_REGION", "unknown"),
        "pollen_type": os.environ.get("PRODUCT_POLLEN_TYPE", variable),
        "resolution": os.environ.get("PRODUCT_RESOLUTION", "unknown"),
        "workflow_node": "product_extract",
        "workflow_version": os.environ.get("PRODUCT_WORKFLOW_VERSION", run_id),
    }


def read_netcdf_points(path: Path, variable: str) -> dict[str, Any]:
    arrays = open_netcdf_arrays(path, variable)
    values = reduce_to_2d(arrays["value"])
    lats = reduce_to_2d(arrays["lat"])
    lons = reduce_to_2d(arrays["lon"])
    if values.shape != lats.shape or values.shape != lons.shape:
        raise ValueError(f"shape mismatch: value={values.shape}, lat={lats.shape}, lon={lons.shape}")

    step = geojson_stride(values.shape)
    features = []
    for row in range(0, values.shape[0], step):
        for col in range(0, values.shape[1], step):
            value = float(values[row, col])
            lat = float(lats[row, col])
            lon = float(lons[row, col])
            if not all(math.isfinite(item) for item in (value, lat, lon)):
                continue
            features.append(
                {
                    "type": "Feature",
                    "geometry": {"type": "Point", "coordinates": [lon, lat]},
                    "properties": {
                        "value": value,
                        "variable": variable,
                        "source": path.name,
                        "row": row,
                        "col": col,
                    },
                }
            )
    return {"features": features}


def open_netcdf_arrays(path: Path, variable: str) -> dict[str, Any]:
    try:
        from netCDF4 import Dataset  # type: ignore

        with Dataset(path) as dataset:
            return {
                "value": dataset.variables[variable][:],
                "lat": first_variable(dataset.variables, lat_variable_names())[:],
                "lon": first_variable(dataset.variables, lon_variable_names())[:],
            }
    except ModuleNotFoundError:
        pass

    from scipy.io import netcdf_file  # type: ignore

    with netcdf_file(path, mode="r", mmap=False) as dataset:
        return {
            "value": dataset.variables[variable].data.copy(),
            "lat": first_variable(dataset.variables, lat_variable_names()).data.copy(),
            "lon": first_variable(dataset.variables, lon_variable_names()).data.copy(),
        }


def first_variable(variables: dict[str, Any], names: list[str]) -> Any:
    for name in names:
        if name in variables:
            return variables[name]
    raise KeyError(f"none of these variables exist: {', '.join(names)}")


def lat_variable_names() -> list[str]:
    raw = os.environ.get("PRODUCT_LAT_VARIABLES", "XLAT,XLAT_M,lat,latitude,LAT,LATITUDE")
    return [item.strip() for item in raw.split(",") if item.strip()]


def lon_variable_names() -> list[str]:
    raw = os.environ.get("PRODUCT_LON_VARIABLES", "XLONG,XLONG_M,lon,longitude,LON,LONGITUDE")
    return [item.strip() for item in raw.split(",") if item.strip()]


def reduce_to_2d(array: Any):
    import numpy as np  # type: ignore

    data = np.asarray(array)
    time_index = int(os.environ.get("PRODUCT_TIME_INDEX", "0"))
    vertical_index = int(os.environ.get("PRODUCT_VERTICAL_INDEX", "0"))
    while data.ndim > 2:
        if data.ndim == 4:
            data = data[time_index, vertical_index]
        elif data.ndim == 3:
            data = data[time_index]
        else:
            data = data[0]
    if data.ndim != 2:
        raise ValueError(f"expected 2D data after slicing, got shape={data.shape}")
    return data


def geojson_stride(shape: tuple[int, int]) -> int:
    explicit = os.environ.get("PRODUCT_GEOJSON_STRIDE")
    if explicit:
        return max(1, int(explicit))
    max_points = max(1, int(os.environ.get("PRODUCT_GEOJSON_MAX_POINTS", "2000")))
    total = max(1, shape[0] * shape[1])
    return max(1, math.ceil(math.sqrt(total / max_points)))


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
