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

from msl_auth.models import UsedToken, UserProfile
from msl_auth.forms import DisplayNameForm
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

    def test_matches_existing_user_with_non_email_username(self):
        """Pre-existing admin account (username != email) must be reused."""
        admin = User.objects.create_user(
            username="as", email="strakosadam@gmail.com", password="x"
        )
        user = get_or_create_user("strakosadam@gmail.com")
        self.assertEqual(user.pk, admin.pk)
        self.assertEqual(user.username, "as")

    def test_email_match_case_insensitive(self):
        admin = User.objects.create_user(
            username="as", email="Strakosadam@Gmail.com", password="x"
        )
        user = get_or_create_user("strakosadam@gmail.com")
        self.assertEqual(user.pk, admin.pk)


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


# ── UserProfile creation ──────────────────────────────────────────────────────

class UserProfileAutoCreateTests(TestCase):

    def test_get_or_create_user_creates_profile(self):
        user = get_or_create_user("profile@example.com")
        self.assertTrue(UserProfile.objects.filter(user=user).exists())
        self.assertIsNone(user.msl_profile.display_name)


# ── DisplayNameForm ───────────────────────────────────────────────────────────

class DisplayNameFormTests(TestCase):

    def setUp(self):
        self.user = get_or_create_user("form@example.com")

    def test_accepts_valid_name(self):
        form = DisplayNameForm({"display_name": "honza42"}, user=self.user)
        self.assertTrue(form.is_valid(), form.errors)

    def test_rejects_too_short(self):
        form = DisplayNameForm({"display_name": "ab"}, user=self.user)
        self.assertFalse(form.is_valid())

    def test_rejects_too_long(self):
        form = DisplayNameForm({"display_name": "x" * 31}, user=self.user)
        self.assertFalse(form.is_valid())

    def test_rejects_bad_chars(self):
        form = DisplayNameForm({"display_name": "bad name!"}, user=self.user)
        self.assertFalse(form.is_valid())

    def test_rejects_duplicate_case_insensitive(self):
        other = get_or_create_user("other@example.com")
        other.msl_profile.display_name = "Honza42"
        other.msl_profile.save()

        form = DisplayNameForm({"display_name": "honza42"}, user=self.user)
        self.assertFalse(form.is_valid())
        self.assertIn("display_name", form.errors)

    def test_allows_own_name_on_re_edit(self):
        self.user.msl_profile.display_name = "honza42"
        self.user.msl_profile.save()
        form = DisplayNameForm({"display_name": "honza42"}, user=self.user)
        self.assertTrue(form.is_valid(), form.errors)


# ── setup_username view ──────────────────────────────────────────────────────

_NON_MANIFEST_STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}


@override_settings(STORAGES=_NON_MANIFEST_STORAGES)
class SetupUsernameViewTests(TestCase):

    def setUp(self):
        self.client = Client()
        self.user = get_or_create_user("setup@example.com")
        self.setup_url = reverse("msl_auth:setup_username")

    def _login(self):
        token = sesame.utils.get_token(self.user)
        self.client.get(reverse("msl_auth:magic_link_verify"), {"sesame": token})

    def test_anonymous_redirected(self):
        resp = self.client.get(self.setup_url)
        self.assertEqual(resp.status_code, 302)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_get_shows_form_when_logged_in(self):
        self._login()
        resp = self.client.get(self.setup_url)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "display_name")

    def test_post_sets_display_name_and_redirects(self):
        self._login()
        resp = self.client.post(
            self.setup_url,
            {"display_name": "newname", "next": "/some-page/"},
        )
        self.assertRedirects(resp, "/some-page/", fetch_redirect_response=False)
        self.user.msl_profile.refresh_from_db()
        self.assertEqual(self.user.msl_profile.display_name, "newname")

    def test_unsafe_next_falls_back_to_root(self):
        self._login()
        resp = self.client.post(
            self.setup_url,
            {"display_name": "newname2", "next": "https://evil.com/"},
        )
        self.assertRedirects(resp, "/", fetch_redirect_response=False)

    def test_already_set_shows_form_prepopulated(self):
        self._login()
        self.user.msl_profile.display_name = "already"
        self.user.msl_profile.save()
        resp = self.client.get(self.setup_url)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'value="already"')

    def test_post_updates_existing_display_name(self):
        self._login()
        self.user.msl_profile.display_name = "oldname"
        self.user.msl_profile.save()
        resp = self.client.post(self.setup_url, {"display_name": "newname"})
        self.assertRedirects(resp, "/", fetch_redirect_response=False)
        self.user.msl_profile.refresh_from_db()
        self.assertEqual(self.user.msl_profile.display_name, "newname")

    def test_integrity_error_on_save_shown_as_form_error(self):
        """A race past the form check (DB unique constraint) renders cleanly."""
        from django.db import IntegrityError

        self._login()
        with patch(
            "msl_auth.models.UserProfile.save",
            side_effect=IntegrityError("duplicate"),
        ):
            resp = self.client.post(self.setup_url, {"display_name": "racey"})
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "již obsazené")
        self.user.msl_profile.refresh_from_db()
        self.assertIsNone(self.user.msl_profile.display_name)


# ── RequireDisplayNameMiddleware ──────────────────────────────────────────────

class RequireDisplayNameMiddlewareTests(TestCase):

    def setUp(self):
        self.client = Client()
        self.user = get_or_create_user("mw@example.com")
        self.setup_url = reverse("msl_auth:setup_username")

    def _login(self):
        token = sesame.utils.get_token(self.user)
        self.client.get(reverse("msl_auth:magic_link_verify"), {"sesame": token})

    def test_anonymous_request_passes_through(self):
        # Anonymous hitting "/" — should not bounce to setup.
        resp = self.client.get("/")
        self.assertNotIn(self.setup_url, resp.get("Location", ""))

    def test_authenticated_without_name_redirected_to_setup(self):
        self._login()
        resp = self.client.get("/")
        self.assertEqual(resp.status_code, 302)
        self.assertIn(self.setup_url, resp["Location"])
        self.assertIn("next=/", resp["Location"])

    def test_exempt_admin_path_not_redirected(self):
        self._login()
        resp = self.client.get("/admin/", follow=False)
        # Whatever the admin returns (302 to login, 200, etc.), it must NOT
        # be a redirect to our setup URL.
        self.assertNotIn(self.setup_url, resp.get("Location", ""))

    def test_exempt_auth_path_not_redirected(self):
        self._login()
        resp = self.client.get(reverse("msl_auth:magic_link_verify"))
        self.assertNotIn(self.setup_url, resp.get("Location", ""))

    def test_authenticated_with_name_passes_through(self):
        self._login()
        self.user.msl_profile.display_name = "namedone"
        self.user.msl_profile.save()
        resp = self.client.get("/")
        self.assertNotIn(self.setup_url, resp.get("Location", ""))
