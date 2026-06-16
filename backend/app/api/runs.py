from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from ..core.database import get_db
from ..models.models import (
    AgentAction,
    ForecastProduct,
    ForecastRun,
    ForecastRunEvent,
    ForecastRunNode,
    ForecastRunStatus,
)
from ..schemas.run_control import (
    CancelRunRequest,
    FlowResponse,
    LogsResponse,
    RetryRequest,
    RunPlanRequest,
    RunSubmitRequest,
)

router = APIRouter()


@router.post("/", response_model=FlowResponse, status_code=status.HTTP_202_ACCEPTED)
def plan_run(payload: RunPlanRequest):
    return not_migrated(
        "run planning moved to the server-owned smanager-server daemon",
        {"requested": payload.model_dump()},
    )


@router.get("/", response_model=FlowResponse)
def list_runs(
    status_filter: str | None = Query(default=None, alias="status"),
    limit: int = Query(default=100, ge=1, le=5000),
    db: Session = Depends(get_db),
):
    query = db.query(ForecastRun)
    if status_filter:
        query = query.filter(ForecastRun.status == status_filter)
    runs = query.order_by(ForecastRun.created_at.desc()).limit(limit).all()
    return FlowResponse(data={"runs": [serialize_run(run) for run in runs], "source": "mysql"})


@router.get("/{run_id}/status", response_model=FlowResponse)
def get_run_status(run_id: str, db: Session = Depends(get_db)):
    run = require_run(db, run_id)
    nodes = (
        db.query(ForecastRunNode)
        .filter(ForecastRunNode.run_id == run_id)
        .order_by(ForecastRunNode.id.asc())
        .all()
    )
    return FlowResponse(
        data={
            **serialize_run(run),
            "nodes": [serialize_node(node) for node in nodes],
            "source": "mysql",
        }
    )


@router.post("/{run_id}/fnl-verify", response_model=FlowResponse, status_code=status.HTTP_202_ACCEPTED)
def verify_run_fnl(run_id: str):
    return not_migrated("FNL verification will be handled by smanager-server repair requests", {"run_id": run_id})


@router.post("/{run_id}/submit", response_model=FlowResponse, status_code=status.HTTP_202_ACCEPTED)
def submit_run(run_id: str, payload: RunSubmitRequest):
    return not_migrated(
        "run submission moved to the server-owned smanager-server daemon",
        {"run_id": run_id, "requested": payload.model_dump()},
    )


@router.get("/{run_id}/logs", response_model=LogsResponse)
def get_run_logs(run_id: str, node: str | None = None):
    return LogsResponse(run_id=run_id, node=node, logs="Server log proxy is pending the new tunnel/server API.")


@router.get("/{run_id}/events", response_model=FlowResponse)
def get_run_events(
    run_id: str,
    node: str | None = None,
    level: str | None = None,
    event_type: str | None = None,
    limit: int = Query(default=200, ge=1, le=5000),
    db: Session = Depends(get_db),
):
    query = db.query(ForecastRunEvent).filter(ForecastRunEvent.run_id == run_id)
    if node:
        query = query.filter(ForecastRunEvent.node_name == node)
    if level:
        query = query.filter(ForecastRunEvent.level == level)
    if event_type:
        query = query.filter(ForecastRunEvent.event_type == event_type)
    events = query.order_by(ForecastRunEvent.id.desc()).limit(limit).all()
    return FlowResponse(data={"run_id": run_id, "events": [serialize_event(event) for event in events]})


@router.get("/{run_id}/diagnose", response_model=FlowResponse, status_code=status.HTTP_202_ACCEPTED)
def diagnose_run(run_id: str):
    return not_migrated("diagnostics will be rebuilt after the new server daemon is in place", {"run_id": run_id})


@router.get("/{run_id}/context", response_model=FlowResponse)
def collect_run_context(
    run_id: str,
    event_limit: int = Query(default=100, ge=1, le=5000),
    db: Session = Depends(get_db),
):
    run = require_run(db, run_id)
    nodes = (
        db.query(ForecastRunNode)
        .filter(ForecastRunNode.run_id == run_id)
        .order_by(ForecastRunNode.id.asc())
        .all()
    )
    events = (
        db.query(ForecastRunEvent)
        .filter(ForecastRunEvent.run_id == run_id)
        .order_by(ForecastRunEvent.id.desc())
        .limit(event_limit)
        .all()
    )
    products = (
        db.query(ForecastProduct)
        .filter(ForecastProduct.product_name.like(f"{run_id}:%"))
        .order_by(ForecastProduct.release_time.desc())
        .all()
    )
    actions = (
        db.query(AgentAction)
        .filter(AgentAction.run_id == run_id)
        .order_by(AgentAction.id.desc())
        .limit(50)
        .all()
    )
    return FlowResponse(
        data={
            "run": serialize_run(run),
            "nodes": [serialize_node(node) for node in nodes],
            "events": [serialize_event(event) for event in events],
            "products": [serialize_product(product) for product in products],
            "actions": [serialize_action(action) for action in actions],
            "source": "mysql",
        }
    )


