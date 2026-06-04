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
WRF_POLLEN_PRESETS = {"wrf_pollen", "pollen_forecast", "auto_pollen"}
POLLEN_SPECIES = [
    {"index": 1, "variable": "POLLEN_1", "name": "evergreen conifer"},
    {"index": 2, "variable": "POLLEN_2", "name": "poplar and willow"},
    {"index": 3, "variable": "POLLEN_3", "name": "oak"},
    {"index": 4, "variable": "POLLEN_4", "name": "elm"},
    {"index": 5, "variable": "POLLEN_5", "name": "white birch"},
    {"index": 6, "variable": "POLLEN_6", "name": "larch"},
    {"index": 7, "variable": "POLLEN_7", "name": "poaceae"},
    {"index": 8, "variable": "POLLEN_8", "name": "artemisia"},
    {"index": 9, "variable": "POLLEN_9", "name": "chenopodiaceae"},
]
WRF_POLLEN_MET_VARIABLES = ["T2", "U10", "V10", "RAINC", "RAINNC", "RAINSH"]
CITY_FORECAST_VARIABLES = [
    "pollen_total",
    "dominant_species_index",
    "t2_c",
    "wind10_ms",
    "precip_step_mm",
    "precip_accum_mm",
]
DEFAULT_CITY_POINTS = [
    {"name": "\u5317\u4eac", "longitude": 116.4074, "latitude": 39.9042},
    {"name": "\u5929\u6d25", "longitude": 117.2000, "latitude": 39.1333},
    {"name": "\u4e0a\u6d77", "longitude": 121.4737, "latitude": 31.2304},
    {"name": "\u5e7f\u5dde", "longitude": 113.2644, "latitude": 23.1291},
    {"name": "\u6df1\u5733", "longitude": 114.0579, "latitude": 22.5431},
    {"name": "\u6b66\u6c49", "longitude": 114.3054, "latitude": 30.5931},
    {"name": "\u6210\u90fd", "longitude": 104.0665, "latitude": 30.5728},
    {"name": "\u897f\u5b89", "longitude": 108.9398, "latitude": 34.3416},
    {"name": "\u54c8\u5c14\u6ee8", "longitude": 126.5349, "latitude": 45.8038},
    {"name": "\u6c88\u9633", "longitude": 123.4315, "latitude": 41.8057},
    {"name": "\u957f\u6625", "longitude": 125.3235, "latitude": 43.8171},
    {"name": "\u547c\u548c\u6d69\u7279", "longitude": 111.7492, "latitude": 40.8426},
    {"name": "\u77f3\u5bb6\u5e84", "longitude": 114.5149, "latitude": 38.0428},
    {"name": "\u592a\u539f", "longitude": 112.5489, "latitude": 37.8706},
    {"name": "\u90d1\u5dde", "longitude": 113.6254, "latitude": 34.7466},
    {"name": "\u6d4e\u5357", "longitude": 117.1201, "latitude": 36.6512},
    {"name": "\u5357\u4eac", "longitude": 118.7969, "latitude": 32.0603},
    {"name": "\u676d\u5dde", "longitude": 120.1551, "latitude": 30.2741},
    {"name": "\u5408\u80a5", "longitude": 117.2272, "latitude": 31.8206},
    {"name": "\u957f\u6c99", "longitude": 112.9388, "latitude": 28.2282},
    {"name": "\u5357\u660c", "longitude": 115.8582, "latitude": 28.6829},
    {"name": "\u798f\u5dde", "longitude": 119.2965, "latitude": 26.0745},
    {"name": "\u91cd\u5e86", "longitude": 106.5516, "latitude": 29.5630},
    {"name": "\u8d35\u9633", "longitude": 106.6302, "latitude": 26.6470},
    {"name": "\u6606\u660e", "longitude": 102.8329, "latitude": 24.8801},
    {"name": "\u5357\u5b81", "longitude": 108.3669, "latitude": 22.8170},
    {"name": "\u6d77\u53e3", "longitude": 110.1983, "latitude": 20.0440},
    {"name": "\u5170\u5dde", "longitude": 103.8343, "latitude": 36.0611},
    {"name": "\u897f\u5b81", "longitude": 101.7782, "latitude": 36.6171},
    {"name": "\u94f6\u5ddd", "longitude": 106.2309, "latitude": 38.4872},
    {"name": "\u4e4c\u9c81\u6728\u9f50", "longitude": 87.6168, "latitude": 43.8256},
    {"name": "\u62c9\u8428", "longitude": 91.1172, "latitude": 29.6469},
]
VARIABLE_METADATA = {
    "T2": {"long_name": "2-meter air temperature", "units": "K"},
    "U10": {"long_name": "10-meter eastward wind", "units": "m s-1"},
    "V10": {"long_name": "10-meter northward wind", "units": "m s-1"},
    "RAINC": {"long_name": "accumulated cumulus precipitation", "units": "mm"},
    "RAINNC": {"long_name": "accumulated grid-scale precipitation", "units": "mm"},
    "RAINSH": {"long_name": "accumulated shallow cumulus precipitation", "units": "mm"},
    "pollen_total": {"long_name": "total pollen concentration", "units": "grains/kg-dryair"},
    "dominant_species_index": {"long_name": "dominant pollen species index", "units": "1"},
    "t2_c": {"long_name": "2-meter air temperature", "units": "degC"},
    "wind10_ms": {"long_name": "10-meter wind speed", "units": "m s-1"},
    "precip_accum_mm": {"long_name": "accumulated precipitation", "units": "mm"},
    "precip_step_mm": {"long_name": "precipitation since previous summary step", "units": "mm"},
}
for species in POLLEN_SPECIES:
    VARIABLE_METADATA[species["variable"]] = {
        "long_name": f"{species['name']} pollen concentration",
        "units": "grains/kg-dryair",
    }


