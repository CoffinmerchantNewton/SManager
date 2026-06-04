from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any

from sqlalchemy.orm import Session

from ..core.config import settings
from .audit import create_action, finish_action


class NotificationService:
    def __init__(self, db: Session | None = None):
        self.db = db

    def notify_run_issue(self, run_id: str, tick_output: dict[str, Any]) -> dict[str, Any]:
        diagnosis = tick_output.get("diagnosis") or {}
        analysis = diagnosis.get("analysis") or {}
        summary = analysis.get("summary") or {}
        should_notify = (not tick_output.get("ok")) or bool(summary.get("requires_operator"))
        if not should_notify:
            return {"ok": True, "skipped": True, "reason": "no_issue"}

        payload = {
            "event": "smanager_run_issue",
            "run_id": run_id,
            "ok": bool(tick_output.get("ok")),
            "status": (tick_output.get("status") or {}).get("status"),
            "recommended_next_action": summary.get("recommended_next_action"),
            "risk_level": summary.get("risk_level"),
            "requires_operator": summary.get("requires_operator"),
            "finding_count": summary.get("finding_count"),
        }
        return self.send("run_issue", run_id, payload)

    def send(self, reason: str, run_id: str | None, payload: dict[str, Any]) -> dict[str, Any]:
        action = None
        if self.db is not None:
            action = create_action(
                self.db,
                action_type="notification",
                status="running",
                run_id=run_id,
                reason=reason,
                input_data=payload,
            )

        webhook_url = settings.NOTIFICATION_WEBHOOK_URL
        if not webhook_url:
            result = {"ok": True, "skipped": True, "reason": "webhook_not_configured"}
            if action is not None:
                finish_action(self.db, action, "skipped", result)
            return result

        try:
            response = post_json(webhook_url, payload, timeout=settings.NOTIFICATION_WEBHOOK_TIMEOUT)
        except Exception as exc:
            result = {"ok": False, "error": exc.__class__.__name__, "message": str(exc)}
            if action is not None:
                finish_action(self.db, action, "error", result)
            return result

        result = {"ok": True, "status_code": response["status_code"], "body": response["body"][:500]}
        if action is not None:
            finish_action(self.db, action, "success", result)
        return result


def post_json(url: str, payload: dict[str, Any], timeout: int) -> dict[str, Any]:
    body = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return {"status_code": response.status, "body": response.read().decode("utf-8", errors="ignore")}
    except urllib.error.HTTPError as exc:
        text = exc.read().decode("utf-8", errors="ignore")
        raise RuntimeError(f"notification webhook failed: HTTP {exc.code} {text}") from exc
