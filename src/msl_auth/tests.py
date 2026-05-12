"""
Tests for the magic-link authentication feature.

Coverage:
- Token expiry (10-minute TTL)
- Single-use enforcement (token cannot be reused)
- Successful login sets session / authenticates the user
- Redirect after login removes the token from the URL
- Rate limiting helpers
- Safe-URL validation
"""

import time
from unittest.mock import patch
from urllib.parse import urlparse, parse_qs

from django.contrib.auth import get_user_model
from django.test import TestCase, Client, override_settings
from django.urls import reverse

import sesame.utils

from msl_auth.models import UsedToken
from util.magic_link_auth import (
    get_or_create_user,
    hash_token,
    verify_and_consume_token,
    check_rate_limit,
    increment_rate_limit,
    is_safe_next_url,
    RATE_LIMIT_MAX,
)

User = get_user_model()


# ── Helpers ───────────────────────────────────────────────────────────────────

class FakeRequest:
    """Minimal request-like object used in unit tests."""

    def __init__(self, host="testserver", secure=False):
        self._host = host
        self._secure = secure

    def is_secure(self):
        return self._secure

    def get_host(self):
        return self._host

    META = {}


# ── User helpers ──────────────────────────────────────────────────────────────

class GetOrCreateUserTests(TestCase):

    def test_creates_user_when_absent(self):
        user = get_or_create_user("newuser@example.com")
        self.assertEqual(user.email, "newuser@example.com")
        self.assertFalse(user.has_usable_password())

    def test_returns_existing_user(self):
        first = get_or_create_user("exist@example.com")
        second = get_or_create_user("exist@example.com")
        self.assertEqual(first.pk, second.pk)

    def test_email_lowercased(self):
        user = get_or_create_user("UPPER@EXAMPLE.COM")
        self.assertEqual(user.email, "upper@example.com")


# ── Token hash ────────────────────────────────────────────────────────────────

class HashTokenTests(TestCase):

    def test_returns_64_hex_chars(self):
        digest = hash_token("some-token")
        self.assertEqual(len(digest), 64)
        self.assertTrue(all(c in "0123456789abcdef" for c in digest))

    def test_deterministic(self):
        self.assertEqual(hash_token("abc"), hash_token("abc"))

    def test_different_tokens_different_hashes(self):
        self.assertNotEqual(hash_token("token1"), hash_token("token2"))


# ── verify_and_consume_token ──────────────────────────────────────────────────

@override_settings(SESAME_MAX_AGE=600)
class VerifyAndConsumeTokenTests(TestCase):

    def setUp(self):
        self.user = get_or_create_user("verify@example.com")

    def test_valid_token_returns_user(self):
        token = sesame.utils.get_token(self.user)
        result = verify_and_consume_token(token)
        self.assertEqual(result, self.user)

    def test_token_is_single_use(self):
        """Second call with same token must return 'used'."""
        token = sesame.utils.get_token(self.user)
        first = verify_and_consume_token(token)
        self.assertEqual(first, self.user)

        second = verify_and_consume_token(token)
        self.assertEqual(second, "used")

    def test_invalid_token_returns_expired(self):
        result = verify_and_consume_token("totally-invalid-garbage")
        self.assertEqual(result, "expired")

    def test_already_used_token_hash_stored(self):
        token = sesame.utils.get_token(self.user)
        verify_and_consume_token(token)
        self.assertTrue(UsedToken.objects.filter(token_hash=hash_token(token)).exists())

    @override_settings(SESAME_MAX_AGE=1)
    def test_expired_token_rejected(self):
        """Token with 1-second TTL must be rejected after sleeping 2 seconds."""
        token = sesame.utils.get_token(self.user)
        time.sleep(2)
        result = verify_and_consume_token(token)
        self.assertEqual(result, "expired")


# ── Rate limiting ─────────────────────────────────────────────────────────────