def main() -> int:
    run_id = require_env("RUN_ID")
    run_dir = Path(require_env("FLOW_RUN_DIR")).resolve()
    products_dir = run_dir / "products"
    output_dir = products_dir / "extracted"
    output_dir.mkdir(parents=True, exist_ok=True)

    sources = discover_sources(run_dir)
    products = []
    summary_product, summary_path = extract_summary_product(run_id, products_dir, sources, output_dir)
    if summary_product and summary_path:
        products.append(summary_product)
        city_product = extract_city_forecast_product(run_id, products_dir, summary_path, output_dir)
        if city_product:
            products.append(city_product)

    if copy_sources_enabled():
        for source in sources[:extract_limit()]:
            target = unique_target(output_dir, source.name)
            shutil.copy2(source, target)
            products.append(product_item(run_id, products_dir, target))

    visual_sources = [summary_path] if summary_path else sources[:extract_limit()]
    for source in visual_sources:
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


def extract_summary_product(
    run_id: str,
    products_dir: Path,
    sources: list[Path],
    output_dir: Path,
) -> tuple[dict[str, Any] | None, Path | None]:
    variables = summary_variables()
    if not variables:
        return None, None
    try:
        summary_path, metadata = write_summary_netcdf(run_id, sources, output_dir, variables)
    except Exception as exc:
        print(
            json.dumps(
                {
                    "warning": "summary_netcdf_extract_failed",
                    "variables": variables,
                    "error": exc.__class__.__name__,
                    "message": str(exc),
                },
                ensure_ascii=False,
                sort_keys=True,
            )
        )
        return None, None
    relative = summary_path.relative_to(products_dir)
    return (
        {
            "name": summary_path.name,
            "path": str(relative),
            "server_path": str(summary_path),
            "type": "summary_netcdf",
            "mime": "application/x-netcdf",
            "region": os.environ.get("PRODUCT_REGION", "unknown"),
            "pollen_type": os.environ.get("PRODUCT_POLLEN_TYPE", metadata["primary_variable"]),
            "resolution": os.environ.get("PRODUCT_RESOLUTION", "unknown"),
            "workflow_node": "product_extract",
            "workflow_version": os.environ.get("PRODUCT_WORKFLOW_VERSION", run_id),
            "summary_variable": metadata["primary_variable"],
            "summary_variables": metadata["summary_variables"],
            "derived_variables": metadata["derived_variables"],
            "time_steps": metadata["time_steps"],
            "source_count": metadata["source_count"],
        },
        summary_path,
    )


