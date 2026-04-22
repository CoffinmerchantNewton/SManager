from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from ..core.database import get_db
from ..models.models import ScheduledTask
from ..schemas.schemas import ScheduledTaskCreate, ScheduledTaskResponse
import random
import string

router = APIRouter()

def generate_task_id():
    return f"TASK-{random.randint(1000, 9999)}"

@router.get("/", response_model=List[ScheduledTaskResponse])
def get_tasks(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    tasks = db.query(ScheduledTask).offset(skip).limit(limit).all()
    return tasks

@router.get("/{task_id}", response_model=ScheduledTaskResponse)
def get_task(task_id: int, db: Session = Depends(get_db)):
    task = db.query(ScheduledTask).filter(ScheduledTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task

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
def update_task_status(task_id: int, status: str, db: Session = Depends(get_db)):
    task = db.query(ScheduledTask).filter(ScheduledTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    task.status = status
    db.commit()
    return {"message": "Task status updated successfully"}

@router.delete("/{task_id}")
def delete_task(task_id: int, db: Session = Depends(get_db)):
    task = db.query(ScheduledTask).filter(ScheduledTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    db.delete(task)
    db.commit()
    return {"message": "Task deleted successfully"}
