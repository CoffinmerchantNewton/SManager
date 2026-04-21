from django.contrib import admin

from pollen.apps.core.models import FriendlyLink, SiteConfiguration


@admin.register(SiteConfiguration)
class SiteConfigurationAdmin(admin.ModelAdmin):
    list_display = ("title", "updated_at")


@admin.register(FriendlyLink)
class FriendlyLinkAdmin(admin.ModelAdmin):
    list_display = ("name", "url", "sort_order", "enabled")
    list_editable = ("sort_order", "enabled")
