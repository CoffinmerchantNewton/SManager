from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from ..core.database import get_db
from ..models.models import FnlFileRecord
from ..schemas.run_control import FnlRepairRequest, FnlVerifyRequest, FlowResponse

router = APIRouter()


@router.post("/verify-server", response_model=FlowResponse, status_code=status.HTTP_202_ACCEPTED)
def verify_server_fnl(payload: FnlVerifyRequest):
    if not payload.run_id and (not payload.start or not payload.end):
        raise HTTPException(status_code=400, detail="run_id or start/end is required")
    return FlowResponse(
        ok=False,
        data={
            "code": "server_first_migration_pending",
            "message": "FNL verification moved to smanager-server repair requests.",
            "requested": payload.model_dump(),
        },
    )


@router.post("/repair", response_model=FlowResponse, status_code=status.HTTP_202_ACCEPTED)
def repair_fnl(payload: FnlRepairRequest):
    if not payload.run_id and (not payload.start or not payload.end):
        raise HTTPException(status_code=400, detail="run_id or start/end is required")
    return FlowResponse(
        ok=False,
        data={
            "code": "server_first_migration_pending",
            "message": "Local FNL repair will be rebuilt as a Docker worker against server repair requests.",
            "requested": payload.model_dump(),
        },
    )


@router.get("/coverage", response_model=FlowResponse)
def fnl_coverage(
    start: str | None = None,
    end: str | None = None,
    status_filter: str | None = Query(default=None, alias="status"),
    needs_repair: bool | None = None,
    limit: int = Query(default=500, ge=1, le=5000),
    db: Session = Depends(get_db),
):
    query = db.query(FnlFileRecord)
    if start:
        query = query.filter(FnlFileRecord.valid_time >= start)
    if end:
        query = query.filter(FnlFileRecord.valid_time <= end)
    if status_filter:
        query = query.filter(FnlFileRecord.status == status_filter)
    if needs_repair is True:
        query = query.filter(FnlFileRecord.status != "server_ok")
    elif needs_repair is False:
        query = query.filter(FnlFileRecord.status == "server_ok")
    records = query.order_by(FnlFileRecord.valid_time.asc()).limit(limit).all()
    return FlowResponse(data={"files": [serialize_fnl_record(item) for item in records], "source": "mysql"})


def serialize_fnl_record(item: FnlFileRecord) -> dict:
    return {
        "valid_time": item.valid_time,
        "file_name": item.file_name,
        "status": item.status,
        "needs_repair": item.status != "server_ok",
        "source": item.source,
        "server_path": item.server_path,
        "local_path": item.local_path,
        "size_bytes": item.size_bytes,
        "valid_grib": item.valid_grib,
        "uploaded": item.uploaded,
        "repair_attempt": item.repair_attempt,
        "error_message": item.error_message,
        "checked_at": item.checked_at,
    }
