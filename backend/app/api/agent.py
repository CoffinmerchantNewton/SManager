from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..core.database import get_db
from ..schemas.run_control import AgentTickRequest, FlowResponse
from ..services.agent import AgentTickService

router = APIRouter()


@router.post("/tick", response_model=FlowResponse)
def agent_tick(payload: AgentTickRequest, db: Session = Depends(get_db)):
    result = AgentTickService(db).tick(payload)
    return FlowResponse(ok=bool(result.get("ok")), data=result)
