from django.contrib import admin

from pollen.apps.workflows.models import WorkflowRun, WorkflowSchedule, WorkflowTaskRun, WorkflowTemplate


@admin.register(WorkflowTemplate)
class WorkflowTemplateAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "region_label", "is_active", "updated_at")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(WorkflowSchedule)
class WorkflowScheduleAdmin(admin.ModelAdmin):
    list_display = ("name", "template", "hour", "minute", "timezone", "enabled")
    list_filter = ("enabled", "timezone")


class WorkflowTaskRunInline(admin.TabularInline):
    model = WorkflowTaskRun
    extra = 0
    readonly_fields = ("step_name", "status", "slurm_job_id", "submitted_at", "finished_at")


@admin.register(WorkflowRun)
class WorkflowRunAdmin(admin.ModelAdmin):
    list_display = ("id", "template", "trigger_mode", "status", "business_time", "is_published")
    list_filter = ("status", "trigger_mode", "is_published")
    inlines = [WorkflowTaskRunInline]