class RateLimitTests(TestCase):

    def setUp(self):
        from django.core.cache import cache
        cache.clear()

    def test_not_limited_initially(self):
        self.assertFalse(check_rate_limit("1.2.3.4", "test@example.com"))

    def test_limited_after_max_attempts(self):
        for _ in range(RATE_LIMIT_MAX):
            increment_rate_limit("1.2.3.4", "test@example.com")
        self.assertTrue(check_rate_limit("1.2.3.4", "test@example.com"))

    def test_limited_per_ip(self):
        """Exceeding per-IP limit blocks even for a new email."""
        for _ in range(RATE_LIMIT_MAX):
            increment_rate_limit("9.9.9.9", "a@example.com")
        self.assertTrue(check_rate_limit("9.9.9.9", "other@example.com"))

    def test_limited_per_email(self):
        """Exceeding per-email limit blocks even from a new IP."""
        for _ in range(RATE_LIMIT_MAX):
            increment_rate_limit("1.1.1.1", "shared@example.com")
        self.assertTrue(check_rate_limit("2.2.2.2", "shared@example.com"))


# ── Safe URL validation ───────────────────────────────────────────────────────

class SafeNextUrlTests(TestCase):

    def _req(self, host="testserver"):
        return FakeRequest(host=host)

    def test_empty_url_is_unsafe(self):
        self.assertFalse(is_safe_next_url(self._req(), ""))

    def test_relative_url_is_safe(self):
        self.assertTrue(is_safe_next_url(self._req(), "/some/page/"))

    def test_external_url_is_unsafe(self):
        self.assertFalse(is_safe_next_url(self._req("testserver"), "https://evil.com/steal"))

    def test_javascript_url_is_unsafe(self):
        self.assertFalse(is_safe_next_url(self._req(), "javascript:alert(1)"))


# ── verify_magic_link view ────────────────────────────────────────────────────

class VerifyMagicLinkViewTests(TestCase):

    def setUp(self):
        self.client = Client()
        self.user = get_or_create_user("viewtest@example.com")
        self.verify_url = reverse("msl_auth:magic_link_verify")

    def test_no_token_returns_redirect(self):
        resp = self.client.get(self.verify_url)
        self.assertEqual(resp.status_code, 302)

    def test_valid_token_authenticates_user(self):
        token = sesame.utils.get_token(self.user)
        resp = self.client.get(self.verify_url, {"sesame": token})
        # Should redirect (to login page or /)
        self.assertEqual(resp.status_code, 302)
        # User should now be authenticated in the session
        self.assertEqual(
            int(self.client.session["_auth_user_id"]), self.user.pk
        )

    def test_redirect_url_does_not_contain_token(self):
        """After verification, the redirect target must not include the sesame token."""
        token = sesame.utils.get_token(self.user)
        resp = self.client.get(self.verify_url, {"sesame": token})
        self.assertEqual(resp.status_code, 302)
        redirect_location = resp["Location"]
        self.assertNotIn("sesame=", redirect_location)

    def test_invalid_token_does_not_authenticate(self):
        resp = self.client.get(self.verify_url, {"sesame": "bad-token"})
        self.assertEqual(resp.status_code, 302)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_reused_token_rejected(self):
        token = sesame.utils.get_token(self.user)
        # First use
        self.client.get(self.verify_url, {"sesame": token})
        self.client.logout()
        # Second use
        resp = self.client.get(self.verify_url, {"sesame": token})
        self.assertEqual(resp.status_code, 302)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_next_redirect_used_when_safe(self):
        token = sesame.utils.get_token(self.user)
        resp = self.client.get(
            self.verify_url, {"sesame": token, "next": "/some-safe-path/"}
        )
        self.assertRedirects(resp, "/some-safe-path/", fetch_redirect_response=False)

    def test_unsafe_next_param_ignored(self):
        token = sesame.utils.get_token(self.user)
        resp = self.client.get(
            self.verify_url,
            {"sesame": token, "next": "https://evil.com/"},
        )
        self.assertEqual(resp.status_code, 302)
        self.assertNotIn("evil.com", resp["Location"])


# ── logout view ───────────────────────────────────────────────────────────────

class LogoutViewTests(TestCase):

    def setUp(self):
        self.client = Client()
        self.user = get_or_create_user("logout@example.com")
        self.logout_url = reverse("msl_auth:magic_link_logout")

    def _login(self):
        token = sesame.utils.get_token(self.user)
        verify_url = reverse("msl_auth:magic_link_verify")
        self.client.get(verify_url, {"sesame": token})

    def test_post_logs_out_user(self):
        self._login()
        self.assertIn("_auth_user_id", self.client.session)
        self.client.post(self.logout_url)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_get_does_not_log_out(self):
        """GET request to logout must NOT terminate the session."""
        self._login()
        self.client.get(self.logout_url)
        # User should still be logged in
        self.assertIn("_auth_user_id", self.client.session)
