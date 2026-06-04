from __future__ import annotations

import json
import random
from datetime import datetime, timedelta, timezone
from time import monotonic
from typing import Any, List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..core.database import get_db
from ..models.models import ScheduledTask, TaskStatus
from ..schemas.run_control import AgentTickRequest
from ..schemas.schemas import (
    ScheduledTaskCreate,
    ScheduledTaskResponse,
    ScheduledTaskRunRequest,
    ScheduledTaskStatusUpdate,
)
from ..services.agent import AgentTickService

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


@router.post("/{task_id}/run")
def run_scheduled_task(
    task_id: int,
    payload: ScheduledTaskRunRequest | None = None,
    db: Session = Depends(get_db),
):
    task = require_task(db, task_id)
    if task.status != TaskStatus.ACTIVE:
        raise HTTPException(status_code=400, detail={"error": "task_not_active", "status": task.status})

    request = payload or ScheduledTaskRunRequest()
    tick_payload = build_agent_tick_request(task, request)
    started = monotonic()
    result = AgentTickService(db).tick(tick_payload)
    duration = round(monotonic() - started, 3)

    task.last_run = datetime.now(timezone.utc)
    task.last_duration = duration
    task.last_result = "Success" if result.get("ok") else "Error"
    task.success_rate = update_success_rate(float(task.success_rate or 100.0), bool(result.get("ok")))
    if not result.get("ok"):
        task.status = TaskStatus.FAILED
    db.commit()

    return {
        "ok": bool(result.get("ok")),
        "task_id": task.task_id,
        "run_id": result.get("run_id"),
        "duration": duration,
        "tick": result,
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


def build_agent_tick_request(task: ScheduledTask, request: ScheduledTaskRunRequest) -> AgentTickRequest:
    template = task_template(task)
    template.update(request.template_overrides or {})
    values = {
        "run_id": first_value(request.run_id, template.get("run_id")),
        "start": first_value(request.start, template.get("start")),
        "end": first_value(request.end, template.get("end")),
        "period": first_value(request.period, template.get("period"), default_period()),
        "domain": first_value(request.domain, template.get("domain"), "neimeng"),
        "variant": first_value(request.variant, template.get("variant"), "official"),
        "met_provider": first_value(request.met_provider, template.get("met_provider"), "FNL"),
        "commands_file": first_value(request.commands_file, template.get("commands_file")),
        "repair_fnl": first_value(request.repair_fnl, template.get("repair_fnl"), True),
        "dry_run_submit": first_value(request.dry_run_submit, template.get("dry_run_submit"), True),
        "allow_noop": first_value(request.allow_noop, template.get("allow_noop"), False),
    }
    if not values["start"] or not values["end"]:
        start, end = default_cycle_window(template)
        values["start"] = values["start"] or start
        values["end"] = values["end"] or end
    return AgentTickRequest(**values)


def task_template(task: ScheduledTask) -> dict[str, Any]:
    if not task.template:
        return {}
    try:
        parsed = json.loads(task.template)
    except json.JSONDecodeError:
        return {"template_name": task.template}
    if not isinstance(parsed, dict):
        return {"template_name": task.template}
    return dict(parsed)


def first_value(*values: Any):
    for value in values:
        if value is not None:
            return value
    return None


def default_cycle_window(template: dict[str, Any]) -> tuple[str, str]:
    now = datetime.now(timezone.utc)
    cycle_hour = int(template.get("cycle_hour", 0))
    forecast_days = int(template.get("forecast_days", 7))
    start = now.replace(hour=cycle_hour, minute=0, second=0, microsecond=0)
    if start > now:
        start -= timedelta(days=1)
    end = start + timedelta(days=forecast_days)
    return start.strftime("%Y%m%d%H"), end.strftime("%Y%m%d%H")


def default_period() -> str:
    month = datetime.now(timezone.utc).month
    if month in {3, 4, 5}:
        return "spring"
    if month in {6, 7, 8}:
        return "summer"
    return "autumn"


def update_success_rate(previous: float, ok: bool) -> float:
    sample = 100.0 if ok else 0.0
    return round(previous * 0.9 + sample * 0.1, 2)
