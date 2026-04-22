from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List
from ..core.database import get_db
from ..models.models import Workflow, ScheduledTask, SystemLog, WorkflowStatus, TaskStatus
from ..schemas.schemas import DashboardStats, SystemLogResponse

router = APIRouter()

@router.get("/stats", response_model=DashboardStats)
def get_dashboard_stats(db: Session = Depends(get_db)):
    active_tasks = db.query(ScheduledTask).filter(ScheduledTask.status == TaskStatus.ACTIVE).count()
    total_workflows = db.query(Workflow).count()
    running_workflows = db.query(Workflow).filter(Workflow.status == WorkflowStatus.RUNNING).count()
    failed_workflows = db.query(Workflow).filter(Workflow.status == WorkflowStatus.FAILED).count()

    return DashboardStats(
        active_schedulers=active_tasks,
        slurm_jobs_queued=12,
        system_health=98.5,
        total_workflows=total_workflows,
        running_workflows=running_workflows,
        failed_workflows=failed_workflows
    )

@router.get("/logs", response_model=List[SystemLogResponse])
def get_system_logs(skip: int = 0, limit: int = 50, db: Session = Depends(get_db)):
    logs = db.query(SystemLog).order_by(SystemLog.timestamp.desc()).offset(skip).limit(limit).all()
    return logs