def write_summary_netcdf(
    run_id: str,
    sources: list[Path],
    output_dir: Path,
    variables: list[str],
) -> tuple[Path, dict[str, Any]]:
    import numpy as np  # type: ignore
    from scipy.io import netcdf_file  # type: ignore

    records = collect_summary_records(sources, variables)
    if not records:
        raise ValueError(f"no summary records found for variables={','.join(variables)}")

    every_nth = max(1, int(os.environ.get("PRODUCT_SUMMARY_EVERY_NTH", "1")))
    max_steps = max(1, int(os.environ.get("PRODUCT_SUMMARY_MAX_STEPS", "7")))
    selected = records[::every_nth][:max_steps]
    if not selected:
        raise ValueError("summary record selection is empty")

    first = selected[0]
    lats = np.asarray(first["lats"], dtype="f4")
    lons = np.asarray(first["lons"], dtype="f4")
    if lats.shape != lons.shape:
        raise ValueError(f"summary coordinate shape mismatch: lat={lats.shape}, lon={lons.shape}")
    present_variables = present_summary_variables(variables, selected)
    if not present_variables:
        raise ValueError("summary record selection has no usable variables")

    direct_values = {
        variable: stack_selected_variable(selected, variable, lats.shape)
        for variable in present_variables
    }
    derived_values = derive_summary_variables(direct_values)
    all_values = {**direct_values, **derived_values}
    primary_variable = summary_primary_variable(present_variables, derived_values)
    primary_shape = all_values[primary_variable].shape
    if primary_shape[-2:] != lats.shape or primary_shape[-2:] != lons.shape:
        raise ValueError(f"summary shape mismatch: values={primary_shape}, lat={lats.shape}, lon={lons.shape}")

    name = os.environ.get("PRODUCT_SUMMARY_NAME") or f"{run_id}_{primary_variable}_summary.nc"
    target = unique_target(output_dir, name)
    lead_step_hours = float(os.environ.get("PRODUCT_SUMMARY_STEP_HOURS", "24"))
    lead_hours = np.asarray([index * lead_step_hours for index in range(len(selected))], dtype="f4")

    with netcdf_file(target, mode="w") as dataset:
        dataset.createDimension("time", primary_shape[0])
        dataset.createDimension("south_north", primary_shape[1])
        dataset.createDimension("west_east", primary_shape[2])
        time_var = dataset.createVariable("lead_hours", "f", ("time",))
        time_var[:] = lead_hours
        time_var.units = "hours since forecast cycle"
        day_var = dataset.createVariable("forecast_day", "i", ("time",))
        day_var[:] = np.arange(1, primary_shape[0] + 1, dtype="i4")
        lat_var = dataset.createVariable("lat", "f", ("south_north", "west_east"))
        lat_var[:] = lats
        lat_var.units = "degrees_north"
        lon_var = dataset.createVariable("lon", "f", ("south_north", "west_east"))
        lon_var[:] = lons
        lon_var.units = "degrees_east"
        for variable, values in all_values.items():
            value_var = dataset.createVariable(variable, "f", ("time", "south_north", "west_east"))
            value_var[:] = values
            metadata = VARIABLE_METADATA.get(variable, {})
            value_var.long_name = summary_long_name(variable, metadata)
            value_var.units = summary_units(variable, metadata)
        dataset.run_id = run_id
        dataset.generated_at = now_iso()
        dataset.summary_variable = primary_variable
        dataset.summary_variables = ",".join(present_variables)
        dataset.derived_variables = ",".join(derived_values)
        dataset.pollen_species = pollen_species_attribute()
        dataset.source_files = ",".join(item["source"].name for item in selected)

    return target, {
        "primary_variable": primary_variable,
        "summary_variables": present_variables,
        "derived_variables": list(derived_values),
        "time_steps": int(primary_shape[0]),
        "source_count": len({item["source"] for item in selected}),
    }


