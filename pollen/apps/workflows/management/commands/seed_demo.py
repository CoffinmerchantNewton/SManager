from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from pollen.apps.core.models import FriendlyLink, SiteConfiguration
from pollen.apps.forecast.models import ForecastDomain, PointQueryProfile, PollenType
from pollen.apps.workflows.execution import WorkflowExecutor
from pollen.apps.workflows.models import WorkflowTemplate


class Command(BaseCommand):
    help = "Seed demo data for the pollen forecast portal."

    def handle(self, *args, **options):
        SiteConfiguration.objects.get_or_create(
            id=1,
            defaults={
                "hero_notice": "业务试运行环境",
            },
        )

        FriendlyLink.objects.get_or_create(name="中国气象局", url="https://www.cma.gov.cn", sort_order=1)
        FriendlyLink.objects.get_or_create(name="NASA Earth", url="https://earthdata.nasa.gov", sort_order=2)
        FriendlyLink.objects.get_or_create(name="ECMWF", url="https://www.ecmwf.int", sort_order=3)

        d01, _ = ForecastDomain.objects.get_or_create(
            code="d01",
            defaults={
                "name": "China National Domain",
                "extent": [73.0, 18.0, 135.0, 54.0],
                "resolution_km": 27.0,
                "center_lon": 104.0,
                "center_lat": 35.5,
                "sort_order": 1,
            },
        )
        d02, _ = ForecastDomain.objects.get_or_create(
            code="d02",
            defaults={
                "name": "Refined Regional Domain",
                "extent": [97.0, 22.0, 123.0, 42.0],
                "resolution_km": 9.0,
                "center_lon": 110.0,
                "center_lat": 31.0,
                "sort_order": 2,
            },
        )

        li, _ = PollenType.objects.get_or_create(code="li-ke", defaults={"name": "黎科花粉", "sort_order": 1, "color_hex": "#8be9fd"})
        pinus, _ = PollenType.objects.get_or_create(code="pine", defaults={"name": "松科花粉", "sort_order": 2, "color_hex": "#ffd166"})
        artemisia, _ = PollenType.objects.get_or_create(code="wormwood", defaults={"name": "蒿属花粉", "sort_order": 3, "color_hex": "#ef476f"})

        PointQueryProfile.objects.get_or_create(
            name="北京城区站",
            defaults={
                "description": "北京市海淀区固定分析点",
                "longitude": 116.38,
                "latitude": 39.90,
                "domain": d01,
                "pollen_type": li,
                "sample_series": [
                    {"time": (timezone.now() + timedelta(hours=idx)).isoformat(), "value": 18 + idx * 1.6}
                    for idx in range(12)
                ],
                "sort_order": 1,
            },
        )
        PointQueryProfile.objects.get_or_create(
            name="长三角样点",
            defaults={
                "description": "上海附近重点区域样点",
                "longitude": 121.48,
                "latitude": 31.23,
                "domain": d02,
                "pollen_type": pinus,
                "sort_order": 2,
            },
        )

        template, _ = WorkflowTemplate.objects.get_or_create(
            slug="china-operational",
            defaults={
                "name": "中国全域业务预报",
                "description": "d01/d02 双域、全流程自动化花粉业务预报模板。",
                "region_label": "China",
                "domain_codes": ["d01", "d02"],
                "default_parameters": {"forecast_hours": 48, "cycle": "00Z"},
                "steps": [
                    {"name": "geogrid", "order": 1},
                    {"name": "ungrib", "order": 2},
                    {"name": "metgrid", "order": 3},
                    {"name": "wps", "order": 4},
                    {"name": "pollen_interp", "order": 5},
                    {"name": "wrf", "order": 6},
                    {"name": "postprocess", "order": 7},
                ],
            },
        )

        executor = WorkflowExecutor()
        run = executor.create_run(template, timezone.now().replace(minute=0, second=0, microsecond=0))
        executor.submit_ready_steps(run)
        run = executor.refresh_run(run)
        executor.publish_run(run)

        self.stdout.write(self.style.SUCCESS(f"Seeded demo data with run #{run.id}"))
