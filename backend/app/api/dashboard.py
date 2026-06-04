from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import List
from ..core.database import get_db
from ..models.models import (
    AgentAction,
    FnlFileRecord,
    ForecastRun,
    ForecastRunNode,
    ForecastRunStatus,
    ForecastProduct,
    ProductStatus,
    ScheduledTask,
    SystemLog,
    TaskStatus,
)
from ..schemas.schemas import DashboardStats, SystemLogResponse

router = APIRouter()

@router.get("/stats", response_model=DashboardStats)
def get_dashboard_stats(db: Session = Depends(get_db)):
    return build_dashboard_stats(db)


@router.get("/overview")
def get_dashboard_overview(
    recent_limit: int = Query(default=8, ge=1, le=50),
    db: Session = Depends(get_db),
):
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
    }


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
        failed_workflows=failed_runs
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

@router.get("/logs", response_model=List[SystemLogResponse])
def get_system_logs(skip: int = 0, limit: int = 50, db: Session = Depends(get_db)):
    logs = db.query(SystemLog).order_by(SystemLog.timestamp.desc()).offset(skip).limit(limit).all()
    return logs
