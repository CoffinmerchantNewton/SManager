import json
from datetime import timedelta
from pathlib import Path

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from pollen.apps.forecast.models import ForecastDomain, ForecastProduct, PollenType
from pollen.apps.workflows.models import WorkflowRun, WorkflowTaskRun, WorkflowTemplate
from pollen.apps.workflows.slurm import SlurmClient
from pollen.apps.workflows.step_library import STEP_LIBRARY


class WorkflowDefinitionError(ValueError):
    pass


def materialize_steps(template: WorkflowTemplate):
    if not template.steps:
        raise WorkflowDefinitionError("WorkflowTemplate.steps is empty")
    materialized = []
    for step in template.ordered_steps():
        name = step["name"]
        if name not in STEP_LIBRARY:
            raise WorkflowDefinitionError(f"Unknown workflow step: {name}")
        defaults = STEP_LIBRARY[name]
        merged = {
            "name": name,
            "display_name": step.get("display_name", defaults["display_name"]),
            "command": step.get("command", defaults["command"]),
            "dependencies": step.get("dependencies", defaults["dependencies"]),
            "expected_outputs": step.get("expected_outputs", defaults["expected_outputs"]),
            "slurm": {**defaults.get("slurm", {}), **step.get("slurm", {})},
            "max_retries": step.get("max_retries", 1),
            "order": step.get("order", 0),
        }
        materialized.append(merged)
    return sorted(materialized, key=lambda item: item["order"])


