from django.conf import settings
from django.db import models
from django.db.models.functions import Lower
from wagtail.models import Page


class UsedToken(models.Model):
    """Tracks consumed magic link tokens to enforce single-use policy."""

    token_hash = models.CharField(
        max_length=64,
        unique=True,
        db_index=True,
        help_text="SHA-256 hash of the consumed sesame token.",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Použitý token"
        verbose_name_plural = "Použité tokeny"
        ordering = ["-created_at"]

    def __str__(self):
        return f"UsedToken({self.token_hash[:12]}…, {self.created_at})"


class UserProfile(models.Model):
    """Per-user display name for the public frontend (set after first login)."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="msl_profile",
    )
    display_name = models.CharField(max_length=30, null=True, blank=True)

    class Meta:
        verbose_name = "Profil uživatele"
        verbose_name_plural = "Profily uživatelů"
        constraints = [
            models.UniqueConstraint(
                Lower("display_name"),
                name="msl_auth_userprofile_display_name_ci_unique",
            ),
        ]

    def __str__(self):
        return self.display_name or f"<no name> ({self.user_id})"


class LoginPage(Page):
    """Wagtail page providing passwordless magic-link login."""

    subpage_types: list = []

    class Meta:
        verbose_name = "Přihlášení uživatele"
        verbose_name_plural = "Přihlášení uživatele"

    def serve(self, request):
        from .views import serve_login_page

        return serve_login_page(request, self)
