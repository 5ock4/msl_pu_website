from django.conf import settings


def site_version(request):
    """Add SITE_VERSION from settings into the template context."""
    return {"SITE_VERSION": getattr(settings, "SITE_VERSION", "")}