@router.post("/{run_id}/retry", response_model=FlowResponse, status_code=status.HTTP_202_ACCEPTED)
def retry_run_node(run_id: str, payload: RetryRequest):
    return not_migrated(
        "node retry will be a whitelisted smanager-server action",
        {"run_id": run_id, "requested": payload.model_dump()},
    )


@router.post("/{run_id}/cancel", response_model=FlowResponse, status_code=status.HTTP_202_ACCEPTED)
def cancel_run(run_id: str, payload: CancelRunRequest):
    return not_migrated(
        "run cancellation will be a whitelisted smanager-server action",
        {"run_id": run_id, "requested": payload.model_dump()},
    )


@router.get("/{run_id}/products", response_model=FlowResponse)
def get_run_products(run_id: str, db: Session = Depends(get_db)):
    products = (
        db.query(ForecastProduct)
        .filter(ForecastProduct.product_name.like(f"{run_id}:%"))
        .order_by(ForecastProduct.release_time.desc())
        .all()
    )
    return FlowResponse(data={"run_id": run_id, "products": [serialize_product(product) for product in products]})


@router.post("/{run_id}/sync-products", response_model=FlowResponse, status_code=status.HTTP_202_ACCEPTED)
def sync_run_products(run_id: str):
    return not_migrated("product sync will be rebuilt on top of the new tunnel/server API", {"run_id": run_id})


def require_run(db: Session, run_id: str) -> ForecastRun:
    run = db.query(ForecastRun).filter(ForecastRun.run_id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return run


def not_migrated(message: str, data: dict | None = None) -> FlowResponse:
    return FlowResponse(ok=False, data={"code": "server_first_migration_pending", "message": message, **(data or {})})


def status_value(value) -> str:
    if isinstance(value, ForecastRunStatus):
        return value.value
    return str(value or ForecastRunStatus.PENDING.value)


def serialize_run(run: ForecastRun) -> dict:
    return {
        "id": run.id,
        "run_id": run.run_id,
        "start_time": run.start_time,
        "end_time": run.end_time,
        "period": run.period,
        "domain": run.domain,
        "variant": run.variant,
        "met_provider": run.met_provider,
        "status": status_value(run.status),
        "progress": float(run.progress or 0),
        "server_run_dir": run.server_run_dir,
        "last_error": run.last_error,
        "created_at": iso_or_none(run.created_at),
        "updated_at": iso_or_none(run.updated_at),
    }


def serialize_node(node: ForecastRunNode) -> dict:
    return {
        "id": node.id,
        "run_id": node.run_id,
        "node": node.node_name,
        "status": node.status,
        "progress": float(node.progress or 0),
        "attempt": int(node.attempt or 0),
        "slurm_job_id": node.slurm_job_id,
        "error_code": node.error_code,
        "message": node.message or "",
        "wrfout_progress": parse_json_or_none(node.wrfout_progress_json),
        "updated_at": iso_or_none(node.updated_at),
    }


def serialize_event(event: ForecastRunEvent) -> dict:
    return {
        "id": event.id,
        "event_key": event.event_key,
        "run_id": event.run_id,
        "node": event.node_name,
        "event_type": event.event_type,
        "level": event.level,
        "message": event.message,
        "payload": parse_json_or_none(event.payload_json),
        "created_at": event.created_at,
        "synced_at": iso_or_none(event.synced_at),
    }


def serialize_product(product: ForecastProduct) -> dict:
    return {
        "id": product.id,
        "name": product.product_name,
        "type": product.product_type,
        "subtype": product.subtype,
        "variable": product.variable,
        "unit": product.unit,
        "path": product.file_path,
        "status": product.status.value if hasattr(product.status, "value") else product.status,
        "release_time": iso_or_none(product.release_time),
    }


def serialize_action(action: AgentAction) -> dict:
    return {
        "id": action.id,
        "run_id": action.run_id,
        "action_type": action.action_type,
        "reason": action.reason,
        "status": action.status,
        "input": parse_json_or_none(action.input_json),
        "output": parse_json_or_none(action.output_json),
        "created_at": iso_or_none(action.created_at),
        "finished_at": iso_or_none(action.finished_at),
    }


def parse_json_or_none(value: str | None):
    if not value:
        return None
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return None


def iso_or_none(value) -> str | None:
    return value.isoformat() if value else None
