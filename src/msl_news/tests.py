from unittest.mock import MagicMock, patch

from django.contrib.auth.models import User
from django.contrib.messages import get_messages
from django.test import TestCase, RequestFactory, override_settings
from django.urls import reverse


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_page(
    title="Test Article",
    body="<p>Body text</p>",
    full_url="http://example.com/news/test/",
    facebook_post_id="",
):
    page = MagicMock()
    page.title = title
    page.body = body
    page.get_full_url.return_value = full_url
    page.facebook_post_id = facebook_post_id
    page.specific = page  # page.specific.save() used when storing new post ID
    return page


# ---------------------------------------------------------------------------
# post_news_to_facebook
# ---------------------------------------------------------------------------

class PostNewsToFacebookTests(TestCase):

    @override_settings(FACEBOOK_PAGE_ID="123456", FACEBOOK_APP_ID="app-id")
    @patch("msl_news.facebook.get_stored_token", return_value="test-token")
    @patch("msl_news.facebook.requests.post")
    def test_creates_new_post_when_no_existing_post_id(self, mock_post, _mock_token):
        mock_post.return_value.raise_for_status = MagicMock()
        mock_post.return_value.json.return_value = {"id": "123456_999"}

        from msl_news.facebook import post_news_to_facebook

        page = _make_page()
        post_news_to_facebook(page)

        mock_post.assert_called_once()
        call_kwargs = mock_post.call_args
        self.assertIn("123456", call_kwargs[0][0])
        payload = call_kwargs[1]["data"]
        self.assertIn("Test Article", payload["message"])
        self.assertIn("Body text", payload["message"])
        self.assertEqual(payload["link"], "http://example.com/news/test/")
        self.assertEqual(payload["access_token"], "test-token")
        # FB post ID should be saved back to the page
        self.assertEqual(page.facebook_post_id, "123456_999")

    @override_settings(FACEBOOK_PAGE_ID="123456", FACEBOOK_APP_ID="app-id")
    @patch("msl_news.facebook.get_stored_token", return_value="test-token")
    @patch("msl_news.facebook.requests.post")
    def test_edits_existing_post_when_post_id_stored(self, mock_post, _mock_token):
        mock_post.return_value.raise_for_status = MagicMock()

        from msl_news.facebook import post_news_to_facebook

        page = _make_page(facebook_post_id="123456_777")
        post_news_to_facebook(page)

        mock_post.assert_called_once()
        call_url = mock_post.call_args[0][0]
        self.assertIn("123456_777", call_url)
        payload = mock_post.call_args[1]["data"]
        self.assertIn("Test Article", payload["message"])
        # link should NOT be present when editing
        self.assertNotIn("link", payload)
        self.assertEqual(payload["access_token"], "test-token")

    # Keep the old name as an alias so existing test references still pass
    test_posts_to_facebook_when_configured = test_creates_new_post_when_no_existing_post_id

    @override_settings(FACEBOOK_PAGE_ID="", FACEBOOK_APP_ID="")
    @patch("msl_news.facebook.requests.post")
    def test_skips_when_not_configured(self, mock_post):
        from msl_news.facebook import post_news_to_facebook

        page = _make_page()
        post_news_to_facebook(page)

        mock_post.assert_not_called()

    @override_settings(FACEBOOK_PAGE_ID="123456", FACEBOOK_APP_ID="app-id")
    @patch("msl_news.facebook.get_stored_token", return_value="test-token")
    @patch("msl_news.facebook.requests.post")
    def test_strips_html_from_body(self, mock_post, _mock_token):
        mock_post.return_value.raise_for_status = MagicMock()
        mock_post.return_value.json.return_value = {"id": "123456_001"}

        from msl_news.facebook import post_news_to_facebook

        page = _make_page(body="<p>Hello <strong>world</strong></p>")
        post_news_to_facebook(page)

        payload = mock_post.call_args[1]["data"]
        self.assertNotIn("<p>", payload["message"])
        self.assertNotIn("<strong>", payload["message"])
        self.assertIn("Hello world", payload["message"])

    @override_settings(FACEBOOK_PAGE_ID="123456", FACEBOOK_APP_ID="app-id")
    @patch("msl_news.facebook.get_stored_token", return_value="test-token")
    @patch("msl_news.facebook.requests.post")
    def test_handles_request_error_gracefully(self, mock_post, _mock_token):
        import requests as req

        mock_post.side_effect = req.RequestException("Connection error")

        from msl_news.facebook import post_news_to_facebook

        page = _make_page()
        # Should not raise
        post_news_to_facebook(page)

    @override_settings(FACEBOOK_PAGE_ID="123456", FACEBOOK_APP_ID="app-id")
    @patch("msl_news.facebook.get_stored_token", return_value="test-token")
    @patch("msl_news.facebook.requests.post")
    def test_edit_handles_request_error_gracefully(self, mock_post, _mock_token):
        import requests as req

        mock_post.side_effect = req.RequestException("Connection error")

        from msl_news.facebook import post_news_to_facebook

        page = _make_page(facebook_post_id="123456_777")
        # Should not raise
        post_news_to_facebook(page)

    @override_settings(FACEBOOK_PAGE_ID="123456", FACEBOOK_APP_ID="app-id")
    @patch("msl_news.facebook.get_stored_token", return_value=None)
    @patch("msl_news.facebook.requests.post")
    def test_skips_when_no_valid_token_in_db(self, mock_post, _mock_token):
        from msl_news.facebook import post_news_to_facebook

        page = _make_page()
        post_news_to_facebook(page)

        mock_post.assert_not_called()


