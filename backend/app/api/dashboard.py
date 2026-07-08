from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, Query
from sqlalchemy.orm import Session

from ..core.database import get_db
from ..models.models import (
    AgentAction,
    ForecastProduct,
    ForecastRun,
    ForecastRunNode,
    ForecastRunStatus,
    ProductStatus,
    ScheduledTask,
    SystemLog,
    TaskStatus,
)
from ..schemas.schemas import DashboardStats, SystemLogResponse
from ..services.server_client import server_client
from ..services.server_runs import serialize_server_run, sort_runs_newest_first

router = APIRouter()


@router.get("/stats", response_model=DashboardStats)
def get_dashboard_stats(db: Session = Depends(get_db)):
    if server_client.configured:
        return build_server_dashboard_stats(db)
    return build_dashboard_stats(db)


@router.get("/overview")
def get_dashboard_overview(
    background_tasks: BackgroundTasks,
    recent_limit: int = Query(default=8, ge=1, le=50),
    db: Session = Depends(get_db),
):
    if server_client.configured:
        return build_server_overview(db, recent_limit, background_tasks)

    recent_runs = (
        db.query(ForecastRun)
        .order_by(ForecastRun.created_at.desc())
        .limit(recent_limit)
        .all()
    )
    latest_products = (
        db.query(ForecastProduct)
        .filter(ForecastProduct.status == ProductStatus.READY)
        .order_by(ForecastProduct.release_time.desc())
        .limit(recent_limit)
        .all()
    )
    latest_actions = db.query(AgentAction).order_by(AgentAction.created_at.desc()).limit(recent_limit).all()
    logs = db.query(SystemLog).order_by(SystemLog.timestamp.desc()).limit(recent_limit).all()
    return {
        "stats": dashboard_stats_to_dict(build_dashboard_stats(db)),
        "runs": [serialize_run(item) for item in recent_runs],
        "products": {
            "total": db.query(ForecastProduct).count(),
            "ready": db.query(ForecastProduct).filter(ForecastProduct.status == ProductStatus.READY).count(),
            "error": db.query(ForecastProduct).filter(ForecastProduct.status == ProductStatus.ERROR).count(),
            "latest": [serialize_product(item) for item in latest_products],
        },
        "fnl": build_fnl_summary(db),
        "actions": [serialize_action(item) for item in latest_actions],
        "logs": [serialize_log(item) for item in logs],
        "source": "mysql",
    }


