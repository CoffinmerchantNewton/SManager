from __future__ import annotations

from datetime import datetime, timedelta, timezone


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def parse_cycle(value: str) -> datetime:
    value = value.strip()
    for fmt in ("%Y%m%d%H", "%Y%m%d"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(
            f"unsupported cycle format: {value}; expected YYYYMMDDHH or YYYYMMDD"
        ) from exc


def format_cycle(value: datetime) -> str:
    return value.strftime("%Y%m%d%H")


def iter_six_hourly(start: datetime, end: datetime):
    current = start
    while current <= end:
        yield current
        current += timedelta(hours=6)


def default_run_id(start: datetime, period: str, domain: str, variant: str) -> str:
    safe_domain = domain.replace(" ", "_")
    safe_variant = variant.replace(" ", "_")
    return f"{format_cycle(start)}_{period}_{safe_domain}_{safe_variant}"
