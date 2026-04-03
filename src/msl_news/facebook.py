import logging
from datetime import datetime

import requests
from django.conf import settings
from django.utils import timezone
from django.utils.html import strip_tags

logger = logging.getLogger(__name__)

GRAPH_API_URL = "https://graph.facebook.com/v18.0/{page_id}/feed"
OAUTH_TOKEN_URL = "https://graph.facebook.com/v18.0/oauth/access_token"
ME_ACCOUNTS_URL = "https://graph.facebook.com/v18.0/me/accounts"
FACEBOOK_MAX_MESSAGE_LENGTH = 63206


def get_stored_token(page_id):
    """Return the stored page access token for *page_id* if it is still valid, else None."""
    from .models import FacebookToken

    try:
        token = FacebookToken.objects.get(page_id=page_id)
        if token.is_valid():
            return token.page_access_token
        return None  # expired
    except FacebookToken.DoesNotExist:
        return None


def exchange_code_for_page_token(code, redirect_uri):
    """Exchange an OAuth authorisation code for a Page access token.

    Performs two Graph API calls:
      1. Exchange ``code`` for a short-lived user access token.
      2. Call ``/me/accounts`` to obtain the Page token for the page
         specified by the ``FACEBOOK_PAGE_ID`` setting.

    The token is persisted in the ``FacebookToken`` table.

    Returns ``(page_id, page_access_token)`` or raises an exception on failure.
    """
    app_id = getattr(settings, "FACEBOOK_APP_ID", "")
    app_secret = getattr(settings, "FACEBOOK_APP_SECRET", "")
    configured_page_id = getattr(settings, "FACEBOOK_PAGE_ID", "")

    # Step 1: Exchange code → user access token
    token_resp = requests.get(
        OAUTH_TOKEN_URL,
        params={
            "client_id": app_id,
            "client_secret": app_secret,
            "redirect_uri": redirect_uri,
            "code": code,
        },
        timeout=10,
    )
    token_resp.raise_for_status()
    user_token = token_resp.json().get("access_token")
    if not user_token:
        raise ValueError("No access_token in Facebook token exchange response")

    # Step 2: GET /me/accounts → page tokens
    accounts_resp = requests.get(
        ME_ACCOUNTS_URL,
        params={"access_token": user_token},
        timeout=10,
    )
    accounts_resp.raise_for_status()
    pages = accounts_resp.json().get("data", [])

    # Find the configured page (or fall back to the first page if no ID is set)
    target_page = None
    for p in pages:
        if p.get("id") == configured_page_id:
            target_page = p
            break

    if target_page is None and not configured_page_id and pages:
        target_page = pages[0]

    if target_page is None:
        available = [p.get("id") for p in pages]
        raise ValueError(
            f"Page with ID '{configured_page_id}' not found in your Facebook accounts. "
            f"Available page IDs: {available}"
        )

    page_id = target_page["id"]
    page_token = target_page["access_token"]

    # Page tokens typically never expire (expires_at == 0 or absent)
    raw_expires = target_page.get("expires_at", 0)
    expires_at = datetime.fromtimestamp(raw_expires, tz=timezone.utc) if raw_expires else None

    # Step 3: Persist the token
    from .models import FacebookToken

    FacebookToken.objects.update_or_create(
        page_id=page_id,
        defaults={
            "page_access_token": page_token,
            "expires_at": expires_at,
        },
    )

    logger.info("Stored Facebook Page token for page ID '%s'.", page_id)
    return page_id, page_token


def post_news_to_facebook(page):
    """Post a NewsPage article to the configured Facebook page."""
    page_id = getattr(settings, "FACEBOOK_PAGE_ID", "")
    app_id = getattr(settings, "FACEBOOK_APP_ID", "")

    if not page_id or not app_id:
        logger.debug("Facebook integration not configured; skipping post for '%s'.", page.title)
        return

    access_token = get_stored_token(page_id)
    if not access_token:
        logger.warning(
            "No valid Facebook token for page '%s'; skipping post for article '%s'. "
            "Re-authenticate via the Facebook OAuth flow.",
            page_id,
            page.title,
        )
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
