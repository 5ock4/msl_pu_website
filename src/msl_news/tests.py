from unittest.mock import MagicMock, patch

from django.test import TestCase, override_settings


class PostNewsToFacebookTests(TestCase):
    def _make_page(self, title="Test Article", body="<p>Body text</p>", full_url="http://example.com/news/test/"):
        page = MagicMock()
        page.title = title
        page.body = body
        page.get_full_url.return_value = full_url
        return page

    @override_settings(FACEBOOK_PAGE_ID="123456", FACEBOOK_ACCESS_TOKEN="test-token")
    @patch("msl_news.facebook.requests.post")
    def test_posts_to_facebook_when_configured(self, mock_post):
        mock_post.return_value.raise_for_status = MagicMock()

        from msl_news.facebook import post_news_to_facebook

        page = self._make_page()
        post_news_to_facebook(page)

        mock_post.assert_called_once()
        call_kwargs = mock_post.call_args
        self.assertIn("123456", call_kwargs[0][0])
        payload = call_kwargs[1]["data"]
        self.assertIn("Test Article", payload["message"])
        self.assertIn("Body text", payload["message"])
        self.assertEqual(payload["link"], "http://example.com/news/test/")
        self.assertEqual(payload["access_token"], "test-token")

    @override_settings(FACEBOOK_PAGE_ID="", FACEBOOK_ACCESS_TOKEN="")
    @patch("msl_news.facebook.requests.post")
    def test_skips_when_not_configured(self, mock_post):
        from msl_news.facebook import post_news_to_facebook

        page = self._make_page()
        post_news_to_facebook(page)

        mock_post.assert_not_called()

    @override_settings(FACEBOOK_PAGE_ID="123456", FACEBOOK_ACCESS_TOKEN="test-token")
    @patch("msl_news.facebook.requests.post")
    def test_strips_html_from_body(self, mock_post):
        mock_post.return_value.raise_for_status = MagicMock()

        from msl_news.facebook import post_news_to_facebook

        page = self._make_page(body="<p>Hello <strong>world</strong></p>")
        post_news_to_facebook(page)

        payload = mock_post.call_args[1]["data"]
        self.assertNotIn("<p>", payload["message"])
        self.assertNotIn("<strong>", payload["message"])
        self.assertIn("Hello world", payload["message"])

    @override_settings(FACEBOOK_PAGE_ID="123456", FACEBOOK_ACCESS_TOKEN="test-token")
    @patch("msl_news.facebook.requests.post")
    def test_handles_request_error_gracefully(self, mock_post):
        import requests as req

        mock_post.side_effect = req.RequestException("Connection error")

        from msl_news.facebook import post_news_to_facebook

        page = self._make_page()
        # Should not raise
        post_news_to_facebook(page)