# ---------------------------------------------------------------------------
# Facebook OAuth views
# ---------------------------------------------------------------------------

class FacebookOAuthInitiateTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("admin", password="pass")
        self.client.login(username="admin", password="pass")

    @override_settings(FACEBOOK_APP_ID="test-app-id", FACEBOOK_APP_SECRET="test-secret", FACEBOOK_PAGE_ID="123456")
    def test_redirects_to_facebook_dialog(self):
        response = self.client.get(reverse("facebook_oauth_initiate"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("facebook.com/dialog/oauth", response["Location"])
        self.assertIn("test-app-id", response["Location"])

    @override_settings(FACEBOOK_APP_ID="")
    def test_error_when_app_id_not_configured(self):
        response = self.client.get(reverse("facebook_oauth_initiate"))
        self.assertEqual(response.status_code, 302)
        msgs = list(get_messages(response.wsgi_request))
        self.assertTrue(any("FACEBOOK_APP_ID" in str(m) for m in msgs))

    def test_requires_login(self):
        self.client.logout()
        response = self.client.get(reverse("facebook_oauth_initiate"))
        self.assertEqual(response.status_code, 302)
        self.assertNotIn("facebook.com", response["Location"])


class FacebookOAuthCallbackTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("admin", password="pass")
        self.client.login(username="admin", password="pass")

    @override_settings(
        FACEBOOK_APP_ID="app-id",
        FACEBOOK_APP_SECRET="app-secret",
        FACEBOOK_PAGE_ID="123456",
    )
    @patch("msl_news.views.exchange_code_for_page_token", return_value=("123456", "page-token"))
    def test_stores_token_and_shows_success(self, mock_exchange):
        session = self.client.session
        session["facebook_oauth_state"] = "valid-state"
        session.save()

        response = self.client.get(
            reverse("facebook_oauth_callback"),
            {"code": "auth-code", "state": "valid-state"},
        )
        self.assertEqual(response.status_code, 302)
        mock_exchange.assert_called_once()
        msgs = list(get_messages(response.wsgi_request))
        self.assertTrue(any("successfully" in str(m) for m in msgs))

    def test_error_on_facebook_error_param(self):
        response = self.client.get(
            reverse("facebook_oauth_callback"),
            {"error": "access_denied", "error_description": "User denied"},
        )
        self.assertEqual(response.status_code, 302)
        msgs = list(get_messages(response.wsgi_request))
        self.assertTrue(any("User denied" in str(m) for m in msgs))

    def test_error_on_state_mismatch(self):
        session = self.client.session
        session["facebook_oauth_state"] = "expected-state"
        session.save()

        response = self.client.get(
            reverse("facebook_oauth_callback"),
            {"code": "some-code", "state": "wrong-state"},
        )
        self.assertEqual(response.status_code, 302)
        msgs = list(get_messages(response.wsgi_request))
        self.assertTrue(any("invalid" in str(m).lower() for m in msgs))

    def test_requires_login(self):
        self.client.logout()
        response = self.client.get(
            reverse("facebook_oauth_callback"),
            {"code": "c", "state": "s"},
        )
        self.assertEqual(response.status_code, 302)


# ---------------------------------------------------------------------------
# before_publish_page hook
# ---------------------------------------------------------------------------

class BeforePublishPageHookTests(TestCase):
    def _make_request(self, user=None):
        factory = RequestFactory()
        req = factory.post("/admin/pages/1/publish/")
        req.session = {}
        req.user = user or MagicMock()
        req._messages = MagicMock()
        return req

    @override_settings(FACEBOOK_APP_ID="app-id", FACEBOOK_PAGE_ID="123456")
    @patch("msl_news.facebook.get_stored_token", return_value=None)
    def test_intercepts_news_page_publish_when_no_token(self, _mock_token):
        from msl_news.wagtail_hooks import check_facebook_token_before_publish
        from msl_news.models import NewsPage

        page = MagicMock()
        page.specific_class = NewsPage
        page.id = 1
        req = self._make_request()

        result = check_facebook_token_before_publish(req, page)
        self.assertIsNotNone(result)
        self.assertEqual(result.status_code, 302)

    @override_settings(FACEBOOK_APP_ID="app-id", FACEBOOK_PAGE_ID="123456")
    @patch("msl_news.facebook.get_stored_token", return_value="valid-token")
    def test_allows_publish_when_valid_token_exists(self, _mock_token):
        from msl_news.wagtail_hooks import check_facebook_token_before_publish
        from msl_news.models import NewsPage

        page = MagicMock()
        page.specific_class = NewsPage
        page.id = 1
        req = self._make_request()

        result = check_facebook_token_before_publish(req, page)
        self.assertIsNone(result)

    @override_settings(FACEBOOK_APP_ID="", FACEBOOK_PAGE_ID="")
    def test_allows_publish_when_integration_not_configured(self):
        from msl_news.wagtail_hooks import check_facebook_token_before_publish
        from msl_news.models import NewsPage

        page = MagicMock()
        page.specific_class = NewsPage
        req = self._make_request()

        result = check_facebook_token_before_publish(req, page)
        self.assertIsNone(result)

    @override_settings(FACEBOOK_APP_ID="app-id", FACEBOOK_PAGE_ID="123456")
    def test_ignores_non_news_pages(self):
        from msl_news.wagtail_hooks import check_facebook_token_before_publish
        from msl_news.models import NewsIndexPage

        page = MagicMock()
        page.specific_class = NewsIndexPage
        req = self._make_request()

        result = check_facebook_token_before_publish(req, page)
        self.assertIsNone(result)
