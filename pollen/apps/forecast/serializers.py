from rest_framework import serializers

from pollen.apps.forecast.models import ForecastDomain, ForecastProduct, PointQueryProfile, PollenType
from pollen.apps.workflows.models import WorkflowRun


class PollenTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = PollenType
        fields = ("id", "code", "name", "scientific_name", "color_hex")


class ForecastDomainSerializer(serializers.ModelSerializer):
    class Meta:
        model = ForecastDomain
        fields = ("id", "code", "name", "extent", "resolution_km", "center_lon", "center_lat", "default_opacity")


class ForecastProductSerializer(serializers.ModelSerializer):
    pollen_type = PollenTypeSerializer()
    domain = ForecastDomainSerializer()

    class Meta:
        model = ForecastProduct
        fields = (
            "id",
            "run_time",
            "valid_time",
            "forecast_hour",
            "geotiff_path",
            "tile_url_template",
            "preview_image_path",
            "stats_json_path",
            "metadata",
            "passed_validation",
            "is_published",
            "pollen_type",
            "domain",
        )


class PointQueryProfileSerializer(serializers.ModelSerializer):
    pollen_type = PollenTypeSerializer()
    domain = ForecastDomainSerializer()

    class Meta:
        model = PointQueryProfile
        fields = (
            "id",
            "name",
            "description",
            "longitude",
            "latitude",
            "chart_type",
            "sample_series",
            "pollen_type",
            "domain",
        )


class WorkflowRunSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkflowRun
        fields = ("id", "status", "business_time", "published_at", "trigger_mode", "summary")
