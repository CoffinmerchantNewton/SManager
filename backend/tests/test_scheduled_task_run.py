import unittest

from backend.app.api.tasks import build_agent_tick_request
from backend.app.models.models import ScheduledTask, TaskStatus
from backend.app.schemas.schemas import ScheduledTaskRunRequest


class ScheduledTaskRunTest(unittest.TestCase):
    def test_build_agent_tick_from_template(self):
        task = ScheduledTask(
            task_id="TASK-1",
            name="daily",
            status=TaskStatus.ACTIVE,
            cron_expression="0 4 * * *",
            region="neimeng",
            template='{"start":"2026060400","end":"2026061100","period":"spring","domain":"d01","dry_run_submit":true}',
        )

        payload = build_agent_tick_request(task, ScheduledTaskRunRequest())

        self.assertEqual(payload.start, "2026060400")
        self.assertEqual(payload.end, "2026061100")
        self.assertEqual(payload.period, "spring")
        self.assertEqual(payload.domain, "d01")
        self.assertTrue(payload.dry_run_submit)

    def test_request_overrides_template(self):
        task = ScheduledTask(
            task_id="TASK-2",
            name="daily",
            status=TaskStatus.ACTIVE,
            cron_expression="0 4 * * *",
            region="neimeng",
            template='{"start":"2026060400","end":"2026061100","period":"spring","domain":"d01"}',
        )

        payload = build_agent_tick_request(
            task,
            ScheduledTaskRunRequest(start="2026070100", end="2026070800", period="summer", domain="d02"),
        )

        self.assertEqual(payload.start, "2026070100")
        self.assertEqual(payload.end, "2026070800")
        self.assertEqual(payload.period, "summer")
        self.assertEqual(payload.domain, "d02")


if __name__ == "__main__":
    unittest.main()
