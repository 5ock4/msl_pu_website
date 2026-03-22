import logging

import requests
from django.conf import settings
from django.utils.html import strip_tags

logger = logging.getLogger(__name__)

GRAPH_API_URL = "https://graph.facebook.com/v18.0/{page_id}/feed"
FACEBOOK_MAX_MESSAGE_LENGTH = 63206


def post_news_to_facebook(page):
    """Post a NewsPage article to the configured Facebook page."""
    page_id = getattr(settings, "FACEBOOK_PAGE_ID", "")
    access_token = getattr(settings, "FACEBOOK_ACCESS_TOKEN", "")

    if not page_id or not access_token:
        logger.debug("Facebook integration not configured; skipping post for '%s'.", page.title)
        return

    url = GRAPH_API_URL.format(page_id=page_id)
    full_url = page.get_full_url()
    message = f"{page.title}\n\n{strip_tags(page.body)}"
    if len(message) > FACEBOOK_MAX_MESSAGE_LENGTH:
        message = message[:FACEBOOK_MAX_MESSAGE_LENGTH]

    payload = {
        "message": message,
        "link": full_url,
        "access_token": access_token,
    }

    try:
        response = requests.post(url, data=payload, timeout=10)
        response.raise_for_status()
        logger.info("Successfully posted article '%s' to Facebook.", page.title)
    except requests.RequestException as e:
        logger.error("Failed to post article '%s' to Facebook: %s", page.title, e)
