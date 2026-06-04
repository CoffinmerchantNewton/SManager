from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from ...models.models import ForecastRun, ForecastRunStatus
from ...schemas.run_control import AgentTickRequest
from ..audit import create_action, finish_action
from ..flow import ServerFlowService
from ..fnl import FnlRepairService


class AgentTickService:
    def __init__(self, db: Session):
        self.db = db
        self.flow = ServerFlowService()

    def tick(self, payload: AgentTickRequest) -> dict[str, Any]:
        action = create_action(
            self.db,
            action_type="agent_tick",
            status="running",
            run_id=payload.run_id,
            reason="single Hermes-agent tick",
            input_data=payload.model_dump(),
        )
        try:
            plan = self.flow.plan(
                run_id=payload.run_id,
                start=payload.start,
                end=payload.end,
                period=payload.period,
                domain=payload.domain,
                variant=payload.variant,
                met_provider=payload.met_provider,
                commands_file=payload.commands_file,
            )
            run_id = plan.get("run_id") or payload.run_id
            self.upsert_run(payload, run_id, plan)

            if payload.repair_fnl:
                fnl = FnlRepairService(self.db).repair(run_id=run_id)
            else:
                fnl = FnlRepairService(self.db).verify_server(run_id=run_id)

            if fnl.get("ok"):
                submit = self.flow.submit(
                    run_id,
                    dry_run=payload.dry_run_submit,
                    allow_noop=payload.allow_noop,
                )
            else:
                submit = {"ok": False, "skipped": True, "reason": "fnl_not_ready"}

            status = self.flow.status(run_id)
            output = {"ok": bool(fnl.get("ok")), "run_id": run_id, "plan": plan, "fnl": fnl, "submit": submit, "status": status}
            finish_action(self.db, action, "success" if output["ok"] else "error", output)
            return output
        except Exception as exc:
            output = {"ok": False, "error": exc.__class__.__name__, "message": str(exc)}
            finish_action(self.db, action, "error", output)
            return output

    def upsert_run(self, payload: AgentTickRequest, run_id: str, plan: dict[str, Any]) -> None:
        run = self.db.query(ForecastRun).filter(ForecastRun.run_id == run_id).first()
        if not run:
            run = ForecastRun(run_id=run_id)
            self.db.add(run)
        run.start_time = payload.start
        run.end_time = payload.end
        run.period = payload.period
        run.domain = payload.domain
        run.variant = payload.variant
        run.met_provider = payload.met_provider
        run.status = ForecastRunStatus.PENDING
        run.server_run_dir = plan.get("run_dir")
        self.db.commit()