def build_server_overview(db: Session, recent_limit: int, background_tasks: BackgroundTasks | None = None) -> dict:
    daemon_result = server_client.daemon_status()
    config_result = server_client.get_config()
    run_limit = max(recent_limit, 100)
    runs_result = server_client.list_runs(limit=run_limit, prefer_cache=True)
    if runs_result.source == "cache" and background_tasks is not None:
        background_tasks.add_task(server_client.refresh_runs_cache, run_limit)
    repair_result = server_client.repair_requests(status="pending")

    daemon = daemon_result.data or {}
    config = config_result.data if isinstance(config_result.data, dict) else {}
    forecast = config.get("forecast") or {}
    schedule = config.get("schedule") or {}
    runs = sort_runs_newest_first([serialize_server_run(item) for item in (runs_result.data or [])])
    runs = runs[:recent_limit]
    pending_repairs = repair_result.data or []

    latest_products = (
        db.query(ForecastProduct)
        .filter(ForecastProduct.status == ProductStatus.READY)
        .order_by(ForecastProduct.release_time.desc())
        .limit(recent_limit)
        .all()
    )

    stats = build_server_dashboard_stats(db, daemon=daemon, runs=runs_result.data or [], pending_repairs=pending_repairs)
    server_logs = []
    tick_detail = (daemon.get("last_tick_result") or "")
    if tick_detail:
        server_logs.append(
            {
                "id": 0,
                "level": "INFO",
                "message": f"last_tick_result={tick_detail}",
                "source": "smanager-server",
                "timestamp": daemon.get("last_tick_at"),
            }
        )

    return {
        "stats": dashboard_stats_to_dict(stats),
        "server": {
            "daemon": daemon,
            "config": {
                "season": forecast.get("season"),
                "regions": forecast.get("regions") or [],
                "schedule_enabled": schedule.get("enabled", daemon.get("schedule_enabled")),
                "tick_time": schedule.get("tick_time"),
                "timezone": schedule.get("timezone"),
            },
            "source": daemon_result.source,
            "stale": bool(daemon_result.error or config_result.error),
            "server_time_local": daemon.get("server_time_local"),
            "server_time_utc": daemon.get("server_time_utc"),
        },
        "runs": [
            {
                "run_key": item["run_key"],
                "run_id": item["run_id"],
                "status": item["status"],
                "progress": item["progress"],
                "start_time": item["start_date"],
                "end_time": None,
                "period": item["season"],
                "domain": item["region"],
                "variant": item.get("variant") or "",
                "pre": item.get("pre"),
                "server_run_dir": item["server_run_dir"],
                "last_error": item.get("last_error"),
                "anomalies": item.get("anomalies") or [],
                "slurm_jobs": item.get("slurm_jobs") or [],
                "slurm_job_ids": item.get("slurm_job_ids") or [],
                "slurm_active_count": item.get("slurm_active_count") or 0,
            }
            for item in runs
        ],
        "products": {
            "total": db.query(ForecastProduct).count(),
            "ready": db.query(ForecastProduct).filter(ForecastProduct.status == ProductStatus.READY).count(),
            "error": db.query(ForecastProduct).filter(ForecastProduct.status == ProductStatus.ERROR).count(),
            "latest": [serialize_product(item) for item in latest_products],
        },
        "fnl": {
            "total": len(pending_repairs),
            "server_ok": 0,
            "uploaded": sum(1 for item in pending_repairs if item.get("status") in {"uploaded", "verified", "completed"}),
            "needs_repair": len(pending_repairs),
            "pending_requests": pending_repairs[:recent_limit],
        },
        "actions": [],
        "logs": server_logs,
        "source": runs_result.source,
        "stale": bool(
            runs_result.error
            or daemon_result.error
            or config_result.error
            or repair_result.error
        ),
    }


def build_server_dashboard_stats(
    db: Session,
    *,
    daemon: dict | None = None,
    runs: list | None = None,
    pending_repairs: list | None = None,
) -> DashboardStats:
    if daemon is None:
        daemon = (server_client.daemon_status().data or {})
    if runs is None:
        runs = server_client.list_runs(limit=100).data or []
    if pending_repairs is None:
        pending_repairs = server_client.repair_requests(status="pending").data or []

    serialized = [serialize_server_run(item) for item in runs]
    total_runs = len(serialized)
    running_runs = sum(1 for item in serialized if item["status"] == "running")
    failed_runs = sum(1 for item in serialized if item["status"] == "error")
    queued_nodes = sum(len(item.get("slurm_jobs") or []) for item in serialized)

    active_tasks = db.query(ScheduledTask).filter(ScheduledTask.status == TaskStatus.ACTIVE).count()
    health = calculate_system_health(total_runs, failed_runs, running_runs)
    if len(pending_repairs) > 0:
        health = max(0.0, health - min(30.0, len(pending_repairs) * 2))

    return DashboardStats(
        active_schedulers=active_tasks,
        slurm_jobs_queued=queued_nodes,
        system_health=health,
        total_workflows=total_runs or int(daemon.get("active_runs") or 0),
        running_workflows=running_runs,
        failed_workflows=failed_runs,
    )


