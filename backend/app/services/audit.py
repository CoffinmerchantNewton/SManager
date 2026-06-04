from __future__ import annotations

import json
from typing import Any

from sqlalchemy.orm import Session

from ..models.models import AgentAction


def create_action(
    db: Session,
    action_type: str,
    status: str,
    run_id: str | None = None,
    reason: str | None = None,
    input_data: dict[str, Any] | None = None,
    output_data: dict[str, Any] | None = None,
) -> AgentAction:
    action = AgentAction(
        run_id=run_id,
        action_type=action_type,
        reason=reason,
        status=status,
        input_json=to_json(input_data),
        output_json=to_json(output_data),
    )
    db.add(action)
    db.commit()
    db.refresh(action)
    return action


def finish_action(
    db: Session,
    action: AgentAction,
    status: str,
    output_data: dict[str, Any] | None = None,
) -> AgentAction:
    from datetime import datetime, timezone

    action.status = status
    action.output_json = to_json(output_data)
    action.finished_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(action)
    return action


def to_json(data: dict[str, Any] | None) -> str | None:
    if data is None:
        return None
    return json.dumps(data, ensure_ascii=False, sort_keys=True)
