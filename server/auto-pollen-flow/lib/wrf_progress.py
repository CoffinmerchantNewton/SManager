from __future__ import annotations

import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .paths import FlowPaths
from .timeutils import parse_cycle


WRFOUT_RE = re.compile(r"^wrfout_d(?P<domain>\d{2})_(?P<time>\d{4}-\d{2}-\d{2}_\d{2}[:-]\d{2}[:-]\d{2})")


def enrich_wrf_run_node(paths: FlowPaths, spec: dict[str, Any], node: dict[str, Any]) -> dict[str, Any]:
    if node.get("node") != "wrf_run":
        return node
    progress = inspect_wrfout_progress(paths, spec)
    if not progress.get("available"):
        node["wrfout_progress"] = progress
        return node

    node["wrfout_progress"] = progress
    if node.get("status") not in {"success", "error", "skipped", "cancelled"}:
        node["progress"] = progress["progress"]
        latest_time = progress.get("latest_forecast_time") or "-"
        eta = progress.get("eta_human")
        if eta:
            node["message"] = f"wrfout through {latest_time}; ETA {eta}"
        else:
            node["message"] = f"wrfout through {latest_time}"
    return node


def inspect_wrfout_progress(paths: FlowPaths, spec: dict[str, Any]) -> dict[str, Any]:
    run_id = spec["run_id"]
    start = as_utc(parse_cycle(spec["start"]))
    end = as_utc(parse_cycle(spec["end"]))
    total_seconds = max(0.0, (end - start).total_seconds())
    output_dirs = candidate_output_dirs(paths, spec)
    files = find_wrfout_files(output_dirs)
    if not files:
        return {
            "available": False,
            "reason": "no_wrfout_found",
            "output_dirs": [str(path) for path in output_dirs],
            "run_id": run_id,
            "start": spec.get("start"),
            "end": spec.get("end"),
        }

    first = files[0]
    latest = files[-1]
    completed_seconds = max(0.0, (latest["forecast_time"] - start).total_seconds())
    progress = 100.0 if total_seconds <= 0 else clamp(completed_seconds * 100.0 / total_seconds, 0.0, 100.0)
    eta_seconds = estimate_remaining_seconds(files, end)
    return {
        "available": True,
        "run_id": run_id,
        "start": spec.get("start"),
        "end": spec.get("end"),
        "output_dirs": [str(path) for path in output_dirs],
        "wrfout_count": len(files),
        "first_output_path": str(first["path"]),
        "first_forecast_time": isoformat(first["forecast_time"]),
        "first_output_mtime": isoformat(first["mtime"]),
        "latest_output_path": str(latest["path"]),
        "latest_forecast_time": isoformat(latest["forecast_time"]),
        "latest_output_mtime": isoformat(latest["mtime"]),
        "completed_forecast_seconds": int(completed_seconds),
        "total_forecast_seconds": int(total_seconds),
        "remaining_forecast_seconds": int(max(0.0, (end - latest["forecast_time"]).total_seconds())),
        "progress": round(progress, 2),
        "eta_seconds": int(eta_seconds) if eta_seconds is not None else None,
        "eta_human": format_duration(eta_seconds) if eta_seconds is not None else None,
        "method": "wrfout filename time compared with run start/end; ETA from first/latest wrfout mtimes",
    }


def candidate_output_dirs(paths: FlowPaths, spec: dict[str, Any]) -> list[Path]:
    wrf_node = next((item for item in spec.get("nodes", []) if item.get("name") == "wrf_run"), {})
    env = {str(key): str(value) for key, value in wrf_node.get("env", {}).items()}
    candidates: list[Path] = []
    for key in ("WRFOUT_DIR", "WRF_OUTPUT_DIR", "WRF_RUN_CWD", "WRF_RUN_DIR"):
        value = env.get(key)
        if value:
            base = Path(expand_env(value, env))
            candidates.append(base)
            candidates.append(base / "output")
    candidates.extend(auto_pollen_wrf_output_dirs(env, spec))
    if wrf_node.get("cwd"):
        candidates.append(Path(expand_env(str(wrf_node["cwd"]), env)))
    candidates.append(paths.run_dir(spec["run_id"]))

    unique = []
    seen = set()
    for path in candidates:
        try:
            resolved = path.expanduser().resolve()
        except OSError:
            resolved = path.expanduser()
        if str(resolved) in seen:
            continue
        seen.add(str(resolved))
        unique.append(resolved)
    return unique


