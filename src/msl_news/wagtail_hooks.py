import logging

from django.conf import settings
from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse

from wagtail import hooks

logger = logging.getLogger(__name__)

_SESSION_NEXT_KEY = "facebook_oauth_next"


@hooks.register("before_publish_page")
def check_facebook_token_before_publish(request, page):
    """Intercept NewsPage publishing when no valid Facebook token is available.

    If the Facebook integration is configured (FACEBOOK_APP_ID and FACEBOOK_PAGE_ID
    are set) but no valid token is stored in the database, cancel the publish action
    and redirect the user to the Facebook OAuth flow.  After successful authorisation
    the user is directed back to the article's edit page to re-publish.
    """
    from .models import NewsPage
    from .facebook import get_stored_token

    # Only apply to NewsPage
    if page.specific_class is not NewsPage:
        return None

    app_id = getattr(settings, "FACEBOOK_APP_ID", "")
    page_id = getattr(settings, "FACEBOOK_PAGE_ID", "")

    # If the integration is not configured, let the publish proceed normally
    if not app_id or not page_id:
        return None

    # If a valid token already exists, let the publish proceed
    if get_stored_token(page_id):
        return None

    # No valid token — stash the edit URL and redirect to OAuth
    request.session[_SESSION_NEXT_KEY] = reverse(
        "wagtailadmin_pages:edit", args=[page.id]
    )
    messages.warning(
        request,
        "Your article has not been published yet. "
        "Please authorise the app to post on your Facebook page, "
        "then publish the article again.",
    )
    return redirect(reverse("facebook_oauth_initiate"))
