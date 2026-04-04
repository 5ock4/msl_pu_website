from django.contrib.auth import login, logout as auth_logout
from django.contrib import messages
from django.shortcuts import render, redirect
from django.utils.http import url_has_allowed_host_and_scheme

from .forms import MagicLinkRequestForm
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
                generate_and_send_magic_link(request, user, next_url=next_url or None)
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

    # result is an authenticated User (backend already set by sesame.utils.get_user)
    login(request, result)
    messages.success(request, f"Byli jste přihlášeni jako {result.email}.")

    # Redirect to a clean URL – removes the token from the address bar.
    # next_url is validated with url_has_allowed_host_and_scheme to prevent open redirects.
    if url_has_allowed_host_and_scheme(
        url=next_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return redirect(next_url)
    return _redirect_to_login(request)


def logout_view(request):
    """Log out the current user (POST only for CSRF protection)."""
    if request.method == "POST":
        auth_logout(request)
        messages.success(request, "Byli jste úspěšně odhlášeni.")
    return _redirect_to_login(request)


def _redirect_to_login(request):
    from .models import LoginPage

    login_page = LoginPage.objects.live().first()
    if login_page:
        return redirect(login_page.url)
    return redirect("/")