def auto_pollen_wrf_output_dirs(env: dict[str, str], spec: dict[str, Any]) -> list[Path]:
    auto_root = env.get("AUTO_POLLEN_ROOT")
    if not auto_root:
        return []
    run_name = wrf_archive_run_name(spec)
    if not run_name:
        return []
    root = Path(expand_env(auto_root, env)) / "WRF"
    run_names = [run_name]
    variant = str(spec.get("variant") or "").strip()
    if variant and variant not in {"default", "none"}:
        run_names.append(f"{run_name}_{variant}")
    dirs: list[Path] = []
    for name in run_names:
        run_dir = root / name
        dirs.extend([run_dir / "output", run_dir])
    return dirs


def wrf_archive_run_name(spec: dict[str, Any]) -> str | None:
    start = short_cycle(spec.get("start"))
    end = short_cycle(spec.get("end"))
    if not start or not end:
        return None
    return f"wrf{start}-{end}"


def short_cycle(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if re.fullmatch(r"\d{10}", text):
        return text[2:]
    try:
        return parse_cycle(text).strftime("%y%m%d%H")
    except ValueError:
        return None


def expand_env(value: str, env: dict[str, str]) -> str:
    merged = os.environ.copy()
    merged.update(env)
    expanded = value
    for key, item in merged.items():
        expanded = expanded.replace(f"${key}", item).replace(f"${{{key}}}", item)
    return os.path.expanduser(expanded)


def find_wrfout_files(output_dirs: list[Path]) -> list[dict[str, Any]]:
    by_path: dict[str, dict[str, Any]] = {}
    for directory in output_dirs:
        if not directory.exists():
            continue
        for path in list(directory.glob("wrfout_d??_*")) + list(directory.glob("**/wrfout_d??_*")):
            if not path.is_file():
                continue
            match = WRFOUT_RE.match(path.name)
            if not match:
                continue
            forecast_time = parse_wrfout_time(match.group("time"))
            stat = path.stat()
            by_path[str(path.resolve())] = {
                "path": path.resolve(),
                "forecast_time": forecast_time,
                "mtime": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc),
                "size_bytes": stat.st_size,
            }
    return sorted(by_path.values(), key=lambda item: (item["forecast_time"], item["mtime"], str(item["path"])))


def parse_wrfout_time(value: str) -> datetime:
    value = re.sub(r"_(\d{2})-(\d{2})-(\d{2})$", r"_\1:\2:\3", value)
    return datetime.strptime(value, "%Y-%m-%d_%H:%M:%S").replace(tzinfo=timezone.utc)


def as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def estimate_remaining_seconds(files: list[dict[str, Any]], end: datetime) -> float | None:
    first = files[0]
    latest = files[-1]
    produced_forecast_seconds = (latest["forecast_time"] - first["forecast_time"]).total_seconds()
    wall_seconds = (latest["mtime"] - first["mtime"]).total_seconds()
    remaining_forecast_seconds = max(0.0, (end - latest["forecast_time"]).total_seconds())
    if produced_forecast_seconds <= 0 or wall_seconds <= 0:
        return None
    return remaining_forecast_seconds * wall_seconds / produced_forecast_seconds


def isoformat(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


def format_duration(seconds: float | None) -> str | None:
    if seconds is None:
        return None
    seconds = max(0, int(seconds))
    days, remainder = divmod(seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, _ = divmod(remainder, 60)
    if days:
        return f"{days}d {hours}h"
    if hours:
        return f"{hours}h {minutes}m"
    return f"{minutes}m"
