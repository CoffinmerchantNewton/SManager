from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from ..core.config import settings
from ..core.database import get_db
from ..schemas.run_control import FlowResponse
from ..services.server_client import server_client
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

    if settings.SERVER_API_BASE_URL:
        try:
            health = server_client.health()
            checks.append(
                check(
                    "server_api",
                    "ok" if not health.stale else "warning",
                    settings.SERVER_API_BASE_URL,
                    {
                        "source": health.source,
                        "stale": health.stale,
                        "payload": health.data,
                    },
                )
            )
        except Exception as exc:
            cached = health if "health" in locals() else None
            checks.append(
                check(
                    "server_api",
                    "warning" if cached and cached.stale else "error",
                    str(exc),
                    {"base_url": settings.SERVER_API_BASE_URL},
                )
            )
    else:
        checks.append(
            check(
                "server_api",
                "warning",
                "SERVER_API_BASE_URL is not configured yet",
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
    server_preflight = {"configured": server_client.configured}
    if server_client.configured:
        status_result = server_client.daemon_status()
        server_preflight.update(
            {
                "source": status_result.source,
                "stale": status_result.stale,
                "daemon": status_result.data,
            }
        )
    return FlowResponse(
        ok=bool(doctor_result.ok),
        data={
            "doctor": doctor_result.data,
            "server_preflight": server_preflight,
        },
    )
