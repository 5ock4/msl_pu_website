from django.contrib.auth import login, logout as auth_logout
from django.contrib import messages
from django.shortcuts import render, redirect
from django.utils.http import url_has_allowed_host_and_scheme
from urllib.parse import urlparse

from .forms import DisplayNameForm, MagicLinkRequestForm
from .models import UserProfile
from util.magic_link_auth import (
    get_or_create_user,
    generate_and_send_magic_link,
    verify_and_consume_token,
    check_rate_limit,
    increment_rate_limit,
    is_safe_next_url,
    get_client_ip,
)


def serve_login_page(request, page):
    """Serve the LoginPage – handles the login request form."""
    form = MagicLinkRequestForm()

    if request.method == "POST" and not request.user.is_authenticated:
        form = MagicLinkRequestForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data["email"].lower().strip()
            next_url = request.POST.get("next", "")
            if not is_safe_next_url(request, next_url):
                next_url = ""

            ip = get_client_ip(request)
            if check_rate_limit(ip, email):
                messages.error(
                    request,
                    "Příliš mnoho pokusů o přihlášení. Zkuste to prosím za chvíli.",
                )
            else:
                increment_rate_limit(ip, email)
                user = get_or_create_user(email)
                generate_and_send_magic_link(user, next_url=next_url or None)
                # Always show the same message to avoid user enumeration
                messages.success(
                    request,
                    "Pokud je e-mailová adresa platná, byl na ni odeslán přihlašovací odkaz. "
                    "Odkaz je platný 10 minut a lze jej použít pouze jednou.",
                )

            return redirect(page.url)

    return render(
        request,
        "msl_auth/login_page.html",
        {
            "page": page,
            "form": form,
        },
    )


def verify_magic_link(request):
    """
    Verify a magic-link token from the URL query string, authenticate the user,
    and redirect to a clean URL without the token to prevent referrer leakage.
    """
    token = request.GET.get("sesame", "")
    # next_url is validated below with url_has_allowed_host_and_scheme before use
    next_url = request.GET.get("next", "")

    if not token:
        messages.error(request, "Neplatný přihlašovací odkaz.")
        return _redirect_to_login(request)

    result = verify_and_consume_token(token)

    if result == "expired":
        messages.error(
            request,
            "Přihlašovací odkaz vypršel. Požádejte prosím o nový.",
        )
        return _redirect_to_login(request)

    if result == "used":
        messages.error(
            request,
            "Tento přihlašovací odkaz již byl použit. Požádejte prosím o nový.",
        )
        return _redirect_to_login(request)

    # result is an authenticated User.
    # sesame.utils.get_user() calls authenticate() which sets user.backend;
    # Django's login() uses that attribute when no explicit backend is given.
    login(request, result)
    profile = getattr(result, "msl_profile", None)
    display = (profile.display_name if profile else None) or result.email
    messages.success(request, f"Byli jste přihlášeni jako {display}.")

    # Redirect to a clean URL – removes the token from the address bar.
    # After validating the URL with url_has_allowed_host_and_scheme we extract
    # only the path/query/fragment (discarding any scheme+host), which ensures
    # the redirect can never leave the current site.
    if url_has_allowed_host_and_scheme(
        url=next_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        parsed = urlparse(next_url)
        safe_path = parsed.path
        if parsed.query:
            safe_path += "?" + parsed.query
        if parsed.fragment:
            safe_path += "#" + parsed.fragment
        return redirect(safe_path or "/")
    return _redirect_to_login(request)


def logout_view(request):
    """Log out the current user (POST only for CSRF protection)."""
    if request.method == "POST":
        auth_logout(request)
        messages.success(request, "Byli jste úspěšně odhlášeni.")
    return _redirect_to_login(request)


def setup_username(request):
    """Set or change the public display name.

    The middleware bounces users here when no name is set yet. Users with a
    name can also reach this view directly to update it.
    """
    if not request.user.is_authenticated:
        return _redirect_to_login(request)

    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    next_url = request.GET.get("next") or request.POST.get("next") or ""
    safe_next = next_url if is_safe_next_url(request, next_url) else "/"
    is_edit = bool(profile.display_name)

    if request.method == "POST":
        form = DisplayNameForm(request.POST, user=request.user)
        if form.is_valid():
            profile.display_name = form.cleaned_data["display_name"]
            profile.save(update_fields=["display_name"])
            messages.success(
                request,
                "Uživatelské jméno bylo změněno." if is_edit
                else "Uživatelské jméno bylo uloženo.",
            )
            return redirect(safe_next)
    else:
        form = DisplayNameForm(
            initial={"display_name": profile.display_name or ""},
            user=request.user,
        )

    return render(
        request,
        "msl_auth/setup_username.html",
        {"form": form, "next": next_url, "is_edit": is_edit},
    )


def _redirect_to_login(request):
    from .models import LoginPage

    login_page = LoginPage.objects.live().first()
    if login_page:
        return redirect(login_page.url)
    return redirect("/")
