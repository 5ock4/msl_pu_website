"""Middleware that forces authenticated users to set a public display name."""

from django.shortcuts import redirect
from django.urls import reverse

from .models import UserProfile


class RequireDisplayNameMiddleware:
    """Redirect logged-in users without a display name to the setup page.

    Exempt paths (admin, static assets, the auth endpoints themselves) are let
    through so users can still log out / access the CMS while picking a name.
    """

    EXEMPT_PREFIXES = (
        "/admin/",
        "/django-admin/",
        "/documents/",
        "/static/",
        "/media/",
        "/auth/",
    )

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, "user", None)
        if user is None or not user.is_authenticated:
            return self.get_response(request)

        path = request.path
        if any(path.startswith(p) for p in self.EXEMPT_PREFIXES):
            return self.get_response(request)

        try:
            profile = user.msl_profile
        except UserProfile.DoesNotExist:
            profile = None

        if profile and profile.display_name:
            return self.get_response(request)

        setup_url = reverse("msl_auth:setup_username")
        return redirect(f"{setup_url}?next={path}")
