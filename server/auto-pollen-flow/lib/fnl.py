from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from .timeutils import format_cycle, iter_six_hourly, now_iso


def roots_from_env() -> list[Path]:
    raw = os.environ.get("FNL_ROOTS")
    if raw:
        roots = [Path(part) for part in raw.split(":") if part]
    else:
        roots = []
        for key in ("FNL_ROOT", "FNL_FALLBACK_ROOT"):
            value = os.environ.get(key)
            if value:
                roots.append(Path(value))
    unique: list[Path] = []
    seen = set()
    for root in roots:
        resolved = str(root.expanduser())
        if resolved not in seen:
            seen.add(resolved)
            unique.append(Path(resolved))
    return unique


def min_bytes_from_env() -> int:
    min_mb = float(os.environ.get("FNL_MIN_MB", "5.0"))
    return int(min_mb * 1024 * 1024)


def fnl_name(cycle) -> str:
    return f"fnl_{cycle.strftime('%Y%m%d')}_{cycle.strftime('%H')}_00.grib2"


def candidate_paths(root: Path, file_name: str, day: str, year: str) -> list[Path]:
    return [
        root / year / day / file_name,
        root / year / file_name,
        root / day / file_name,
        root / file_name,
    ]


def is_grib(path: Path) -> bool:
    try:
        with path.open("rb") as handle:
            return handle.read(4) == b"GRIB"
    except OSError:
        return False


def inspect_path(path: Path, min_bytes: int) -> dict[str, Any]:
    info: dict[str, Any] = {
        "path": str(path),
        "exists": path.exists(),
        "is_symlink": path.is_symlink(),
        "link_broken": path.is_symlink() and not path.exists(),
        "size_bytes": None,
        "valid_grib": False,
        "valid": False,
        "reason": "missing",
    }
    if info["link_broken"]:
        info["reason"] = "link_broken"
        return info
    if not path.exists():
        return info
    try:
        size = path.stat().st_size
    except OSError:
        info["reason"] = "stat_failed"
        return info
    valid_grib = is_grib(path)
    info["size_bytes"] = size
    info["valid_grib"] = valid_grib
    if size < min_bytes:
        info["reason"] = "too_small"
    elif not valid_grib:
        info["reason"] = "bad_magic"
    else:
        info["reason"] = "ok"
        info["valid"] = True
    return info


def scan_fnl(start, end, roots: list[Path] | None = None) -> dict[str, Any]:
    roots = roots if roots is not None else roots_from_env()
    min_bytes = min_bytes_from_env()
    files = []
    for cycle in iter_six_hourly(start, end):
        day = cycle.strftime("%Y%m%d")
        year = cycle.strftime("%Y")
        name = fnl_name(cycle)
        inspected = []
        for root in roots:
            for path in candidate_paths(root, name, day, year):
                checked = inspect_path(path, min_bytes)
                if checked["exists"] or checked["link_broken"]:
                    checked["root"] = str(root)
                    inspected.append(checked)
        valid = [item for item in inspected if item["valid"]]
        if valid:
            best = sorted(
                valid,
                key=lambda item: (item["size_bytes"] or 0, -roots.index(Path(item["root"]))),
                reverse=True,
            )[0]
            status = "server_ok"
            source = "server_primary" if roots and Path(best["root"]) == roots[0] else "server_fallback"
        else:
            best = None
            reasons = {item["reason"] for item in inspected}
            if "bad_magic" in reasons:
                status = "bad_magic"
            elif "too_small" in reasons:
                status = "too_small"
            elif "link_broken" in reasons:
                status = "link_broken"
            else:
                status = "missing"
            source = None
        files.append(
            {
                "valid_time": format_cycle(cycle),
                "file_name": name,
                "status": status,
                "needs_repair": status != "server_ok",
                "source": source,
                "server_path": best["path"] if best else None,
                "size_bytes": best["size_bytes"] if best else None,
                "valid_grib": bool(best),
                "candidates": inspected,
                "checked_at": now_iso(),
            }
        )
    ok = all(file["status"] == "server_ok" for file in files)
    return {
        "provider": "FNL",
        "start": format_cycle(start),
        "end": format_cycle(end),
        "roots": [str(root) for root in roots],
        "min_bytes": min_bytes,
        "ok": ok,
        "files": files,
        "checked_at": now_iso(),
    }
