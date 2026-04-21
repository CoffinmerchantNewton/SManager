from functools import wraps

from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from pollen.apps.forecast.models import ForecastProduct
from pollen.apps.workflows.execution import WorkflowExecutor
from pollen.apps.workflows.forms import ConsoleLoginForm, ManualRunForm, WorkflowScheduleForm, WorkflowTemplateForm
from pollen.apps.workflows.models import WorkflowRun, WorkflowSchedule, WorkflowTemplate
from pollen.apps.workflows.tasks import launch_workflow_run, resume_workflow_run, sync_schedule_to_beat


def console_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.session.get("console_authed"):
            return redirect("console-login")
        return view_func(request, *args, **kwargs)

    return wrapper


def console_login(request):
    form = ConsoleLoginForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        request.session["console_authed"] = True
        messages.success(request, "已进入预报管理模块。")
        return redirect("console-dashboard")
    return render(request, "workflows/console_login.html", {"form": form})


def console_logout(request):
    request.session.pop("console_authed", None)
    messages.info(request, "已退出控制台。")
    return redirect("home")


@console_required
def console_dashboard(request):
    run_form = ManualRunForm(request.POST or None)
    if request.method == "POST" and "trigger_run" in request.POST and run_form.is_valid():
        executor = WorkflowExecutor()
        run = executor.create_run(
            template=run_form.cleaned_data["template"],
            business_time=run_form.cleaned_data["business_time"],
            trigger_mode="manual",
            context={"source": "console"},
        )
        launch_workflow_run.delay(run.id)
        messages.success(request, f"已提交流程运行 #{run.id}")
        return redirect("console-runs")
    context = {
        "run_form": run_form,
        "stats": {
            "templates": WorkflowTemplate.objects.count(),
            "schedules": WorkflowSchedule.objects.count(),
            "runs": WorkflowRun.objects.count(),
            "published_products": ForecastProduct.objects.filter(is_published=True).count(),
        },
        "recent_runs": WorkflowRun.objects.select_related("template").order_by("-created_at")[:8],
    }
    return render(request, "workflows/dashboard.html", context)


@console_required
def template_manager(request):
    editing = None
    if request.GET.get("edit"):
        editing = get_object_or_404(WorkflowTemplate, pk=request.GET["edit"])
    form = WorkflowTemplateForm(request.POST or None, instance=editing)
    if request.method == "POST" and form.is_valid():
        template = form.save()
        messages.success(request, f"模板 {template.name} 已保存。")
        return redirect("console-templates")
    return render(
        request,
        "workflows/templates.html",
        {
            "form": form,
            "editing": editing,
            "templates": WorkflowTemplate.objects.order_by("name"),
        },
    )


@console_required
def template_delete(request, pk):
    get_object_or_404(WorkflowTemplate, pk=pk).delete()
    messages.info(request, "流程模板已删除。")
    return redirect("console-templates")


@console_required
def schedule_manager(request):
    editing = None
    if request.GET.get("edit"):
        editing = get_object_or_404(WorkflowSchedule, pk=request.GET["edit"])
    form = WorkflowScheduleForm(request.POST or None, instance=editing)
    if request.method == "POST" and form.is_valid():
        schedule = form.save()
        sync_schedule_to_beat(schedule)
        messages.success(request, f"定时任务 {schedule.name} 已同步。")
        return redirect("console-schedules")
    return render(
        request,
        "workflows/schedules.html",
        {
            "form": form,
            "editing": editing,
            "schedules": WorkflowSchedule.objects.select_related("template").order_by("name"),
        },
    )


@console_required
def schedule_delete(request, pk):
    schedule = get_object_or_404(WorkflowSchedule, pk=pk)
    if schedule.beat_task_name:
        from django_celery_beat.models import PeriodicTask

        PeriodicTask.objects.filter(name=schedule.beat_task_name).delete()
    schedule.delete()
    messages.info(request, "定时任务已删除。")
    return redirect("console-schedules")


@console_required
def run_manager(request):
    runs = WorkflowRun.objects.select_related("template").prefetch_related("task_runs").order_by("-created_at")[:20]
    return render(request, "workflows/runs.html", {"runs": runs})


@console_required
def run_resume(request, pk):
    run = get_object_or_404(WorkflowRun, pk=pk)
    resume_workflow_run.delay(run.id)
    messages.success(request, f"已尝试续跑 #{run.id}")
    return redirect("console-runs")


@console_required
def run_refresh(request, pk):
    run = get_object_or_404(WorkflowRun, pk=pk)
    WorkflowExecutor().refresh_run(run)
    messages.info(request, f"已刷新运行 #{run.id}")
    return redirect("console-runs")


@console_required
def publication_manager(request):
    runs = WorkflowRun.objects.select_related("template").prefetch_related("products").order_by("-business_time")[:20]
    return render(request, "workflows/publications.html", {"runs": runs, "now": timezone.now()})


@console_required
def publish_run(request, pk):
    run = get_object_or_404(WorkflowRun, pk=pk)
    try:
        WorkflowExecutor().publish_run(run)
    except Exception as exc:
        messages.error(request, f"发布失败：{exc}")
    else:
        messages.success(request, f"运行 #{run.id} 已发布到首页。")
    return redirect("console-publications")
