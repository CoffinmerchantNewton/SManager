from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..core.database import get_db
from ..models.models import ForecastRun, ForecastRunNode, ForecastRunStatus
from ..schemas.run_control import (
    CancelRunRequest,
    FlowResponse,
    LogsResponse,
    RetryRequest,
    RunPlanRequest,
    RunSubmitRequest,
)
from ..services.events import RunEventService
from ..services.flow import ServerFlowService
from ..services.products import ProductSyncService

router = APIRouter()


def service() -> ServerFlowService:
    return ServerFlowService()


@router.post("/", response_model=FlowResponse)
def plan_run(payload: RunPlanRequest, db: Session = Depends(get_db)):
    result = service().plan(**payload.model_dump())
    run_id = result.get("run_id") or payload.run_id
    if run_id:
        run = db.query(ForecastRun).filter(ForecastRun.run_id == run_id).first()
        if not run:
            run = ForecastRun(run_id=run_id)
            db.add(run)
        run.start_time = payload.start
        run.end_time = payload.end
        run.period = payload.period
        run.domain = payload.domain
        run.variant = payload.variant
        run.met_provider = payload.met_provider
        run.status = ForecastRunStatus.PENDING
        run.server_run_dir = result.get("run_dir")
        db.commit()
    return FlowResponse(data=result)


@router.get("/", response_model=FlowResponse)
def list_runs(
    status: str | None = None,
    limit: int = Query(default=100, ge=1, le=5000),
    sync: bool = True,
    db: Session = Depends(get_db),
):
    result = service().list_runs()
    runs = result.get("runs", [])
    synced_count = sync_run_list(db, runs) if sync else 0
    if status:
        runs = [item for item in runs if item.get("status") == status]
    runs = runs[:limit]
    result["runs"] = runs
    result["synced_count"] = synced_count
    return FlowResponse(data=result)


@router.get("/{run_id}/status", response_model=FlowResponse)
def get_run_status(run_id: str, db: Session = Depends(get_db)):
    result = service().status(run_id)
    sync_run_status(db, run_id, result)
    return FlowResponse(data=result)


@router.post("/{run_id}/fnl-verify", response_model=FlowResponse)
def verify_run_fnl(run_id: str):
    result = service().fnl_verify(run_id=run_id)
    return FlowResponse(ok=bool(result.get("ok", result.get("_exit_code") == 0)), data=result)


@router.post("/{run_id}/submit", response_model=FlowResponse)
def submit_run(run_id: str, payload: RunSubmitRequest, db: Session = Depends(get_db)):
    flow = service()
    result = flow.submit(run_id, dry_run=payload.dry_run, allow_noop=payload.allow_noop)
    ok = bool(result.get("ok", result.get("_exit_code") == 0))
    if not ok and result.get("error"):
        raise HTTPException(status_code=400, detail=result)
    sync_status_after_action(db, flow, run_id, result)
    return FlowResponse(data=result)


@router.get("/{run_id}/logs", response_model=LogsResponse)
def get_run_logs(
    run_id: str,
    node: str | None = None,
    tail: int = Query(default=200, ge=1, le=5000),
):
    return LogsResponse(run_id=run_id, node=node, logs=service().logs(run_id, node=node, tail=tail))


@router.get("/{run_id}/events", response_model=FlowResponse)
def get_run_events(
    run_id: str,
    node: str | None = None,
    level: str | None = None,
    event_type: str | None = None,
    limit: int = Query(default=200, ge=1, le=5000),
    sync: bool = True,
    db: Session = Depends(get_db),
):
    events = RunEventService(db)
    sync_result = None
    if sync:
        sync_result = events.sync(run_id, tail=limit, node=node, level=level, event_type=event_type)
    return FlowResponse(
        ok=bool(sync_result.get("ok", True)) if sync_result else True,
        data={
            "run_id": run_id,
            "events": events.list_events(run_id, limit=limit, node=node, level=level, event_type=event_type),
            "sync": sync_result,
        },
    )


@router.get("/{run_id}/diagnose", response_model=FlowResponse)
def diagnose_run(run_id: str):
    return FlowResponse(data=service().diagnose(run_id))


@router.get("/{run_id}/context", response_model=FlowResponse)
def collect_run_context(
    run_id: str,
    tail: int = Query(default=120, ge=1, le=5000),
    event_limit: int = Query(default=100, ge=1, le=5000),
    max_logs: int = Query(default=12, ge=1, le=100),
):
    result = service().collect_context(run_id, tail=tail, event_limit=event_limit, max_logs=max_logs)
    return FlowResponse(ok=bool(result.get("ok", result.get("_exit_code") == 0)), data=result)


@router.post("/{run_id}/retry", response_model=FlowResponse)
def retry_run_node(run_id: str, payload: RetryRequest, db: Session = Depends(get_db)):
    flow = service()
    result = flow.retry(run_id, node=payload.node, dry_run=payload.dry_run)
    sync_status_after_action(db, flow, run_id, result)
    return FlowResponse(ok=bool(result.get("ok", result.get("_exit_code") == 0)), data=result)


@router.post("/{run_id}/cancel", response_model=FlowResponse)
def cancel_run(run_id: str, payload: CancelRunRequest, db: Session = Depends(get_db)):
    flow = service()
    result = flow.cancel(run_id, dry_run=payload.dry_run)
    sync_status_after_action(db, flow, run_id, result)
    return FlowResponse(ok=bool(result.get("ok", result.get("_exit_code") == 0)), data=result)


@router.get("/{run_id}/products", response_model=FlowResponse)
def get_run_products(run_id: str):
    return FlowResponse(data=service().products(run_id))


@router.post("/{run_id}/sync-products", response_model=FlowResponse)
def sync_run_products(run_id: str, db: Session = Depends(get_db)):
    result = ProductSyncService(db).sync(run_id)
    return FlowResponse(ok=bool(result.get("ok")), data=result)


def sync_run_status(db: Session, run_id: str, workflow: dict) -> None:
    run = db.query(ForecastRun).filter(ForecastRun.run_id == run_id).first()
    if not run:
        run = ForecastRun(run_id=run_id)
        db.add(run)
    status = workflow.get("status") or "pending"
    try:
        run.status = ForecastRunStatus(status)
    except ValueError:
        run.status = ForecastRunStatus.PENDING
    run.progress = float(workflow.get("progress") or 0)
    for node in workflow.get("nodes", []):
        item = (
            db.query(ForecastRunNode)
            .filter(ForecastRunNode.run_id == run_id, ForecastRunNode.node_name == node.get("node"))
            .first()
        )
        if not item:
            item = ForecastRunNode(run_id=run_id, node_name=node.get("node"))
            db.add(item)
        item.status = node.get("status")
        item.progress = float(node.get("progress") or 0)
        item.attempt = int(node.get("attempt") or 0)
        item.slurm_job_id = node.get("slurm_job_id")
        item.error_code = node.get("error_code")
        item.message = node.get("message")
    db.commit()


def sync_run_list(db: Session, runs: list[dict]) -> int:
    count = 0
    for workflow in runs:
        run_id = workflow.get("run_id")
        if not run_id:
            continue
        sync_run_status(db, run_id, workflow)
        count += 1
    return count


def sync_status_after_action(db: Session, flow: ServerFlowService, run_id: str, result: dict) -> None:
    ok = bool(result.get("ok", result.get("_exit_code") == 0))
    if not ok or result.get("dry_run") or result.get("no_op"):
        return
    sync_run_status(db, run_id, flow.status(run_id))
