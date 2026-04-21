from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from pollen.apps.workflows.execution import WorkflowExecutor
from pollen.apps.workflows.models import WorkflowTemplate


@override_settings(SIMULATE_SLURM=True, CELERY_TASK_ALWAYS_EAGER=True)
class WorkflowExecutionTests(TestCase):
    def setUp(self):
        self.template = WorkflowTemplate.objects.create(
            name="China Workflow",
            slug="china-workflow",
            domain_codes=["d01", "d02"],
            steps=[
                {"name": "geogrid", "order": 1},
                {"name": "ungrib", "order": 2},
                {"name": "metgrid", "order": 3},
                {"name": "wps", "order": 4},
                {"name": "pollen_interp", "order": 5},
                {"name": "wrf", "order": 6},
                {"name": "postprocess", "order": 7},
            ],
        )

    def test_executor_completes_simulated_run(self):
        executor = WorkflowExecutor()
        run = executor.create_run(self.template, timezone.now())
        executor.submit_ready_steps(run)
        run = executor.refresh_run(run)
        self.assertEqual(run.status, "succeeded")
        self.assertEqual(run.task_runs.filter(status="succeeded").count(), 7)

    def test_console_password_gate(self):
        response = self.client.get(reverse("console-dashboard"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("console-login"), response["Location"])
