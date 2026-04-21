from django.shortcuts import render

from pollen.apps.core.models import SiteConfiguration
from pollen.apps.forecast.models import ForecastDomain, PollenType, PointQueryProfile
from pollen.apps.workflows.models import WorkflowRun


def home(request):
    latest_run = (
        WorkflowRun.objects.filter(is_published=True)
        .select_related("template")
        .order_by("-published_at", "-business_time")
        .first()
    )
    context = {
        "config": SiteConfiguration.load(),
        "domains": ForecastDomain.objects.filter(is_active=True).order_by("sort_order", "code"),
        "pollen_types": PollenType.objects.filter(is_active=True).order_by("sort_order", "name"),
        "featured_profiles": PointQueryProfile.objects.filter(is_featured=True).select_related(
            "domain", "pollen_type"
        )[:4],
        "latest_run": latest_run,
    }
    return render(request, "core/home.html", context)
