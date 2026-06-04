from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..core.database import get_db
from ..models.models import AgentAction
from ..schemas.run_control import AgentTickRequest, FlowResponse
from ..services.agent import AgentTickService

router = APIRouter()


@router.post("/tick", response_model=FlowResponse)
def agent_tick(payload: AgentTickRequest, db: Session = Depends(get_db)):
    result = AgentTickService(db).tick(payload)
    return FlowResponse(ok=bool(result.get("ok")), data=result)


@router.get("/actions", response_model=FlowResponse)
def list_agent_actions(
    run_id: str | None = None,
    action_type: str | None = None,
    status: str | None = None,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    query = db.query(AgentAction)
    if run_id:
        query = query.filter(AgentAction.run_id == run_id)
    if action_type:
        query = query.filter(AgentAction.action_type == action_type)
    if status:
        query = query.filter(AgentAction.status == status)
    actions = query.order_by(AgentAction.created_at.desc()).limit(limit).all()
    return FlowResponse(
        data={
            "actions": [
                {
                    "id": item.id,
                    "run_id": item.run_id,
                    "action_type": item.action_type,
                    "reason": item.reason,
                    "status": item.status,
                    "input_json": item.input_json,
                    "output_json": item.output_json,
                    "created_at": item.created_at.isoformat() if item.created_at else None,
                    "finished_at": item.finished_at.isoformat() if item.finished_at else None,
                }
                for item in actions
            ]
        }
    )
