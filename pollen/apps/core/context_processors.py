from pollen.apps.core.models import FriendlyLink, SiteConfiguration


def shell_context(request):
    return {
        "site_config": SiteConfiguration.load(),
        "friendly_links": FriendlyLink.objects.filter(enabled=True).order_by("sort_order", "name")[:8],
    }
