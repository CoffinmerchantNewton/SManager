from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..core.config import settings


class StorageService:
    def snapshot(self) -> dict[str, Any]:
        roots = [self.summarize_root(name, path) for name, path in storage_roots().items()]
        return {
            "roots": roots,
            "total_bytes": sum(item["total_bytes"] for item in roots),
            "file_count": sum(item["file_count"] for item in roots),
            "error_count": sum(item["error_count"] for item in roots),
        }

    def summarize_root(self, name: str, path_value: str) -> dict[str, Any]:
        path = Path(path_value)
        files = 0
        total_bytes = 0
        latest_mtime: float | None = None
        errors: list[dict[str, str]] = []

        if path.exists():
            for item in path.rglob("*"):
                try:
                    if not item.is_file():
                        continue
                    stat = item.stat()
                    files += 1
                    total_bytes += stat.st_size
                    latest_mtime = max(latest_mtime or stat.st_mtime, stat.st_mtime)
                except OSError as exc:
                    errors.append({"path": str(item), "message": str(exc)})

        return {
            "name": name,
            "path": str(path),
            "exists": path.exists(),
            "file_count": files,
            "total_bytes": total_bytes,
            "latest_mtime": iso_from_mtime(latest_mtime),
            "error_count": len(errors),
            "errors": errors[:20],
        }


def storage_roots() -> dict[str, str]:
    return {
        "fnl": settings.JUMPBOX_FNL_CACHE_DIR,
        "products": settings.JUMPBOX_PRODUCTS_DIR,
        "logs": settings.JUMPBOX_LOGS_DIR,
        "manifests": settings.JUMPBOX_MANIFESTS_DIR,
        "cache": settings.JUMPBOX_CACHE_DIR,
    }


def iso_from_mtime(value: float | None) -> str | None:
    if value is None:
        return None
    return datetime.fromtimestamp(value, tz=timezone.utc).isoformat(timespec="seconds")