def build_dashboard_stats(db: Session) -> DashboardStats:
    active_tasks = db.query(ScheduledTask).filter(ScheduledTask.status == TaskStatus.ACTIVE).count()
    total_runs = db.query(ForecastRun).count()
    running_runs = (
        db.query(ForecastRun)
        .filter(ForecastRun.status.in_([ForecastRunStatus.RUNNING, ForecastRunStatus.RETRYING]))
        .count()
    )
    failed_runs = db.query(ForecastRun).filter(ForecastRun.status == ForecastRunStatus.ERROR).count()
    queued_nodes = (
        db.query(ForecastRunNode)
        .filter(
            ForecastRunNode.slurm_job_id.isnot(None),
            ForecastRunNode.status.in_(["ready", "running", "retrying"]),
        )
        .count()
    )

    return DashboardStats(
        active_schedulers=active_tasks,
        slurm_jobs_queued=queued_nodes,
        system_health=calculate_system_health(total_runs, failed_runs, running_runs),
        total_workflows=total_runs,
        running_workflows=running_runs,
        failed_workflows=failed_runs,
    )


def calculate_system_health(total_runs: int, failed_runs: int, running_runs: int) -> float:
    if total_runs <= 0:
        return 100.0
    failure_penalty = failed_runs / total_runs * 70
    pressure_penalty = min(running_runs, 5) * 2
    return round(max(0.0, 100.0 - failure_penalty - pressure_penalty), 1)


def dashboard_stats_to_dict(stats: DashboardStats) -> dict:
    if hasattr(stats, "model_dump"):
        return stats.model_dump()
    return stats.dict()


def build_fnl_summary(db: Session) -> dict:
    from ..models.models import FnlFileRecord

    total = db.query(FnlFileRecord).count()
    needs_repair = (
        db.query(FnlFileRecord)
        .filter(FnlFileRecord.status.in_(["missing", "bad_magic", "too_small", "link_broken"]))
        .count()
    )
    return {
        "total": total,
        "server_ok": db.query(FnlFileRecord).filter(FnlFileRecord.status == "server_ok").count(),
        "uploaded": db.query(FnlFileRecord).filter(FnlFileRecord.uploaded.is_(True)).count(),
        "needs_repair": needs_repair,
    }


def serialize_run(run: ForecastRun) -> dict:
    return {
        "run_id": run.run_id,
        "status": run.status.value if run.status else None,
        "progress": run.progress,
        "start_time": run.start_time,
        "end_time": run.end_time,
        "period": run.period,
        "domain": run.domain,
        "variant": run.variant,
        "server_run_dir": run.server_run_dir,
        "last_error": run.last_error,
        "created_at": run.created_at.isoformat() if run.created_at else None,
        "updated_at": run.updated_at.isoformat() if run.updated_at else None,
    }


def serialize_product(product: ForecastProduct) -> dict:
    return {
        "id": product.id,
        "product_name": product.product_name,
        "product_type": product.product_type,
        "status": product.status.value if product.status else None,
        "region": product.region,
        "pollen_type": product.pollen_type,
        "resolution": product.resolution,
        "release_time": product.release_time.isoformat() if product.release_time else None,
    }


def serialize_action(action: AgentAction) -> dict:
    return {
        "id": action.id,
        "run_id": action.run_id,
        "action_type": action.action_type,
        "reason": action.reason,
        "status": action.status,
        "created_at": action.created_at.isoformat() if action.created_at else None,
        "finished_at": action.finished_at.isoformat() if action.finished_at else None,
    }


def serialize_log(log: SystemLog) -> dict:
    return {
        "id": log.id,
        "level": log.level,
        "message": log.message,
        "source": log.source,
        "timestamp": log.timestamp.isoformat() if log.timestamp else None,
    }


@router.get("/logs", response_model=list[SystemLogResponse])
def get_system_logs(skip: int = 0, limit: int = 50, db: Session = Depends(get_db)):
    logs = db.query(SystemLog).order_by(SystemLog.timestamp.desc()).offset(skip).limit(limit).all()
    return logs