class WorkflowExecutor:
    def __init__(self, slurm_client=None):
        self.slurm = slurm_client or SlurmClient()

    @transaction.atomic
    def create_run(self, template, business_time, trigger_mode="manual", context=None):
        context = context or {}
        run = WorkflowRun.objects.create(
            template=template,
            business_time=business_time,
            trigger_mode=trigger_mode,
            status="pending",
            context=context,
            summary=f"{template.name} pending for {business_time:%Y-%m-%d %H:%M}",
        )
        run_root = Path(settings.RUNS_ROOT) / f"{run.id}"
        log_root = Path(settings.LOGS_ROOT) / f"{run.id}"
        output_root = Path(settings.PRODUCTS_ROOT) / business_time.strftime("%Y%m%d%H")
        for directory in (run_root, log_root, output_root):
            directory.mkdir(parents=True, exist_ok=True)
        run.run_directory = str(run_root)
        run.log_directory = str(log_root)
        run.output_directory = str(output_root)
        run.save(update_fields=["run_directory", "log_directory", "output_directory"])
        for step in materialize_steps(template):
            work_dir = run_root / step["name"]
            work_dir.mkdir(parents=True, exist_ok=True)
            WorkflowTaskRun.objects.create(
                run=run,
                step_name=step["name"],
                display_name=step["display_name"],
                step_order=step["order"],
                dependencies=step["dependencies"],
                command_text=step["command"],
                working_directory=str(work_dir),
                expected_outputs=step["expected_outputs"],
                max_retries=step["max_retries"],
            )
        return run

    def submit_ready_steps(self, run):
        now = timezone.now()
        changed = False
        for task in run.task_runs.select_for_update().all():
            if task.status not in {"pending", "ready"}:
                continue
            deps = list(
                run.task_runs.filter(step_name__in=task.dependencies).values_list("status", flat=True)
            )
            if any(status == "failed" for status in deps):
                task.status = "skipped"
                task.finished_at = now
                task.state_detail = {"reason": "dependency_failed"}
                task.save(update_fields=["status", "finished_at", "state_detail"])
                changed = True
                continue
            if task.dependencies and not all(status == "succeeded" for status in deps):
                continue
            task.status = "submitted"
            task.submitted_at = now
            script_path = Path(task.working_directory) / "submit.sh"
            output_log = Path(run.log_directory) / f"{task.step_name}.log"
            batch_script = self.slurm.render_batch_script(
                task.step_name,
                self._build_step_command(run, task),
                output_log,
                self._slurm_arguments(run.template, task),
            )
            script_path.write_text(batch_script, encoding="utf-8")
            task.script_path = str(script_path)
            task.output_log_path = str(output_log)
            task.error_log_path = str(output_log)
            task.slurm_job_id = self.slurm.submit(script_path)
            task.save(
                update_fields=[
                    "status",
                    "submitted_at",
                    "script_path",
                    "output_log_path",
                    "error_log_path",
                    "slurm_job_id",
                ]
            )
            changed = True
            if settings.SIMULATE_SLURM:
                self._simulate_step_completion(run, task)
        if changed and run.status == "pending":
            run.status = "queued"
            run.submitted_at = now
            run.summary = f"{run.template.name} queued with {run.task_runs.count()} steps"
            run.save(update_fields=["status", "submitted_at", "summary"])
        return changed

    def refresh_run(self, run):
        run = WorkflowRun.objects.prefetch_related("task_runs").get(pk=run.pk)
        now = timezone.now()
        terminal = True
        any_running = False
        any_failed = False
        for task in run.task_runs.all():
            if task.status in {"submitted", "running"} and not settings.SIMULATE_SLURM:
                account = self.slurm.accounting(task.slurm_job_id)
                state = account["state"].upper()
                if "COMPLETED" in state and self._validate_outputs(task):
                    task.status = "succeeded"
                    task.finished_at = now
                    task.state_detail = account
                    task.save(update_fields=["status", "finished_at", "state_detail"])
                elif any(token in state for token in ("FAILED", "CANCELLED", "TIMEOUT")):
                    task.status = "failed"
                    task.finished_at = now
                    task.state_detail = account
                    task.save(update_fields=["status", "finished_at", "state_detail"])
            if task.status in {"pending", "ready", "submitted", "running"}:
                terminal = False
            if task.status in {"submitted", "running"}:
                any_running = True
            if task.status == "failed":
                any_failed = True
        self.submit_ready_steps(run)
        run = WorkflowRun.objects.prefetch_related("task_runs").get(pk=run.pk)
        statuses = list(run.task_runs.values_list("status", flat=True))
        if statuses and all(status in {"succeeded", "skipped"} for status in statuses):
            run.status = "succeeded"
            run.finished_at = timezone.now()
            run.summary = f"{run.template.name} completed successfully"
            run.failure_summary = ""
            run.save(update_fields=["status", "finished_at", "summary", "failure_summary"])
            self.ensure_products(run)
        elif any_failed:
            run.status = "failed"
            run.finished_at = timezone.now()
            run.failure_summary = "One or more workflow steps failed."
            run.summary = f"{run.template.name} failed"
            run.save(update_fields=["status", "finished_at", "failure_summary", "summary"])
        elif any_running or any(status == "submitted" for status in statuses):
            run.status = "running"
            if not run.started_at:
                run.started_at = timezone.now()
            run.summary = f"{run.template.name} running"
            run.save(update_fields=["status", "started_at", "summary"])
        return run

    def publish_run(self, run):
        if run.status != "succeeded":
            raise WorkflowDefinitionError("Only succeeded workflow runs can be published.")
        now = timezone.now()
        ForecastProduct.objects.exclude(run=run).filter(is_published=True).update(
            is_published=False,
            published_at=None,
        )
        WorkflowRun.objects.exclude(pk=run.pk).filter(is_published=True).update(
            is_published=False,
            published_at=None,
        )
        run.products.update(is_published=True, published_at=now)
        run.is_published = True
        run.published_at = now
        run.save(update_fields=["is_published", "published_at"])

    def ensure_products(self, run):
        pollen_types = list(PollenType.objects.filter(is_active=True))
        domains = list(ForecastDomain.objects.filter(is_active=True, code__in=run.template.domain_codes or ["d01", "d02"]))
        if not pollen_types or not domains:
            return
        preview_path = "img/demo-forecast.svg"
        created = 0
        for pollen in pollen_types:
            for domain in domains:
                for hour in range(0, 49, 6):
                    valid_time = run.business_time + timedelta(hours=hour)
                    _, was_created = ForecastProduct.objects.get_or_create(
                        run=run,
                        pollen_type=pollen,
                        domain=domain,
                        valid_time=valid_time,
                        defaults={
                            "run_time": run.business_time,
                            "forecast_hour": hour,
                            "geotiff_path": f"{run.output_directory}/{domain.code}/{pollen.code}/fh{hour:03d}.tif",
                            "stats_json_path": f"{run.output_directory}/{domain.code}/{pollen.code}/fh{hour:03d}.json",
                            "preview_image_path": preview_path,
                            "tile_url_template": "",
                            "metadata": {
                                "max_concentration": round(60 + hour * 0.7, 2),
                                "mean_concentration": round(18 + hour * 0.25, 2),
                                "domain_extent": domain.extent,
                            },
                            "passed_validation": True,
                        },
                    )
                    created += int(was_created)
        manifest_path = Path(run.output_directory) / "manifest.json"
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text(
            json.dumps(
                {
                    "run_id": run.id,
                    "created_products": created,
                    "created_at": timezone.now().isoformat(),
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

    def _slurm_arguments(self, template, task):
        return STEP_LIBRARY[task.step_name].get("slurm", {})

    def _build_step_command(self, run, task):
        marker_path = Path(task.working_directory) / "SUCCESS.marker"
        task.success_marker_path = str(marker_path)
        task.save(update_fields=["success_marker_path"])
        if settings.SIMULATE_SLURM:
            return (
                f"cd \"{task.working_directory}\" && "
                f"echo 'simulate {task.step_name}' > step.txt && "
                f"touch \"{marker_path}\""
            )
        return f"cd \"{task.working_directory}\" && {task.command_text} && touch \"{marker_path}\""

    def _simulate_step_completion(self, run, task):
        marker = Path(task.success_marker_path or Path(task.working_directory) / "SUCCESS.marker")
        marker.parent.mkdir(parents=True, exist_ok=True)
        marker.write_text("ok\n", encoding="utf-8")
        for expected in task.expected_outputs:
            filename = expected.replace("FILE:", "")
            Path(task.working_directory, filename).write_text("simulated\n", encoding="utf-8")
        task.status = "succeeded"
        task.started_at = timezone.now()
        task.finished_at = timezone.now()
        task.state_detail = {"simulated": True, "job_id": task.slurm_job_id}
        task.save(update_fields=["status", "started_at", "finished_at", "state_detail"])

    def _validate_outputs(self, task):
        if task.success_marker_path and Path(task.success_marker_path).exists():
            return True
        return all(Path(task.working_directory, output.replace("FILE:", "")).exists() for output in task.expected_outputs)