def collect_summary_records(sources: list[Path], variables: list[str]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for source in sources:
        try:
            records.extend(read_summary_records(source, variables))
        except Exception as exc:
            print(
                json.dumps(
                    {
                        "warning": "summary_source_skipped",
                        "source": str(source),
                        "variables": variables,
                        "error": exc.__class__.__name__,
                        "message": str(exc),
                    },
                    ensure_ascii=False,
                    sort_keys=True,
                )
            )
    return records


def read_summary_records(path: Path, variables: list[str]) -> list[dict[str, Any]]:
    arrays = open_netcdf_variables(path, variables)
    lats = reduce_to_2d(arrays["lat"])
    lons = reduce_to_2d(arrays["lon"])
    stacks = {
        variable: values_to_time_stack(value, lats.shape)
        for variable, value in arrays["values"].items()
    }
    if not stacks:
        raise KeyError(f"none of these variables exist: {', '.join(variables)}")
    max_time = max(stack.shape[0] for stack in stacks.values())
    records = []
    for index in range(max_time):
        values_by_var = {}
        for variable, stack in stacks.items():
            if index < stack.shape[0]:
                values_by_var[variable] = stack[index]
            elif stack.shape[0] == 1:
                values_by_var[variable] = stack[0]
        if values_by_var:
            records.append(
                {
                    "source": path,
                    "record_index": index,
                    "values_by_var": values_by_var,
                    "lats": lats,
                    "lons": lons,
                }
            )
    return records


def values_to_time_stack(array: Any, lat_shape: tuple[int, int]):
    import numpy as np  # type: ignore

    data = sanitize_array(array)
    vertical_index = int(os.environ.get("PRODUCT_SUMMARY_VERTICAL_INDEX", os.environ.get("PRODUCT_VERTICAL_INDEX", "0")))
    axis_3d = os.environ.get("PRODUCT_SUMMARY_3D_AXIS", "time").lower()
    if data.ndim == 4:
        data = data[:, vertical_index, :, :]
    elif data.ndim == 3:
        if axis_3d == "vertical":
            data = data[vertical_index : vertical_index + 1, :, :]
        elif data.shape[-2:] == lat_shape:
            pass
        else:
            data = data[0:1, :, :]
    elif data.ndim == 2:
        data = data.reshape((1, *data.shape))
    else:
        data = reduce_to_2d(data).reshape((1, *lat_shape))
    if data.ndim != 3 or data.shape[-2:] != lat_shape:
        raise ValueError(f"expected summary stack as time/y/x, got shape={data.shape}, lat_shape={lat_shape}")
    return data


def present_summary_variables(variables: list[str], selected: list[dict[str, Any]]) -> list[str]:
    present = set()
    for item in selected:
        present.update(item["values_by_var"])
    return [variable for variable in variables if variable in present]


def stack_selected_variable(selected: list[dict[str, Any]], variable: str, shape: tuple[int, int]):
    import numpy as np  # type: ignore

    arrays = []
    for item in selected:
        value = item["values_by_var"].get(variable)
        if value is None:
            arrays.append(np.full(shape, np.nan, dtype="f4"))
            continue
        data = sanitize_array(value).astype("f4", copy=False)
        if data.shape != shape:
            raise ValueError(f"summary shape mismatch for {variable}: value={data.shape}, grid={shape}")
        arrays.append(data)
    return np.stack(arrays, axis=0)


def derive_summary_variables(values: dict[str, Any]) -> dict[str, Any]:
    import numpy as np  # type: ignore

    derived: dict[str, Any] = {}
    pollen_values = [
        (species["index"], values[species["variable"]])
        for species in POLLEN_SPECIES
        if species["variable"] in values
    ]
    if pollen_values:
        pollen_stack = np.stack([sanitize_array(item[1]).astype("f4", copy=False) for item in pollen_values], axis=0)
        finite_stack = np.where(np.isfinite(pollen_stack), pollen_stack, 0.0)
        derived["pollen_total"] = np.sum(finite_stack, axis=0).astype("f4", copy=False)
        species_indices = np.asarray([item[0] for item in pollen_values], dtype="f4")
        candidate = np.where(np.isfinite(pollen_stack), pollen_stack, -np.inf)
        has_value = np.any(np.isfinite(pollen_stack), axis=0)
        winner = np.argmax(candidate, axis=0)
        dominant = species_indices[winner].astype("f4", copy=False)
        dominant = np.where(has_value, dominant, np.nan).astype("f4", copy=False)
        derived["dominant_species_index"] = dominant

    if "T2" in values:
        derived["t2_c"] = (sanitize_array(values["T2"]).astype("f4", copy=False) - np.float32(273.15)).astype("f4")

    if "U10" in values and "V10" in values:
        u10 = sanitize_array(values["U10"]).astype("f4", copy=False)
        v10 = sanitize_array(values["V10"]).astype("f4", copy=False)
        derived["wind10_ms"] = np.sqrt(u10 * u10 + v10 * v10).astype("f4")

    rain_parts = [sanitize_array(values[name]).astype("f4", copy=False) for name in ("RAINC", "RAINNC", "RAINSH") if name in values]
    if rain_parts:
        precip_accum = np.sum(np.stack(rain_parts, axis=0), axis=0).astype("f4", copy=False)
        derived["precip_accum_mm"] = precip_accum
        precip_step = np.empty_like(precip_accum, dtype="f4")
        precip_step[0] = np.maximum(precip_accum[0], 0.0)
        if precip_accum.shape[0] > 1:
            precip_step[1:] = np.maximum(precip_accum[1:] - precip_accum[:-1], 0.0)
        derived["precip_step_mm"] = precip_step

    return derived


def summary_primary_variable(present_variables: list[str], derived_values: dict[str, Any]) -> str:
    configured = os.environ.get("PRODUCT_SUMMARY_PRIMARY_VARIABLE")
    if configured and configured.strip():
        name = configured.strip()
        if name in present_variables or name in derived_values:
            return name
        raise ValueError(f"PRODUCT_SUMMARY_PRIMARY_VARIABLE is not available: {name}")
    if "pollen_total" in derived_values:
        return "pollen_total"
    return present_variables[0]


def summary_long_name(variable: str, metadata: dict[str, str]) -> str:
    if variable == summary_variable():
        configured = os.environ.get("PRODUCT_SUMMARY_LONG_NAME")
        if configured:
            return configured
    return metadata.get("long_name", variable)


def summary_units(variable: str, metadata: dict[str, str]) -> str:
    if variable == summary_variable():
        configured = os.environ.get("PRODUCT_SUMMARY_UNITS") or os.environ.get("PRODUCT_UNITS")
        if configured:
            return configured
    return metadata.get("units", "unknown")


def pollen_species_attribute() -> str:
    return ";".join(f"{item['index']}={item['name']}" for item in POLLEN_SPECIES)


def extract_city_forecast_product(
    run_id: str,
    products_dir: Path,
    summary_path: Path,
    output_dir: Path,
) -> dict[str, Any] | None:
    if not city_forecast_enabled():
        return None
    try:
        payload = build_city_forecast(summary_path)
    except Exception as exc:
        print(
            json.dumps(
                {
                    "warning": "city_forecast_extract_failed",
                    "source": str(summary_path),
                    "error": exc.__class__.__name__,
                    "message": str(exc),
                },
                ensure_ascii=False,
                sort_keys=True,
            )
        )
        return None
    target = unique_target(output_dir, f"{summary_path.stem}_city_forecast.json")
    write_json(target, payload)
    return {
        "name": target.name,
        "path": str(target.relative_to(products_dir)),
        "server_path": str(target),
        "type": "city_forecast_json",
        "mime": "application/json",
        "region": os.environ.get("PRODUCT_REGION", "unknown"),
        "pollen_type": os.environ.get("PRODUCT_POLLEN_TYPE", "pollen_total"),
        "resolution": os.environ.get("PRODUCT_RESOLUTION", "unknown"),
        "workflow_node": "product_extract",
        "workflow_version": os.environ.get("PRODUCT_WORKFLOW_VERSION", run_id),
    }


def build_city_forecast(summary_path: Path) -> dict[str, Any]:
    import numpy as np  # type: ignore

    variables = city_forecast_variables()
    arrays = open_netcdf_variables(summary_path, variables)
    lats = reduce_to_2d(arrays["lat"])
    lons = reduce_to_2d(arrays["lon"])
    stacks = {
        variable: values_to_time_stack(value, lats.shape)
        for variable, value in arrays["values"].items()
    }
    if "pollen_total" not in stacks:
        raise KeyError("city forecast requires pollen_total in summary NetCDF")

    lead_hours = read_optional_time_axis(summary_path, "lead_hours", stacks["pollen_total"].shape[0])
    forecast_days = read_optional_time_axis(summary_path, "forecast_day", stacks["pollen_total"].shape[0])
    thresholds = pollen_risk_thresholds()
    cities = []
    for city in city_points():
        row, col, distance_km = nearest_grid_cell(lats, lons, float(city["latitude"]), float(city["longitude"]))
        forecast = []
        for time_index in range(stacks["pollen_total"].shape[0]):
            pollen_total = finite_float(stacks["pollen_total"][time_index, row, col])
            forecast_day = forecast_days[time_index] if time_index < len(forecast_days) else None
            lead_hour = lead_hours[time_index] if time_index < len(lead_hours) else None
            step = {
                "time_index": time_index,
                "forecast_day": int(forecast_day) if forecast_day is not None else time_index + 1,
                "lead_hours": lead_hour if lead_hour is not None else float(time_index * 24),
                "pollen_total": pollen_total,
                "risk": classify_pollen_risk(pollen_total, thresholds),
            }
            for variable, stack in stacks.items():
                if variable == "pollen_total":
                    continue
                if time_index >= stack.shape[0]:
                    continue
                step[variable] = finite_float(stack[time_index, row, col])
            if "dominant_species_index" in step:
                step["dominant_species"] = pollen_species_name(step["dominant_species_index"])
            forecast.append(step)
        cities.append(
            {
                "name": city["name"],
                "longitude": float(city["longitude"]),
                "latitude": float(city["latitude"]),
                "grid": {"row": int(row), "col": int(col), "distance_km": round(distance_km, 3)},
                "forecast": forecast,
            }
        )
    return {
        "type": "city_forecast",
        "source": summary_path.name,
        "generated_at": now_iso(),
        "variables": list(stacks),
        "risk_thresholds": thresholds,
        "species": [{"index": item["index"], "name": item["name"]} for item in POLLEN_SPECIES],
        "cities": cities,
    }


def city_forecast_enabled() -> bool:
    configured = os.environ.get("PRODUCT_CITY_FORECAST_ENABLED")
    if configured is not None:
        return configured.strip().lower() in {"1", "true", "yes", "on"}
    return os.environ.get("PRODUCT_SUMMARY_PRESET", "").strip().lower() in WRF_POLLEN_PRESETS


def city_forecast_variables() -> list[str]:
    configured = split_env_list(os.environ.get("PRODUCT_CITY_FORECAST_VARIABLES"))
    return unique_names(configured or CITY_FORECAST_VARIABLES)


def city_points() -> list[dict[str, Any]]:
    raw = os.environ.get("PRODUCT_CITY_POINTS_JSON")
    if raw:
        return normalize_city_points(json.loads(raw))
    path = os.environ.get("PRODUCT_CITY_POINTS_FILE")
    if path:
        return normalize_city_points(json.loads(Path(path).read_text(encoding="utf-8")))
    return DEFAULT_CITY_POINTS


def normalize_city_points(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, dict) and payload.get("type") == "FeatureCollection":
        items = []
        for feature in payload.get("features", []):
            coordinates = feature.get("geometry", {}).get("coordinates", [])
            properties = feature.get("properties", {})
            if len(coordinates) < 2:
                continue
            items.append(
                {
                    "name": properties.get("name") or properties.get("city") or "unknown",
                    "longitude": coordinates[0],
                    "latitude": coordinates[1],
                }
            )
        return items
    if isinstance(payload, dict) and "cities" in payload:
        payload = payload["cities"]
    if not isinstance(payload, list):
        raise ValueError("city points must be a list, {'cities': [...]}, or GeoJSON FeatureCollection")
    cities = []
    for item in payload:
        if not isinstance(item, dict):
            continue
        name = item.get("name") or item.get("city")
        longitude = item.get("longitude", item.get("lon"))
        latitude = item.get("latitude", item.get("lat"))
        if name is None or longitude is None or latitude is None:
            continue
        cities.append({"name": str(name), "longitude": float(longitude), "latitude": float(latitude)})
    if not cities:
        raise ValueError("city point list is empty")
    return cities


def nearest_grid_cell(lats: Any, lons: Any, latitude: float, longitude: float) -> tuple[int, int, float]:
    import numpy as np  # type: ignore

    lat_data = np.asarray(lats, dtype=float)
    lon_data = np.asarray(lons, dtype=float)
    distances = (lat_data - latitude) ** 2 + (lon_data - longitude) ** 2
    distances = np.where(np.isfinite(distances), distances, np.inf)
    index = int(np.argmin(distances))
    row, col = np.unravel_index(index, distances.shape)
    return int(row), int(col), haversine_km(latitude, longitude, float(lat_data[row, col]), float(lon_data[row, col]))


def haversine_km(lat_a: float, lon_a: float, lat_b: float, lon_b: float) -> float:
    radius_km = 6371.0
    phi_a = math.radians(lat_a)
    phi_b = math.radians(lat_b)
    d_phi = math.radians(lat_b - lat_a)
    d_lambda = math.radians(lon_b - lon_a)
    h = math.sin(d_phi / 2.0) ** 2 + math.cos(phi_a) * math.cos(phi_b) * math.sin(d_lambda / 2.0) ** 2
    return 2.0 * radius_km * math.asin(min(1.0, math.sqrt(h)))


def read_optional_time_axis(path: Path, variable: str, fallback_length: int) -> list[float | None]:
    try:
        arrays = open_netcdf_arrays(path, variable)
        data = sanitize_array(arrays["value"]).reshape(-1)
        return [finite_float(item) for item in data]
    except Exception:
        if variable == "forecast_day":
            return [float(index + 1) for index in range(fallback_length)]
        return [float(index * 24) for index in range(fallback_length)]


def pollen_risk_thresholds() -> dict[str, float]:
    raw = os.environ.get("PRODUCT_POLLEN_RISK_THRESHOLDS", "300,600,1000")
    if raw.strip().startswith("{"):
        payload = json.loads(raw)
        return {
            "medium": float(payload["medium"]),
            "high": float(payload["high"]),
            "critical": float(payload["critical"]),
        }
    values = [float(item.strip()) for item in raw.split(",") if item.strip()]
    if len(values) != 3:
        raise ValueError("PRODUCT_POLLEN_RISK_THRESHOLDS must be 'medium,high,critical'")
    medium, high, critical = values
    if not (medium <= high <= critical):
        raise ValueError("PRODUCT_POLLEN_RISK_THRESHOLDS must be ordered")
    return {"medium": medium, "high": high, "critical": critical}


def classify_pollen_risk(value: float | None, thresholds: dict[str, float]) -> str:
    if value is None or not math.isfinite(value):
        return "unknown"
    if value >= thresholds["critical"]:
        return "critical"
    if value >= thresholds["high"]:
        return "high"
    if value >= thresholds["medium"]:
        return "medium"
    return "low"


def pollen_species_name(index: Any) -> str | None:
    try:
        numeric = int(round(float(index)))
    except (TypeError, ValueError):
        return None
    for item in POLLEN_SPECIES:
        if item["index"] == numeric:
            return item["name"]
    return None


def finite_float(value: Any) -> float | None:
    number = float(value)
    return number if math.isfinite(number) else None


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


def open_netcdf_variables(path: Path, variables: list[str]) -> dict[str, Any]:
    try:
        from netCDF4 import Dataset  # type: ignore

        with Dataset(path) as dataset:
            values = {name: dataset.variables[name][:] for name in variables if name in dataset.variables}
            if not values:
                raise KeyError(f"none of these variables exist: {', '.join(variables)}")
            return {
                "values": values,
                "lat": first_variable(dataset.variables, lat_variable_names())[:],
                "lon": first_variable(dataset.variables, lon_variable_names())[:],
            }
    except ModuleNotFoundError:
        pass

    from scipy.io import netcdf_file  # type: ignore

    with netcdf_file(path, mode="r", mmap=False) as dataset:
        values = {name: dataset.variables[name].data.copy() for name in variables if name in dataset.variables}
        if not values:
            raise KeyError(f"none of these variables exist: {', '.join(variables)}")
        return {
            "values": values,
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

    data = sanitize_array(array)
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


def sanitize_array(array: Any):
    import numpy as np  # type: ignore

    data = np.ma.asarray(array)
    if np.ma.isMaskedArray(data):
        data = data.filled(np.nan)
    return np.asarray(data)


def geojson_stride(shape: tuple[int, int]) -> int:
    explicit = os.environ.get("PRODUCT_GEOJSON_STRIDE")
    if explicit:
        return max(1, int(explicit))
    max_points = max(1, int(os.environ.get("PRODUCT_GEOJSON_MAX_POINTS", "2000")))
    total = max(1, shape[0] * shape[1])
    return max(1, math.ceil(math.sqrt(total / max_points)))


def summary_variable() -> str | None:
    value = os.environ.get("PRODUCT_SUMMARY_VARIABLE")
    return value.strip() if value and value.strip() else None


def summary_variables() -> list[str]:
    explicit = split_env_list(os.environ.get("PRODUCT_SUMMARY_VARIABLES"))
    if explicit:
        return unique_names(explicit)

    legacy = summary_variable()
    if legacy:
        return [legacy]

    preset = os.environ.get("PRODUCT_SUMMARY_PRESET", "").strip().lower()
    if preset in WRF_POLLEN_PRESETS:
        return unique_names([item["variable"] for item in POLLEN_SPECIES] + WRF_POLLEN_MET_VARIABLES)

    return []


def split_env_list(value: str | None) -> list[str]:
    if not value:
        return []
    return [item.strip() for item in value.replace(os.pathsep, ",").split(",") if item.strip()]


def unique_names(names: list[str]) -> list[str]:
    result = []
    seen = set()
    for name in names:
        if name in seen:
            continue
        seen.add(name)
        result.append(name)
    return result


def copy_sources_enabled() -> bool:
    configured = os.environ.get("PRODUCT_COPY_SOURCES")
    if configured is not None:
        return configured.strip().lower() in {"1", "true", "yes", "on"}
    return not summary_variables()


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
