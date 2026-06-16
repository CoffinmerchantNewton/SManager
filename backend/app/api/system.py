from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from ..core.config import settings
from ..core.database import get_db
from ..schemas.run_control import FlowResponse
from ..services.storage import StorageService

router = APIRouter()


class StorageCleanupRequest(BaseModel):
    dry_run: bool = True
    retention_days: int | None = None
    max_gb: float | None = None


def check(name: str, status: str, message: str, detail: dict[str, Any] | None = None) -> dict[str, Any]:
    return {"name": name, "status": status, "message": message, "detail": detail or {}}


@router.get("/doctor", response_model=FlowResponse)
def doctor(db: Session = Depends(get_db)):
    checks: list[dict[str, Any]] = []

    try:
        db.execute(text("SELECT 1"))
        backend = db.bind.url.get_backend_name() if db.bind is not None else "unknown"
        checks.append(
            check(
                "database",
                "ok" if backend in {"mysql", "mariadb"} else "error",
                f"database backend: {backend}",
            )
        )
    except Exception as exc:
        checks.append(check("database", "error", str(exc), {"error": exc.__class__.__name__}))

    checks.append(
        check(
            "server_api",
            "ok" if settings.SERVER_API_BASE_URL else "warning",
            settings.SERVER_API_BASE_URL or "SERVER_API_BASE_URL is not configured yet",
        )
    )
    checks.append(
        check(
            "tunnel",
            "ok" if settings.TUNNEL_HEALTH_URL else "warning",
            settings.TUNNEL_HEALTH_URL or "TUNNEL_HEALTH_URL is not configured yet",
        )
    )
    checks.append(
        check(
            "fnl_download_command",
            "ok" if settings.FNL_DOWNLOAD_COMMAND else "warning",
            "configured" if settings.FNL_DOWNLOAD_COMMAND else "FNL_DOWNLOAD_COMMAND is not configured",
        )
    )
    checks.append(
        check(
            "local_storage",
            "ok",
            "configured",
            {
                "fnl_cache_dir": settings.LOCAL_FNL_CACHE_DIR,
                "products_dir": settings.LOCAL_PRODUCTS_DIR,
                "logs_dir": settings.LOCAL_LOGS_DIR,
            },
        )
    )

    status_counts = {
        "ok": sum(1 for item in checks if item["status"] == "ok"),
        "warning": sum(1 for item in checks if item["status"] == "warning"),
        "error": sum(1 for item in checks if item["status"] == "error"),
    }
    return FlowResponse(ok=status_counts["error"] == 0, data={"checks": checks, "status_counts": status_counts})


@router.get("/storage", response_model=FlowResponse)
def storage_snapshot():
    snapshot = StorageService().snapshot()
    return FlowResponse(ok=snapshot["error_count"] == 0, data=snapshot)


@router.post("/storage/cleanup", response_model=FlowResponse)
def cleanup_storage(payload: StorageCleanupRequest):
    result = StorageService().cleanup(
        dry_run=payload.dry_run,
        retention_days=payload.retention_days,
        max_gb=payload.max_gb,
    )
    return FlowResponse(ok=bool(result["ok"]), data=result)


@router.get("/preflight", response_model=FlowResponse)
def preflight(db: Session = Depends(get_db)):
    doctor_result = doctor(db)
    return FlowResponse(
        ok=bool(doctor_result.ok),
        data={
            "doctor": doctor_result.data,
            "server_preflight": {
                "code": "server_first_migration_pending",
                "message": "Server preflight will be implemented through smanager-server and the Docker tunnel.",
            },
        },
    )
