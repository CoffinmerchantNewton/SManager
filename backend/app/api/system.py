from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from ..core.config import settings
from ..core.database import get_db
from ..schemas.run_control import FlowResponse
from ..services.ssh import SSHClient

router = APIRouter()


def check(name: str, status: str, message: str, detail: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "name": name,
        "status": status,
        "message": message,
        "detail": detail or {},
    }


@router.get("/doctor", response_model=FlowResponse)
def doctor(db: Session = Depends(get_db)):
    checks: list[dict[str, Any]] = []

    try:
        db.execute(text("SELECT 1"))
        checks.append(check("database", "ok", "database connection is usable"))
    except Exception as exc:
        checks.append(check("database", "error", str(exc), {"error": exc.__class__.__name__}))

    ssh = SSHClient()
    checks.append(
        check(
            "server_connection_mode",
            "ok",
            "local mode" if ssh.is_local else "ssh mode",
            {
                "host": settings.SERVER_SSH_HOST,
                "user": settings.SERVER_SSH_USER,
                "port": settings.SERVER_SSH_PORT,
                "timeout": settings.SERVER_SSH_TIMEOUT,
            },
        )
    )

    flowctl_path = settings.SERVER_FLOWCTL_PATH
    checks.append(
        check(
            "server_flowctl_path",
            "ok" if bool(flowctl_path) else "error",
            flowctl_path or "SERVER_FLOWCTL_PATH is not configured",
            {"workdir": settings.SERVER_FLOW_WORKDIR, "root": settings.SERVER_FLOW_ROOT},
        )
    )

    if ssh.is_local and flowctl_path:
        local_flowctl = Path(flowctl_path).expanduser()
        checks.append(
            check(
                "local_flowctl_file",
                "ok" if local_flowctl.is_file() else "warning",
                str(local_flowctl),
                {"exists": local_flowctl.is_file()},
            )
        )

    for command in ("ssh", "scp", "rsync"):
        found = shutil.which(command)
        status = "ok" if found else "warning"
        if command == "ssh" and not ssh.is_local and not found:
            status = "error"
        checks.append(
            check(
                f"command:{command}",
                status,
                found or f"{command} not found on jumpbox PATH",
                {"path": found},
            )
        )

    checks.append(
        check(
            "fnl_download_command",
            "ok" if settings.FNL_DOWNLOAD_COMMAND else "warning",
            "configured" if settings.FNL_DOWNLOAD_COMMAND else "FNL_DOWNLOAD_COMMAND is not configured",
            {"required_when": "server FNL verification reports repairable files"},
        )
    )
    checks.append(
        check(
            "server_fnl_upload_dir",
            "ok" if settings.SERVER_FNL_UPLOAD_DIR else "warning",
            settings.SERVER_FNL_UPLOAD_DIR or "SERVER_FNL_UPLOAD_DIR is not configured",
            {"upload_method": settings.FNL_UPLOAD_METHOD},
        )
    )
    checks.append(
        check(
            "jumpbox_storage",
            "ok",
            "configured",
            {
                "fnl_cache_dir": settings.JUMPBOX_FNL_CACHE_DIR,
                "products_dir": settings.JUMPBOX_PRODUCTS_DIR,
            },
        )
    )

    status_counts = {
        "ok": sum(1 for item in checks if item["status"] == "ok"),
        "warning": sum(1 for item in checks if item["status"] == "warning"),
        "error": sum(1 for item in checks if item["status"] == "error"),
    }
    return FlowResponse(
        ok=status_counts["error"] == 0,
        data={
            "checks": checks,
            "status_counts": status_counts,
            "version": settings.VERSION,
        },
    )
