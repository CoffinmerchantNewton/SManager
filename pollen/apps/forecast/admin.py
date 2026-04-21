from django.contrib import admin

from pollen.apps.forecast.models import ForecastDomain, ForecastProduct, PointQueryProfile, PollenType


@admin.register(PollenType)
class PollenTypeAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "color_hex", "sort_order", "is_active")
    list_editable = ("sort_order", "is_active")
    prepopulated_fields = {"code": ("name",)}


@admin.register(ForecastDomain)
class ForecastDomainAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "resolution_km", "sort_order", "is_active")
    list_editable = ("sort_order", "is_active")


@admin.register(PointQueryProfile)
class PointQueryProfileAdmin(admin.ModelAdmin):
    list_display = ("name", "longitude", "latitude", "chart_type", "is_featured")
    list_filter = ("chart_type", "is_featured", "domain", "pollen_type")


@admin.register(ForecastProduct)
class ForecastProductAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "run",
        "domain",
        "pollen_type",
        "forecast_hour",
        "passed_validation",
        "is_published",
    )
    list_filter = ("domain", "pollen_type", "is_published", "passed_validation")
