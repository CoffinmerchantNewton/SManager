#!/usr/bin/env python3
from __future__ import annotations

import glob
import binascii
import json
import math
import os
import shutil
import struct
import zlib
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
        products.extend(extract_png_overlay_products(run_id, products_dir, source, output_dir))

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
    grid = read_netcdf_grid(path, variable)
    values = grid["values"]
    lats = grid["lats"]
    lons = grid["lons"]

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


def extract_png_overlay_products(
    run_id: str,
    products_dir: Path,
    source: Path,
    output_dir: Path,
) -> list[dict[str, Any]]:
    variable = png_overlay_variable()
    if not variable:
        return []
    try:
        grid = read_netcdf_grid(source, variable)
        png_path, metadata_path, metadata = write_png_overlay(source, output_dir, variable, grid)
    except Exception as exc:
        print(
            json.dumps(
                {
                    "warning": "png_overlay_extract_failed",
                    "source": str(source),
                    "variable": variable,
                    "error": exc.__class__.__name__,
                    "message": str(exc),
                },
                ensure_ascii=False,
                sort_keys=True,
            )
        )
        return []

    common = {
        "region": os.environ.get("PRODUCT_REGION", "unknown"),
        "pollen_type": os.environ.get("PRODUCT_POLLEN_TYPE", variable),
        "resolution": os.environ.get("PRODUCT_RESOLUTION", "unknown"),
        "workflow_node": "product_extract",
        "workflow_version": os.environ.get("PRODUCT_WORKFLOW_VERSION", run_id),
    }
    return [
        {
            "name": png_path.name,
            "path": str(png_path.relative_to(products_dir)),
            "server_path": str(png_path),
            "type": "png_overlay",
            "mime": "image/png",
            **common,
        },
        {
            "name": metadata_path.name,
            "path": str(metadata_path.relative_to(products_dir)),
            "server_path": str(metadata_path),
            "type": "png_overlay_metadata",
            "mime": "application/json",
            "related_image": metadata["image"]["name"],
            **common,
        },
    ]


def read_netcdf_grid(path: Path, variable: str) -> dict[str, Any]:
    arrays = open_netcdf_arrays(path, variable)
    values = reduce_to_2d(arrays["value"])
    lats = reduce_to_2d(arrays["lat"])
    lons = reduce_to_2d(arrays["lon"])
    if values.shape != lats.shape or values.shape != lons.shape:
        raise ValueError(f"shape mismatch: value={values.shape}, lat={lats.shape}, lon={lons.shape}")
    return {"values": values, "lats": lats, "lons": lons}


def write_png_overlay(
    source: Path,
    output_dir: Path,
    variable: str,
    grid: dict[str, Any],
) -> tuple[Path, Path, dict[str, Any]]:
    values = orient_values_for_image(grid["values"], grid["lats"], grid["lons"])
    bounds = grid_bounds(grid["lats"], grid["lons"])
    value_range = finite_range(values)
    rgba = rgba_heatmap(values, value_range["min"], value_range["max"])
    png_path = unique_target(output_dir, f"{source.stem}_{variable}.png")
    write_png_rgba(png_path, rgba)
    metadata_path = unique_target(output_dir, f"{source.stem}_{variable}.overlay.json")
    metadata = {
        "type": "png_overlay",
        "variable": variable,
        "source": source.name,
        "image": {
            "name": png_path.name,
            "path": png_path.name,
            "mime": "image/png",
            "width": int(rgba.shape[1]),
            "height": int(rgba.shape[0]),
        },
        "bounds": bounds,
        "value_range": value_range,
        "opacity": float(os.environ.get("PRODUCT_PNG_OPACITY", "0.72")),
        "legend": color_legend(value_range["min"], value_range["max"]),
        "generated_at": now_iso(),
    }
    write_json(metadata_path, metadata)
    return png_path, metadata_path, metadata


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


def png_overlay_variable() -> str | None:
    value = os.environ.get("PRODUCT_PNG_VARIABLE") or os.environ.get("PRODUCT_OVERLAY_VARIABLE")
    return value.strip() if value and value.strip() else None


def orient_values_for_image(values: Any, lats: Any, lons: Any) -> Any:
    import numpy as np  # type: ignore

    image = np.array(values, copy=True)
    row_lats = np.nanmean(np.asarray(lats, dtype=float), axis=1)
    col_lons = np.nanmean(np.asarray(lons, dtype=float), axis=0)
    if row_lats.size >= 2 and row_lats[0] < row_lats[-1]:
        image = np.flipud(image)
    if col_lons.size >= 2 and col_lons[0] > col_lons[-1]:
        image = np.fliplr(image)
    return image


