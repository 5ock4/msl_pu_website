"""
Magic-link authentication utilities.

Responsibilities:
- Create / retrieve users by email address.
- Generate a one-time magic-link URL (via django-sesame).
- Send the magic-link email.
- Verify the token and enforce single-use (via the UsedToken model).
- Rate-limiting helpers (per-IP and per-email).
- Safe URL validation for the `next` parameter.
"""

import hashlib
from urllib.parse import quote

import sesame.utils

from django.conf import settings
from django.core.cache import cache
from django.core.mail import send_mail
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme

User = get_user_model()

# ── Rate-limiting constants ───────────────────────────────────────────────────
RATE_LIMIT_MAX = 5       # maximum attempts per window
RATE_LIMIT_WINDOW = 300  # window length in seconds (5 minutes)


# ── User helpers ─────────────────────────────────────────────────────────────

def get_or_create_user(email: str):
    """
    Return (and possibly create) a User whose identity is *email*.

    New users receive an unusable password so they cannot log in via the
    standard password form.
    """
    email = email.lower().strip()
    # Use email as the unique lookup; derive a username from it.
    user, created = User.objects.get_or_create(
        email=email,
        defaults={"username": email[:150], "is_active": True},
    )
    if created:
        user.set_unusable_password()
        user.save(update_fields=["password"])
    return user


# ── Token helpers ─────────────────────────────────────────────────────────────

def hash_token(token: str) -> str:
    """Return the hex-encoded SHA-256 digest of *token*."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def generate_magic_link_url(request, user, next_url: str | None = None) -> str:
    """
    Build an absolute magic-link URL for *user*.

    The URL points to the token-verification view and embeds a sesame token.
    An optional *next_url* parameter is included when provided.
    """
    token = sesame.utils.get_token(user)
    verify_path = reverse("msl_auth:magic_link_verify")
    params = f"sesame={quote(token, safe='')}"
    if next_url:
        params += f"&next={quote(next_url, safe='')}"

    scheme = "https" if request.is_secure() else "http"
    host = request.get_host()
    return f"{scheme}://{host}{verify_path}?{params}"


def send_magic_link_email(email: str, magic_link_url: str) -> None:
    """Send the magic-link email to *email*."""
    subject = "Přihlašovací odkaz – MSL"
    body = (
        "Dobrý den,\n\n"
        "klikněte na odkaz níže pro přihlášení na web MSL:\n\n"
        f"{magic_link_url}\n\n"
        "Odkaz je platný 10 minut a lze jej použít pouze jednou.\n\n"
        "Pokud jste o přihlášení nežádali, tento e-mail prosím ignorujte.\n\n"
        "S pozdravem,\nTým MSL"
    )
    send_mail(
        subject,
        body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[email],
        fail_silently=False,
    )


def generate_and_send_magic_link(request, user, next_url: str | None = None) -> str:
    """
    Generate a magic-link URL and dispatch the email.

    Returns the generated URL (useful in tests / admin commands).
    """
    url = generate_magic_link_url(request, user, next_url=next_url)
    send_magic_link_email(user.email, url)
    return url


# ── Token verification ────────────────────────────────────────────────────────

def verify_and_consume_token(token: str):
    """
    Verify *token* and, if valid and unused, mark it as consumed.

    Returns
    -------
    - The ``User`` instance when the token is valid and unused.
    - ``"used"``    when the token hash already exists in ``UsedToken``.
    - ``"expired"`` when sesame rejects the token (expired or bad signature).
    """
    from msl_auth.models import UsedToken

    token_hash = hash_token(token)

    # Reject already-consumed tokens first (cheapest check).
    if UsedToken.objects.filter(token_hash=token_hash).exists():
        return "used"

    # Let sesame validate the signature and TTL.
    user = sesame.utils.get_user(token)
    if user is None:
        return "expired"

    # Atomically record the token as consumed.
    UsedToken.objects.get_or_create(token_hash=token_hash)
    return user


# ── Rate limiting ─────────────────────────────────────────────────────────────

def _ip_cache_key(ip: str) -> str:
    return f"magic_link_rl_ip_{hashlib.sha256(ip.encode()).hexdigest()[:24]}"


def _email_cache_key(email: str) -> str:
    return f"magic_link_rl_email_{hashlib.sha256(email.encode()).hexdigest()[:24]}"


def check_rate_limit(ip: str, email: str) -> bool:
    """Return ``True`` when either the per-IP or per-email limit is exceeded."""
    ip_count = cache.get(_ip_cache_key(ip), 0)
    email_count = cache.get(_email_cache_key(email), 0)
    return ip_count >= RATE_LIMIT_MAX or email_count >= RATE_LIMIT_MAX


def increment_rate_limit(ip: str, email: str) -> None:
    """Increment rate-limit counters for *ip* and *email*."""
    for key in (_ip_cache_key(ip), _email_cache_key(email)):
        try:
            cache.incr(key)
        except ValueError:
            # Key does not exist yet – set it with the expiry window.
            cache.set(key, 1, RATE_LIMIT_WINDOW)


# ── URL safety ────────────────────────────────────────────────────────────────

def is_safe_next_url(request, url: str) -> bool:
    """Return ``True`` when *url* is safe to redirect to after login."""
    if not url:
        return False
    return url_has_allowed_host_and_scheme(
        url=url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    )


# ── Request helpers ───────────────────────────────────────────────────────────

def get_client_ip(request) -> str:
    """Extract the client IP address from *request*."""
    forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "")
