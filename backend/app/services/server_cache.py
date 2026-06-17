from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..core.config import settings


def cache_dir() -> Path:
    path = Path(settings.LOCAL_CACHE_DIR)
    path.mkdir(parents=True, exist_ok=True)
    return path


def read_cache(name: str) -> dict[str, Any] | None:
    path = cache_dir() / f"{name}.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def write_cache(name: str, payload: Any) -> None:
    envelope = {
        "cached_at": datetime.now(timezone.utc).isoformat(),
        "payload": payload,
    }
    path = cache_dir() / f"{name}.json"
    path.write_text(json.dumps(envelope, ensure_ascii=False, indent=2), encoding="utf-8")
