from django.db import models


class PollenType(models.Model):
    code = models.SlugField(unique=True)
    name = models.CharField(max_length=100)
    scientific_name = models.CharField(max_length=150, blank=True)
    description = models.TextField(blank=True)
    color_hex = models.CharField(max_length=7, default="#69c0ff")
    sort_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ("sort_order", "name")
        verbose_name = "花粉类别"
        verbose_name_plural = "花粉类别"

    def __str__(self):
        return self.name


class ForecastDomain(models.Model):
    code = models.CharField(max_length=10, unique=True)
    name = models.CharField(max_length=100)
    description = models.CharField(max_length=255, blank=True)
    extent = models.JSONField(default=list, help_text="[min_lon, min_lat, max_lon, max_lat]")
    resolution_km = models.DecimalField(max_digits=6, decimal_places=2, default=9.0)
    center_lon = models.FloatField(default=104.0)
    center_lat = models.FloatField(default=35.5)
    default_opacity = models.FloatField(default=0.72)
    sort_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ("sort_order", "code")
        verbose_name = "预报域"
        verbose_name_plural = "预报域"

    def __str__(self):
        return self.code


class PointQueryProfile(models.Model):
    CHART_TYPES = [
        ("line", "折线图"),
        ("bar", "柱状图"),
    ]

    name = models.CharField(max_length=100)
    description = models.CharField(max_length=255, blank=True)
    longitude = models.FloatField()
    latitude = models.FloatField()
    pollen_type = models.ForeignKey(
        PollenType,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="point_profiles",
    )
    domain = models.ForeignKey(
        ForecastDomain,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="point_profiles",
    )
    chart_type = models.CharField(max_length=20, choices=CHART_TYPES, default="line")
    sample_series = models.JSONField(default=list, blank=True)
    is_featured = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ("sort_order", "name")
        verbose_name = "点位分析配置"
        verbose_name_plural = "点位分析配置"

    def __str__(self):
        return self.name


class ForecastProduct(models.Model):
    run = models.ForeignKey(
        "workflows.WorkflowRun",
        on_delete=models.CASCADE,
        related_name="products",
    )
    pollen_type = models.ForeignKey(PollenType, on_delete=models.CASCADE, related_name="products")
    domain = models.ForeignKey(ForecastDomain, on_delete=models.CASCADE, related_name="products")
    run_time = models.DateTimeField()
    valid_time = models.DateTimeField()
    forecast_hour = models.PositiveIntegerField(default=0)
    geotiff_path = models.CharField(max_length=255, blank=True)
    tile_url_template = models.CharField(max_length=255, blank=True)
    preview_image_path = models.CharField(max_length=255, blank=True)
    stats_json_path = models.CharField(max_length=255, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    passed_validation = models.BooleanField(default=False)
    is_published = models.BooleanField(default=False)
    published_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-valid_time", "domain__code", "pollen_type__name")
        unique_together = ("run", "pollen_type", "domain", "valid_time")
        verbose_name = "预报产物"
        verbose_name_plural = "预报产物"

    def __str__(self):
        return f"{self.run_id}:{self.domain.code}:{self.pollen_type.name}:{self.valid_time}"
