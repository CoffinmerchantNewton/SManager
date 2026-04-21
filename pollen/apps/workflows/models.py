from django.db import models


class WorkflowTemplate(models.Model):
    name = models.CharField(max_length=120)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    region_label = models.CharField(max_length=120, default="China")
    domain_codes = models.JSONField(default=list, blank=True)
    default_parameters = models.JSONField(default=dict, blank=True)
    steps = models.JSONField(default=list, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("name",)
        verbose_name = "流程模板"
        verbose_name_plural = "流程模板"

    def __str__(self):
        return self.name

    def ordered_steps(self):
        return sorted(self.steps, key=lambda step: step.get("order", 0))


class WorkflowSchedule(models.Model):
    template = models.ForeignKey(WorkflowTemplate, on_delete=models.CASCADE, related_name="schedules")
    name = models.CharField(max_length=120)
    timezone = models.CharField(max_length=64, default="Asia/Shanghai")
    minute = models.CharField(max_length=20, default="0")
    hour = models.CharField(max_length=20, default="2")
    day_of_week = models.CharField(max_length=20, default="*")
    day_of_month = models.CharField(max_length=20, default="*")
    month_of_year = models.CharField(max_length=20, default="*")
    schedule_parameters = models.JSONField(default=dict, blank=True)
    enabled = models.BooleanField(default=True)
    beat_task_name = models.CharField(max_length=150, blank=True)
    last_enqueued_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("name",)
        verbose_name = "定时任务"
        verbose_name_plural = "定时任务"

    def __str__(self):
        return self.name


class WorkflowRun(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("queued", "Queued"),
        ("running", "Running"),
        ("succeeded", "Succeeded"),
        ("failed", "Failed"),
        ("partial", "Partial"),
        ("cancelled", "Cancelled"),
    ]
    TRIGGER_CHOICES = [
        ("manual", "Manual"),
        ("schedule", "Schedule"),
        ("resume", "Resume"),
    ]

    template = models.ForeignKey(WorkflowTemplate, on_delete=models.CASCADE, related_name="runs")
    trigger_mode = models.CharField(max_length=20, choices=TRIGGER_CHOICES, default="manual")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    business_time = models.DateTimeField()
    context = models.JSONField(default=dict, blank=True)
    summary = models.CharField(max_length=255, blank=True)
    run_directory = models.CharField(max_length=255, blank=True)
    log_directory = models.CharField(max_length=255, blank=True)
    output_directory = models.CharField(max_length=255, blank=True)
    is_published = models.BooleanField(default=False)
    published_at = models.DateTimeField(null=True, blank=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    failure_summary = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-business_time", "-created_at")
        verbose_name = "流程运行"
        verbose_name_plural = "流程运行"

    def __str__(self):
        return f"{self.template.name} @ {self.business_time:%Y-%m-%d %H:%M}"


class WorkflowTaskRun(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("ready", "Ready"),
        ("submitted", "Submitted"),
        ("running", "Running"),
        ("succeeded", "Succeeded"),
        ("failed", "Failed"),
        ("skipped", "Skipped"),
    ]

    run = models.ForeignKey(WorkflowRun, on_delete=models.CASCADE, related_name="task_runs")
    step_name = models.CharField(max_length=64)
    display_name = models.CharField(max_length=120)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    step_order = models.PositiveIntegerField(default=0)
    dependencies = models.JSONField(default=list, blank=True)
    slurm_job_id = models.CharField(max_length=40, blank=True)
    command_text = models.TextField(blank=True)
    working_directory = models.CharField(max_length=255, blank=True)
    script_path = models.CharField(max_length=255, blank=True)
    output_log_path = models.CharField(max_length=255, blank=True)
    error_log_path = models.CharField(max_length=255, blank=True)
    expected_outputs = models.JSONField(default=list, blank=True)
    success_marker_path = models.CharField(max_length=255, blank=True)
    retries = models.PositiveIntegerField(default=0)
    max_retries = models.PositiveIntegerField(default=1)
    state_detail = models.JSONField(default=dict, blank=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("step_order", "id")
        unique_together = ("run", "step_name")
        verbose_name = "任务步骤"
        verbose_name_plural = "任务步骤"

    def __str__(self):
        return f"{self.run_id}:{self.step_name}"
