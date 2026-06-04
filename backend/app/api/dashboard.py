from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List
from ..core.database import get_db
from ..models.models import (
    ForecastRun,
    ForecastRunNode,
    ForecastRunStatus,
    ScheduledTask,
    SystemLog,
    TaskStatus,
)
from ..schemas.schemas import DashboardStats, SystemLogResponse

router = APIRouter()

@router.get("/stats", response_model=DashboardStats)
def get_dashboard_stats(db: Session = Depends(get_db)):
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

@router.get("/logs", response_model=List[SystemLogResponse])
def get_system_logs(skip: int = 0, limit: int = 50, db: Session = Depends(get_db)):
    logs = db.query(SystemLog).order_by(SystemLog.timestamp.desc()).offset(skip).limit(limit).all()
    return logs
