from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from pollen.apps.core.models import SiteConfiguration
from pollen.apps.forecast.models import ForecastDomain, ForecastProduct, PollenType
from pollen.apps.workflows.models import WorkflowRun, WorkflowTemplate


class HomePageTests(TestCase):
    def setUp(self):
        SiteConfiguration.objects.create(title="测试花粉预报系统")
        domain = ForecastDomain.objects.create(
            code="d01",
            name="National",
            extent=[73.0, 18.0, 135.0, 54.0],
        )
        pollen = PollenType.objects.create(code="li-ke", name="黎科花粉")
        template = WorkflowTemplate.objects.create(
            name="模板",
            slug="template",
            domain_codes=["d01"],
            steps=[{"name": "geogrid", "order": 1}],
        )
        run = WorkflowRun.objects.create(
            template=template,
            business_time=timezone.now(),
            status="succeeded",
            is_published=True,
            published_at=timezone.now(),
        )
        ForecastProduct.objects.create(
            run=run,
            pollen_type=pollen,
            domain=domain,
            run_time=timezone.now(),
            valid_time=timezone.now(),
            forecast_hour=0,
            preview_image_path="img/demo-forecast.svg",
            passed_validation=True,
            is_published=True,
        )

    def test_home_page_renders(self):
        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "测试花粉预报系统")
        self.assertContains(response, "控制台")
