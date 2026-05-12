from django.db import models
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


class LoginPage(Page):
    """Wagtail page providing passwordless magic-link login."""

    subpage_types: list = []

    class Meta:
        verbose_name = "Přihlášení uživatele"
        verbose_name_plural = "Přihlášení uživatele"

    def serve(self, request):
        from .views import serve_login_page

        return serve_login_page(request, self)
