from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from pollen.apps.forecast.models import ForecastDomain, PointQueryProfile, PollenType
from pollen.apps.workflows.models import WorkflowRun, WorkflowTemplate


class ForecastApiTests(TestCase):
    def setUp(self):
        self.domain = ForecastDomain.objects.create(
            code="d01",
            name="National",
            extent=[73.0, 18.0, 135.0, 54.0],
        )
        self.pollen = PollenType.objects.create(code="li-ke", name="黎科花粉")
        self.profile = PointQueryProfile.objects.create(
            name="北京",
            longitude=116.4,
            latitude=39.9,
            domain=self.domain,
            pollen_type=self.pollen,
            sample_series=[{"time": timezone.now().isoformat(), "value": 23.5}],
        )
        template = WorkflowTemplate.objects.create(
            name="模板",
            slug="api-template",
            domain_codes=["d01"],
            steps=[{"name": "geogrid", "order": 1}],
        )
        WorkflowRun.objects.create(
            template=template,
            business_time=timezone.now(),
            status="succeeded",
            is_published=True,
            published_at=timezone.now(),
        )

    def test_summary_api_returns_payload(self):
        response = self.client.get(reverse("api-home-summary"))
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn("pollen_types", payload)
        self.assertEqual(payload["pollen_types"][0]["code"], "li-ke")

    def test_point_profile_series_api_returns_sample_series(self):
        response = self.client.get(reverse("api-profile-series", kwargs={"pk": self.profile.pk}))
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["profile"]["name"], "北京")
        self.assertEqual(payload["series"][0]["value"], 23.5)
