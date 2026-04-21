from django.conf import settings
from django.db import models


class SiteConfiguration(models.Model):
    title = models.CharField(max_length=128, default=settings.SITE_TITLE)
    subtitle = models.CharField(max_length=255, default=settings.SITE_SUBTITLE)
    hero_notice = models.CharField(max_length=255, blank=True)
    copyright_notice = models.CharField(max_length=255, default=settings.SITE_COPYRIGHT)
    map_center_lon = models.FloatField(default=104.0)
    map_center_lat = models.FloatField(default=35.5)
    map_zoom = models.FloatField(default=4.5)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "站点配置"
        verbose_name_plural = "站点配置"

    def __str__(self):
        return self.title

    @classmethod
    def load(cls):
        obj = cls.objects.first()
        if obj:
            return obj
        return cls()


class FriendlyLink(models.Model):
    name = models.CharField(max_length=100)
    url = models.URLField()
    description = models.CharField(max_length=255, blank=True)
    sort_order = models.PositiveIntegerField(default=0)
    enabled = models.BooleanField(default=True)

    class Meta:
        ordering = ("sort_order", "name")
        verbose_name = "友情链接"
        verbose_name_plural = "友情链接"

    def __str__(self):
        return self.name
