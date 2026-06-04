from __future__ import annotations

import hashlib
import json
from typing import Any

from sqlalchemy.orm import Session

from ..models.models import ForecastRunEvent
from .flow import ServerFlowService


class RunEventService:
    def __init__(self, db: Session, flow: ServerFlowService | None = None):
        self.db = db
        self.flow = flow or ServerFlowService()

    def sync(
        self,
        run_id: str,
        tail: int = 5000,
        node: str | None = None,
        level: str | None = None,
        event_type: str | None = None,
    ) -> dict[str, Any]:
        manifest = self.flow.events(run_id, tail=tail, node=node, level=level, event_type=event_type)
        created = 0
        updated = 0
        for event in manifest.get("events", []):
            item, is_created = self.upsert_event(run_id, event)
            if is_created:
                created += 1
            else:
                updated += 1
        self.db.commit()
        return {
            "ok": bool(manifest.get("ok", manifest.get("_exit_code") == 0)),
            "run_id": run_id,
            "source_count": len(manifest.get("events", [])),
            "created_count": created,
            "updated_count": updated,
        }

    def list_events(
        self,
        run_id: str,
        limit: int = 200,
        node: str | None = None,
        level: str | None = None,
        event_type: str | None = None,
    ) -> list[dict[str, Any]]:
        query = self.db.query(ForecastRunEvent).filter(ForecastRunEvent.run_id == run_id)
        if node:
            query = query.filter(ForecastRunEvent.node_name == node)
        if level:
            query = query.filter(ForecastRunEvent.level == level)
        if event_type:
            query = query.filter(ForecastRunEvent.event_type == event_type)
        rows = query.order_by(ForecastRunEvent.created_at.desc()).limit(limit).all()
        return [self.serialize_event(row) for row in rows]

    def upsert_event(self, run_id: str, event: dict[str, Any]) -> tuple[ForecastRunEvent, bool]:
        key = event_key(run_id, event)
        row = self.db.query(ForecastRunEvent).filter(ForecastRunEvent.event_key == key).first()
        created = row is None
        if row is None:
            row = ForecastRunEvent(event_key=key, run_id=run_id)
            self.db.add(row)
        row.node_name = event.get("node")
        row.event_type = event.get("event_type") or "event"
        row.level = event.get("level") or "info"
        row.message = event.get("message") or ""
        row.payload_json = stable_json(event.get("payload") or {})
        row.created_at = event.get("created_at") or ""
        return row, created

    @staticmethod
    def serialize_event(row: ForecastRunEvent) -> dict[str, Any]:
        return {
            "id": row.id,
            "run_id": row.run_id,
            "node": row.node_name,
            "event_type": row.event_type,
            "level": row.level,
            "message": row.message,
            "payload": json.loads(row.payload_json or "{}"),
            "created_at": row.created_at,
            "synced_at": row.synced_at.isoformat() if row.synced_at else None,
        }


def event_key(run_id: str, event: dict[str, Any]) -> str:
    identity = {
        "run_id": run_id,
        "node": event.get("node"),
        "event_type": event.get("event_type"),
        "level": event.get("level"),
        "message": event.get("message"),
        "payload": event.get("payload") or {},
        "created_at": event.get("created_at"),
    }
    return hashlib.sha1(stable_json(identity).encode("utf-8")).hexdigest()


def stable_json(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
