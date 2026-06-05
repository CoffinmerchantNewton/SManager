from __future__ import annotations

import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from backend.app.api.runs import collect_db_context
from backend.app.core.migrations import run_migrations
from backend.app.models.models import ForecastRun, ForecastRunNode, ForecastRunStatus


class RunContextFallbackTest(unittest.TestCase):
    def test_database_context_returns_nodes_without_server_flow(self):
        engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
        run_migrations(engine)

        with Session(engine) as db:
            db.add(
                ForecastRun(
                    run_id="run-a",
                    start_time="2026060100",
                    end_time="2026060112",
                    period="spring",
                    status=ForecastRunStatus.RUNNING,
                    progress=50,
                )
            )
            db.add(ForecastRunNode(run_id="run-a", node_name="fnl_verify", status="success", progress=100, attempt=1))
            db.add(ForecastRunNode(run_id="run-a", node_name="wrf_run", status="running", progress=20, attempt=2))
            db.commit()

            context = collect_db_context(db, "run-a")

        self.assertEqual(context["source"], "database_snapshot")
        self.assertEqual(context["status"]["status"], "running")
        self.assertEqual(len(context["status"]["nodes"]), 2)
        self.assertEqual(context["status"]["nodes"][1]["node"], "wrf_run")


if __name__ == "__main__":
    unittest.main()