def grid_bounds(lats: Any, lons: Any) -> dict[str, float]:
    import numpy as np  # type: ignore

    lat_data = np.asarray(lats, dtype=float)
    lon_data = np.asarray(lons, dtype=float)
    finite_lat = lat_data[np.isfinite(lat_data)]
    finite_lon = lon_data[np.isfinite(lon_data)]
    if finite_lat.size == 0 or finite_lon.size == 0:
        raise ValueError("latitude/longitude arrays contain no finite coordinates")
    return {
        "west": float(np.min(finite_lon)),
        "south": float(np.min(finite_lat)),
        "east": float(np.max(finite_lon)),
        "north": float(np.max(finite_lat)),
    }


def finite_range(values: Any) -> dict[str, float]:
    import numpy as np  # type: ignore

    data = np.asarray(values, dtype=float)
    finite = data[np.isfinite(data)]
    if finite.size == 0:
        raise ValueError("value array contains no finite values")
    configured_min = os.environ.get("PRODUCT_PNG_MIN")
    configured_max = os.environ.get("PRODUCT_PNG_MAX")
    vmin = float(configured_min) if configured_min is not None else float(np.min(finite))
    vmax = float(configured_max) if configured_max is not None else float(np.max(finite))
    if not math.isfinite(vmin) or not math.isfinite(vmax):
        raise ValueError("PRODUCT_PNG_MIN/PRODUCT_PNG_MAX must be finite numbers")
    if vmax <= vmin:
        vmax = vmin + 1.0
    return {"min": vmin, "max": vmax}


def rgba_heatmap(values: Any, vmin: float, vmax: float) -> Any:
    import numpy as np  # type: ignore

    data = np.asarray(values, dtype=float)
    normalized = np.clip((data - vmin) / (vmax - vmin), 0.0, 1.0)
    finite = np.isfinite(data)
    rgba = np.zeros((*data.shape, 4), dtype=np.uint8)
    max_alpha = int(max(0, min(255, round(float(os.environ.get("PRODUCT_PNG_ALPHA", "190"))))))
    for row in range(data.shape[0]):
        for col in range(data.shape[1]):
            if not finite[row, col]:
                continue
            t = float(normalized[row, col])
            red, green, blue = interpolate_rgb(t)
            alpha = round(max_alpha * (0.28 + 0.72 * t))
            rgba[row, col] = [red, green, blue, alpha]
    return rgba


def interpolate_rgb(t: float) -> tuple[int, int, int]:
    ramp = [
        (0.0, (37, 99, 235)),
        (0.35, (34, 197, 94)),
        (0.65, (250, 204, 21)),
        (0.82, (249, 115, 22)),
        (1.0, (220, 38, 38)),
    ]
    for index, (stop, color) in enumerate(ramp):
        if t <= stop:
            if index == 0:
                return color
            previous_stop, previous_color = ramp[index - 1]
            span = stop - previous_stop
            local_t = 0.0 if span <= 0 else (t - previous_stop) / span
            return tuple(
                round(previous_color[channel] + (color[channel] - previous_color[channel]) * local_t)
                for channel in range(3)
            )
    return ramp[-1][1]


def color_legend(vmin: float, vmax: float) -> list[dict[str, Any]]:
    stops = [0.0, 0.35, 0.65, 0.82, 1.0]
    return [
        {
            "value": round(vmin + (vmax - vmin) * stop, 6),
            "color": "#{:02x}{:02x}{:02x}".format(*interpolate_rgb(stop)),
        }
        for stop in stops
    ]


def write_png_rgba(path: Path, rgba: Any) -> None:
    height = int(rgba.shape[0])
    width = int(rgba.shape[1])
    raw = b"".join(b"\x00" + bytes(rgba[row].reshape(width * 4)) for row in range(height))
    payload = b"\x89PNG\r\n\x1a\n"
    payload += png_chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0))
    payload += png_chunk(b"IDAT", zlib.compress(raw, level=6))
    payload += png_chunk(b"IEND", b"")
    path.write_bytes(payload)


def png_chunk(kind: bytes, data: bytes) -> bytes:
    checksum = binascii.crc32(kind + data) & 0xFFFFFFFF
    return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", checksum)


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
