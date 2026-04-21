from celery import shared_task
from django.utils import timezone

from pollen.apps.workflows.execution import WorkflowExecutor
from pollen.apps.workflows.models import WorkflowRun, WorkflowSchedule, WorkflowTemplate


@shared_task
def trigger_scheduled_workflow(schedule_id):
    schedule = WorkflowSchedule.objects.select_related("template").get(pk=schedule_id)
    executor = WorkflowExecutor()
    run = executor.create_run(
        schedule.template,
        business_time=timezone.now().replace(minute=0, second=0, microsecond=0),
        trigger_mode="schedule",
        context=schedule.schedule_parameters,
    )
    launch_workflow_run.delay(run.id)
    schedule.last_enqueued_at = timezone.now()
    schedule.save(update_fields=["last_enqueued_at"])
    return run.id


@shared_task
def launch_workflow_run(run_id):
    executor = WorkflowExecutor()
    run = WorkflowRun.objects.get(pk=run_id)
    executor.submit_ready_steps(run)
    refreshed = executor.refresh_run(run)
    return refreshed.status


@shared_task
def resume_workflow_run(run_id):
    executor = WorkflowExecutor()
    run = WorkflowRun.objects.get(pk=run_id)
    run.status = "pending"
    run.failure_summary = ""
    run.save(update_fields=["status", "failure_summary"])
    for task in run.task_runs.filter(status="failed"):
        task.status = "pending"
        task.save(update_fields=["status"])
    executor.submit_ready_steps(run)
    refreshed = executor.refresh_run(run)
    return refreshed.status


def sync_schedule_to_beat(schedule: WorkflowSchedule):
    from django_celery_beat.models import CrontabSchedule, PeriodicTask

    crontab, _ = CrontabSchedule.objects.get_or_create(
        minute=schedule.minute,
        hour=schedule.hour,
        day_of_week=schedule.day_of_week,
        day_of_month=schedule.day_of_month,
        month_of_year=schedule.month_of_year,
        timezone=schedule.timezone,
    )
    task_name = schedule.beat_task_name or f"workflow-schedule-{schedule.pk}"
    PeriodicTask.objects.update_or_create(
        name=task_name,
        defaults={
            "task": "pollen.apps.workflows.tasks.trigger_scheduled_workflow",
            "crontab": crontab,
            "enabled": schedule.enabled,
            "args": f"[{schedule.pk}]",
        },
    )
    if schedule.beat_task_name != task_name:
        schedule.beat_task_name = task_name
        schedule.save(update_fields=["beat_task_name"])
