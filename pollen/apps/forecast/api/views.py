from datetime import timedelta

from django.utils import timezone
from rest_framework.response import Response
from rest_framework.views import APIView

from pollen.apps.core.models import SiteConfiguration
from pollen.apps.forecast.models import ForecastDomain, ForecastProduct, PointQueryProfile, PollenType
from pollen.apps.forecast.serializers import (
    ForecastDomainSerializer,
    ForecastProductSerializer,
    PointQueryProfileSerializer,
    PollenTypeSerializer,
)
from pollen.apps.workflows.models import WorkflowRun


class HomeSummaryAPIView(APIView):
    def get(self, request):
        latest_run = (
            WorkflowRun.objects.filter(is_published=True)
            .select_related("template")
            .order_by("-published_at", "-business_time")
            .first()
        )
        return Response(
            {
                "site": {
                    "title": SiteConfiguration.load().title,
                    "subtitle": SiteConfiguration.load().subtitle,
                },
                "latest_run": {
                    "id": latest_run.id if latest_run else None,
                    "status": latest_run.status if latest_run else None,
                    "business_time": latest_run.business_time if latest_run else None,
                    "summary": latest_run.summary if latest_run else "",
                },
                "pollen_types": PollenTypeSerializer(
                    PollenType.objects.filter(is_active=True).order_by("sort_order", "name"), many=True
                ).data,
                "domains": ForecastDomainSerializer(
                    ForecastDomain.objects.filter(is_active=True).order_by("sort_order", "code"), many=True
                ).data,
                "featured_profiles": PointQueryProfileSerializer(
                    PointQueryProfile.objects.filter(is_featured=True).select_related("domain", "pollen_type")[:4],
                    many=True,
                ).data,
            }
        )


class ProductCollectionAPIView(APIView):
    def get(self, request):
        domain_code = request.GET.get("domain")
        pollen_code = request.GET.get("pollen")
        run_id = request.GET.get("run_id")
        queryset = ForecastProduct.objects.filter(is_published=True, passed_validation=True).select_related(
            "domain", "pollen_type", "run"
        )
        if domain_code:
            queryset = queryset.filter(domain__code=domain_code)
        if pollen_code:
            queryset = queryset.filter(pollen_type__code=pollen_code)
        if run_id:
            queryset = queryset.filter(run_id=run_id)
        return Response(ForecastProductSerializer(queryset.order_by("valid_time")[:72], many=True).data)


class PointProfileSeriesAPIView(APIView):
    def get(self, request, pk):
        profile = PointQueryProfile.objects.select_related("domain", "pollen_type").get(pk=pk)
        if profile.sample_series:
            series = profile.sample_series
        else:
            now = timezone.now().replace(minute=0, second=0, microsecond=0)
            series = []
            for idx in range(24):
                series.append(
                    {
                        "time": (now + timedelta(hours=idx)).isoformat(),
                        "value": round(12 + idx * 1.8 + ((idx % 4) * 2.1), 2),
                    }
                )
        return Response(
            {
                "profile": PointQueryProfileSerializer(profile).data,
                "series": series,
            }
        )
