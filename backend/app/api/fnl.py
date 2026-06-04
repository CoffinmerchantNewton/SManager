from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..core.database import get_db
from ..models.models import FnlFileRecord
from ..schemas.run_control import FnlRepairRequest, FnlVerifyRequest, FlowResponse
from ..services.fnl import FnlRepairService

router = APIRouter()


@router.post("/verify-server", response_model=FlowResponse)
def verify_server_fnl(payload: FnlVerifyRequest, db: Session = Depends(get_db)):
    if not payload.run_id and (not payload.start or not payload.end):
        raise HTTPException(status_code=400, detail="run_id or start/end is required")
    result = FnlRepairService(db).verify_server(run_id=payload.run_id, start=payload.start, end=payload.end)
    return FlowResponse(ok=bool(result.get("ok", result.get("_exit_code") == 0)), data=result)


@router.post("/repair", response_model=FlowResponse)
def repair_fnl(payload: FnlRepairRequest, db: Session = Depends(get_db)):
    if not payload.run_id and (not payload.start or not payload.end):
        raise HTTPException(status_code=400, detail="run_id or start/end is required")
    result = FnlRepairService(db).repair(run_id=payload.run_id, start=payload.start, end=payload.end)
    return FlowResponse(ok=bool(result.get("ok")), data=result)


@router.get("/coverage", response_model=FlowResponse)
def fnl_coverage(
    start: str | None = None,
    end: str | None = None,
    status: str | None = None,
    limit: int = Query(default=500, ge=1, le=5000),
    db: Session = Depends(get_db),
):
    query = db.query(FnlFileRecord)
    if start:
        query = query.filter(FnlFileRecord.valid_time >= start)
    if end:
        query = query.filter(FnlFileRecord.valid_time <= end)
    if status:
        query = query.filter(FnlFileRecord.status == status)
    records = query.order_by(FnlFileRecord.valid_time.asc()).limit(limit).all()
    return FlowResponse(
        data={
            "files": [
                {
                    "valid_time": item.valid_time,
                    "file_name": item.file_name,
                    "status": item.status,
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
                for item in records
            ]
        }
    )
