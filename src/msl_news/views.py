import logging
import secrets
from urllib.parse import urlencode

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from django.urls import reverse

from .facebook import exchange_code_for_page_token

logger = logging.getLogger(__name__)

FACEBOOK_OAUTH_DIALOG_URL = "https://www.facebook.com/dialog/oauth"
FACEBOOK_OAUTH_SCOPES = "pages_manage_posts,pages_read_engagement"

_SESSION_STATE_KEY = "facebook_oauth_state"
_SESSION_NEXT_KEY = "facebook_oauth_next"


@login_required
def facebook_oauth_initiate(request):
    """Redirect the authenticated user to Facebook's OAuth authorisation dialog."""
    app_id = getattr(settings, "FACEBOOK_APP_ID", "")
    if not app_id:
        messages.error(request, "Facebook App ID (FACEBOOK_APP_ID) is not configured.")
        return redirect(reverse("wagtailadmin_home"))

    state = secrets.token_urlsafe(32)
    request.session[_SESSION_STATE_KEY] = state

    callback_url = request.build_absolute_uri(reverse("facebook_oauth_callback"))
    params = {
        "client_id": app_id,
        "redirect_uri": callback_url,
        "scope": FACEBOOK_OAUTH_SCOPES,
        "state": state,
        "response_type": "code",
    }
    return redirect(f"{FACEBOOK_OAUTH_DIALOG_URL}?{urlencode(params)}")


@login_required
def facebook_oauth_callback(request):
    """Handle the Facebook OAuth callback, store the page token, and return to admin."""
    # Check for error response from Facebook
    error = request.GET.get("error")
    if error:
        error_description = request.GET.get("error_description", error)
        messages.error(request, f"Facebook authorization failed: {error_description}")
        return redirect(reverse("wagtailadmin_home"))

    code = request.GET.get("code")
    state = request.GET.get("state")
    stored_state = request.session.pop(_SESSION_STATE_KEY, None)

    if not code or not state or state != stored_state:
        messages.error(
            request,
            "Facebook authorization failed: invalid or missing state parameter. Please try again.",
        )
        return redirect(reverse("wagtailadmin_home"))

    callback_url = request.build_absolute_uri(reverse("facebook_oauth_callback"))

    try:
        page_id, _ = exchange_code_for_page_token(code, callback_url)
        messages.success(
            request,
            f"Facebook page (ID: {page_id}) connected successfully. "
            "Please publish your news article again.",
        )
    except Exception as exc:
        logger.error("Facebook OAuth callback error: %s", exc)
        messages.error(request, f"Failed to connect Facebook page: {exc}")

    next_url = request.session.pop(_SESSION_NEXT_KEY, None)
    return redirect(next_url or reverse("wagtailadmin_home"))
