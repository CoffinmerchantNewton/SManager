from __future__ import annotations

from datetime import datetime, timezone

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
from ..services.server_client import server_client
from ..services.server_runs import (
    collect_log_tails,
    parse_run_key,
    run_log_candidates,
    serialize_server_run,
    sort_runs_newest_first,
)

router = APIRouter()


def _server_payload(result) -> dict:
    return {
        "source": result.source,
        "stale": result.stale,
        "error": result.error,
    }


@router.post("/", response_model=FlowResponse, status_code=status.HTTP_202_ACCEPTED)
def plan_run(payload: RunPlanRequest):
    start_date = payload.start[:8]
    result = server_client.tick(force=False, start_date=start_date)
    return FlowResponse(
        ok=not result.stale,
        data={
            **_server_payload(result),
            "message": "已转发至 smanager-server tick",
            "requested": payload.model_dump(),
            "tick": result.data,
        },
    )


@router.get("/", response_model=FlowResponse)
def list_runs(
    status_filter: str | None = Query(default=None, alias="status"),
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    if server_client.configured:
        result = server_client.list_runs(limit=limit)
        runs = sort_runs_newest_first([serialize_server_run(item) for item in (result.data or [])])
        if status_filter:
            runs = [item for item in runs if item["status"] == status_filter]
        return FlowResponse(
            ok=not result.stale,
            data={"runs": runs, **_server_payload(result)},
        )

    query = db.query(ForecastRun)
    if status_filter:
        query = query.filter(ForecastRun.status == status_filter)
    runs = query.order_by(ForecastRun.created_at.desc()).limit(limit).all()
    return FlowResponse(data={"runs": [serialize_run(run) for run in runs], "source": "mysql"})


@router.get("/{run_key:path}/status", response_model=FlowResponse)
def get_run_status(run_key: str, db: Session = Depends(get_db)):
    if server_client.configured:
        try:
            season, region, run_id = parse_run_key(run_key)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        result = server_client.run_detail_live(season, region, run_id)
        payload = serialize_server_run(result.data or {})
        return FlowResponse(
            ok=not result.stale,
            data={
                **payload,
                "source": result.source,
                "stale": result.stale,
                "error": result.error,
            },
        )

    run = require_run(db, run_key)
    nodes = (
        db.query(ForecastRunNode)
        .filter(ForecastRunNode.run_id == run_key)
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


@router.post("/{run_key:path}/fnl-verify", response_model=FlowResponse, status_code=status.HTTP_202_ACCEPTED)
def verify_run_fnl(run_key: str):
    try:
        _, _, run_id = parse_run_key(run_key)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    start_date = run_id[:8]
    result = server_client.fnl_scan(start_date)
    scan = result.data or {}
    return FlowResponse(
        ok=not result.stale and not scan.get("missing"),
        data={
            **_server_payload(result),
            "run_key": run_key,
            "scan": scan,
        },
    )


@router.post("/{run_key:path}/submit", response_model=FlowResponse, status_code=status.HTTP_202_ACCEPTED)
def submit_run(run_key: str, payload: RunSubmitRequest):
    try:
        season, region, run_id = parse_run_key(run_key)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if payload.dry_run:
        result = server_client.run_detail(season, region, run_id)
        return FlowResponse(
            ok=True,
            data={
                "dry_run": True,
                "run_key": run_key,
                "run": serialize_server_run(result.data or {}),
                **_server_payload(result),
            },
        )
    result = server_client.tick(force=True, start_date=run_id[:8])
    return FlowResponse(
        ok=not result.stale,
        data={
            "run_key": run_key,
            "tick": result.data,
            **_server_payload(result),
        },
    )


@router.get("/{run_key:path}/logs", response_model=LogsResponse)
def get_run_logs(
    run_key: str,
    node: str | None = None,
    tail: int = Query(default=200, ge=1, le=2000),
):
    if not server_client.configured:
        return LogsResponse(run_id=run_key, node=node, logs="SERVER_API_BASE_URL 未配置。")

    try:
        season, region, run_id = parse_run_key(run_key)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    result = server_client.run_detail(season, region, run_id)
    run = result.data or {}
    logs: list[str] = []
    for entry in collect_log_tails(run, lines=tail, tail_file=server_client.tail_file):
        if node and node not in {entry["name"], entry["path"]}:
            continue
        tail_lines = entry.get("tail") or []
        if tail_lines and not str(tail_lines[0]).startswith("[skip]"):
            logs.append(f"=== {entry['name']} ({entry['path']}) ===")
            logs.extend(tail_lines)
    if not logs:
        logs = ["未找到可读取的日志文件，请确认 run 目录下 wrf/rsl.error.0000 是否存在。"]
    return LogsResponse(run_id=run_key, node=node, logs="\n".join(logs))


@router.get("/{run_key:path}/events", response_model=FlowResponse)
def get_run_events(
    run_key: str,
    node: str | None = None,
    level: str | None = None,
    event_type: str | None = None,
    limit: int = Query(default=200, ge=1, le=5000),
    db: Session = Depends(get_db),
):
    query = db.query(ForecastRunEvent).filter(ForecastRunEvent.run_id == run_key)
    if node:
        query = query.filter(ForecastRunEvent.node_name == node)
    if level:
        query = query.filter(ForecastRunEvent.level == level)
    if event_type:
        query = query.filter(ForecastRunEvent.event_type == event_type)
    events = query.order_by(ForecastRunEvent.id.desc()).limit(limit).all()
    return FlowResponse(data={"run_id": run_key, "events": [serialize_event(event) for event in events], "source": "mysql"})


@router.get("/{run_key:path}/diagnose", response_model=FlowResponse)
def diagnose_run(run_key: str):
    if not server_client.configured:
        return not_migrated("diagnostics require smanager-server", {"run_key": run_key})

    try:
        season, region, run_id = parse_run_key(run_key)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    result = server_client.run_detail(season, region, run_id)
    run = serialize_server_run(result.data or {})
    findings: list[dict] = []
    for job in run.get("slurm_jobs") or []:
        state = str(job.get("state") or "").upper()
        if state not in {"COMPLETED", "RUNNING", "PENDING", "CONFIGURING"}:
            findings.append(
                {
                    "node": "slurm",
                    "code": state.lower(),
                    "message": f"Slurm job {job.get('job_id')} is {state}",
                    "suggested_action": "inspect_logs",
                }
            )
    for anomaly in run.get("anomalies") or []:
        findings.append(
            {
                "node": "reconcile",
                "code": "anomaly",
                "message": str(anomaly),
                "suggested_action": "inspect_logs",
            }
        )
    for node in run.get("nodes") or []:
        if node.get("status") == "error":
            findings.append(
                {
                    "node": node.get("node"),
                    "code": "node_error",
                    "message": node.get("message") or "node failed",
                    "suggested_action": "inspect_logs",
                }
            )
    return FlowResponse(
        ok=len(findings) == 0,
        data={"findings": findings, "run": run, **_server_payload(result)},
    )


@router.get("/{run_key:path}/context", response_model=FlowResponse)
def collect_run_context(
    run_key: str,
    event_limit: int = Query(default=100, ge=1, le=5000),
    tail: int = Query(default=120, ge=1, le=500),
    db: Session = Depends(get_db),
):
    if server_client.configured:
        try:
            season, region, run_id = parse_run_key(run_key)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        result = server_client.run_detail_live(season, region, run_id)
        run = serialize_server_run(result.data or {})
        log_entries = collect_log_tails(run, lines=tail, tail_file=server_client.tail_file)

        return FlowResponse(
            ok=not result.stale,
            data={
                "run_id": run_key,
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "run_dir": run.get("server_run_dir"),
                "status": {
                    "run_id": run_key,
                    "status": run.get("status"),
                    "progress": run.get("progress"),
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                    "nodes": run.get("nodes") or [],
                },
                "events": [],
                "logs": log_entries,
                "slurm_jobs": run.get("slurm_jobs") or [],
                "state": run.get("state") or {},
                "effective_state": run.get("effective_state") or {},
                "failure": run.get("failure"),
                "anomalies": run.get("anomalies") or [],
                "source": result.source,
                "stale": result.stale,
                "error": result.error,
            },
        )

    run = require_run(db, run_key)
    nodes = (
        db.query(ForecastRunNode)
        .filter(ForecastRunNode.run_id == run_key)
        .order_by(ForecastRunNode.id.asc())
        .all()
    )
    events = (
        db.query(ForecastRunEvent)
        .filter(ForecastRunEvent.run_id == run_key)
        .order_by(ForecastRunEvent.id.desc())
        .limit(event_limit)
        .all()
    )
    products = (
        db.query(ForecastProduct)
        .filter(ForecastProduct.product_name.like(f"{run_key}:%"))
        .order_by(ForecastProduct.release_time.desc())
        .all()
    )
    actions = (
        db.query(AgentAction)
        .filter(AgentAction.run_id == run_key)
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


@router.post("/{run_key:path}/retry", response_model=FlowResponse, status_code=status.HTTP_202_ACCEPTED)
def retry_run_node(run_key: str, payload: RetryRequest):
    return not_migrated(
        "node retry will be a whitelisted smanager-server action",
        {"run_key": run_key, "requested": payload.model_dump()},
    )


@router.post("/{run_key:path}/cancel", response_model=FlowResponse, status_code=status.HTTP_202_ACCEPTED)
def cancel_run(run_key: str, payload: CancelRunRequest):
    return not_migrated(
        "run cancellation will be a whitelisted smmanager-server action",
        {"run_key": run_key, "requested": payload.model_dump()},
    )


@router.get("/{run_key:path}/products", response_model=FlowResponse)
def get_run_products(run_key: str, db: Session = Depends(get_db)):
    products = (
        db.query(ForecastProduct)
        .filter(ForecastProduct.product_name.like(f"%{run_key.split('/')[-1]}%"))
        .order_by(ForecastProduct.release_time.desc())
        .all()
    )
    return FlowResponse(data={"run_id": run_key, "products": [serialize_product(product) for product in products]})


@router.post("/{run_key:path}/sync-products", response_model=FlowResponse, status_code=status.HTTP_202_ACCEPTED)
def sync_run_products(run_key: str):
    return not_migrated("product sync will be rebuilt on top of the new tunnel/server API", {"run_key": run_key})


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
    import json

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


def serialize_action(action) -> dict:
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
    import json

    if not value:
        return None
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return None


def iso_or_none(value) -> str | None:
    return value.isoformat() if value else None
