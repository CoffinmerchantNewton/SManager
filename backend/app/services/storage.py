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

    def cleanup(self, dry_run: bool = True, retention_days: int | None = None, max_gb: float | None = None) -> dict[str, Any]:
        retention = settings.STORAGE_RETENTION_DAYS if retention_days is None else retention_days
        max_bytes = int((settings.STORAGE_MAX_GB if max_gb is None else max_gb) * 1024 * 1024 * 1024)
        now = datetime.now(tz=timezone.utc).timestamp()
        cutoff = now - max(0, retention) * 86400
        candidates: list[dict[str, Any]] = []
        errors: list[dict[str, str]] = []

        for root_name, root_value in storage_roots().items():
            root = Path(root_value)
            if not root.exists():
                continue
            for item in root.rglob("*"):
                try:
                    if not item.is_file() or item.name == ".gitkeep":
                        continue
                    stat = item.stat()
                    candidates.append(
                        {
                            "root": root_name,
                            "path": str(item),
                            "size_bytes": stat.st_size,
                            "mtime": stat.st_mtime,
                            "age_days": round((now - stat.st_mtime) / 86400, 2),
                            "reason": "retention" if stat.st_mtime < cutoff else "quota",
                        }
                    )
                except OSError as exc:
                    errors.append({"path": str(item), "message": str(exc)})

        total_bytes = sum(item["size_bytes"] for item in candidates)
        expired = [item for item in candidates if item["mtime"] < cutoff]
        quota_pool = sorted(
            [item for item in candidates if item not in expired],
            key=lambda item: item["mtime"],
        )
        selected = list(expired)
        remaining_bytes = total_bytes - sum(item["size_bytes"] for item in selected)
        while remaining_bytes > max_bytes and quota_pool:
            item = quota_pool.pop(0)
            selected.append(item)
            remaining_bytes -= item["size_bytes"]

        deleted: list[dict[str, Any]] = []
        for item in selected:
            if dry_run:
                continue
            try:
                Path(item["path"]).unlink()
                deleted.append(item)
            except OSError as exc:
                errors.append({"path": item["path"], "message": str(exc)})

        return {
            "ok": not errors,
            "dry_run": dry_run,
            "retention_days": retention,
            "max_gb": max_gb if max_gb is not None else settings.STORAGE_MAX_GB,
            "candidate_count": len(candidates),
            "selected_count": len(selected),
            "selected_bytes": sum(item["size_bytes"] for item in selected),
            "deleted_count": len(deleted),
            "deleted_bytes": sum(item["size_bytes"] for item in deleted),
            "selected": selected[:500],
            "errors": errors[:50],
        }


def storage_roots() -> dict[str, str]:
    return {
        "fnl": settings.LOCAL_FNL_CACHE_DIR,
        "products": settings.LOCAL_PRODUCTS_DIR,
        "logs": settings.LOCAL_LOGS_DIR,
        "manifests": settings.LOCAL_MANIFESTS_DIR,
        "cache": settings.LOCAL_CACHE_DIR,
    }


def iso_from_mtime(value: float | None) -> str | None:
    if value is None:
        return None
    return datetime.fromtimestamp(value, tz=timezone.utc).isoformat(timespec="seconds")
