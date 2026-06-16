from __future__ import annotations

import random
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..core.database import get_db
from ..models.models import ScheduledTask, TaskStatus
from ..schemas.schemas import ScheduledTaskCreate, ScheduledTaskResponse, ScheduledTaskRunRequest, ScheduledTaskStatusUpdate

router = APIRouter()


def generate_task_id() -> str:
    return f"TASK-{random.randint(1000, 9999)}"


@router.get("/", response_model=List[ScheduledTaskResponse])
def get_tasks(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return db.query(ScheduledTask).offset(skip).limit(limit).all()


@router.get("/{task_id}", response_model=ScheduledTaskResponse)
def get_task(task_id: int, db: Session = Depends(get_db)):
    return require_task(db, task_id)


@router.post("/", response_model=ScheduledTaskResponse, status_code=status.HTTP_201_CREATED)
def create_task(task: ScheduledTaskCreate, db: Session = Depends(get_db)):
    task_data = task.model_dump()
    task_data["task_id"] = generate_task_id()
    db_task = ScheduledTask(**task_data)
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    return db_task


@router.patch("/{task_id}/status")
def update_task_status(task_id: int, payload: ScheduledTaskStatusUpdate, db: Session = Depends(get_db)):
    task = require_task(db, task_id)
    task.status = payload.status
    db.commit()
    return {"message": "Task status updated successfully", "task_id": task.task_id, "status": task.status}


@router.post("/{task_id}/run", status_code=status.HTTP_202_ACCEPTED)
def run_scheduled_task(task_id: int, payload: ScheduledTaskRunRequest | None = None, db: Session = Depends(get_db)):
    task = require_task(db, task_id)
    if task.status != TaskStatus.ACTIVE:
        raise HTTPException(status_code=400, detail={"error": "task_not_active", "status": task.status})
    return {
        "ok": False,
        "task_id": task.task_id,
        "code": "server_first_migration_pending",
        "message": "Scheduled execution moved to smanager-server. Local backend keeps task metadata only.",
        "requested": payload.model_dump() if payload else {},
    }


@router.delete("/{task_id}")
def delete_task(task_id: int, db: Session = Depends(get_db)):
    task = require_task(db, task_id)
    db.delete(task)
    db.commit()
    return {"message": "Task deleted successfully"}


def require_task(db: Session, task_id: int) -> ScheduledTask:
    task = db.query(ScheduledTask).filter(ScheduledTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task
