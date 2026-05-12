# Magic-link authentication (passwordless login)

## Overview

The site supports passwordless "magic link" authentication for frontend users.
Users do **not** need a password — they authenticate by clicking a short-lived,
single-use link delivered by email.

The feature is implemented using **[django-sesame](https://django-sesame.readthedocs.io/)**
together with a thin custom layer for single-use enforcement and rate limiting.

---

## How it works

1. The user visits the **"Přihlášení uživatele"** page (a Wagtail `LoginPage`).
2. They enter their email address and submit the form.
3. The server calls `get_or_create_user(email)` to find (or create) the account,
   generates a signed sesame token via `sesame.utils.get_token(user)`, and sends
   an email containing the magic link.
4. The user clicks the link, which points to `/auth/verify/?sesame=<token>`.
5. The verification view:
   a. checks the token hash against the `UsedToken` table (rejects if already used),
   b. passes the token to `sesame.utils.get_user()` (rejects if expired or tampered),
   c. records the token hash in `UsedToken` (single-use enforcement),
   d. calls `login(request, user)` to establish the Django session,
   e. **immediately redirects** to a clean URL that does not contain the token
      (prevents token leakage via the Referer header).
6. Subsequent requests carry the session cookie — the user is authenticated.
7. The user can log out via the logout button (POST to `/auth/logout/`).

---

## Security mitigations

| Requirement | Implementation |
|---|---|
| **10-minute TTL** | `SESAME_MAX_AGE = 600` in `settings/base.py`; sesame embeds a timestamp and rejects stale tokens. |
| **Single-use tokens** | `UsedToken` model stores the SHA-256 hash of each consumed token. Reuse is rejected before sesame is even consulted. |
| **No raw token in DB** | Only `hash_token(token)` (SHA-256 hex digest) is stored, not the token itself. |
| **No Referer leakage** | `SECURE_REFERRER_POLICY = "same-origin"`; the verification view redirects immediately without rendering a template. |
| **Rate limiting** | `check_rate_limit` / `increment_rate_limit` in `util/magic_link_auth.py` use Django's cache framework to enforce a per-IP **and** per-email limit of 5 requests per 5-minute window. |
| **No user enumeration** | The login form always shows the same success message whether the email exists or not. |
| **Open-redirect prevention** | `is_safe_next_url()` wraps Django's `url_has_allowed_host_and_scheme()`; unsafe `next` values are silently ignored. |
| **CSRF on logout** | The logout endpoint accepts POST only, protected by Django's CSRF middleware. |

---

## Relevant settings

All settings live in `src/msl_pu_website/settings/base.py`:

```python
# Authentication backends (standard + sesame)
AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    "sesame.backends.ModelBackend",
]

# Token TTL: 10 minutes
SESAME_MAX_AGE = 600

# Prevent token leakage via the Referer header
SECURE_REFERRER_POLICY = "same-origin"
```

---

## Relevant apps and files

| Path | Purpose |
|---|---|
| `src/msl_auth/` | Django app containing `LoginPage`, `UsedToken`, views, URLs, template |
| `src/msl_auth/models.py` | `LoginPage` (Wagtail page), `UsedToken` (single-use token registry) |
| `src/msl_auth/views.py` | `serve_login_page`, `verify_magic_link`, `logout_view` |
| `src/msl_auth/urls.py` | `/auth/verify/` and `/auth/logout/` URL patterns |
| `src/msl_auth/templates/msl_auth/login_page.html` | Login page template |
| `src/util/magic_link_auth.py` | All business logic: token generation, email, verification, rate limiting |
| `src/msl_auth/tests.py` | Automated tests |

---

## Email configuration

Magic-link emails are sent via the same email backend used by the rest of the
site (configured in `settings/dev.py` and `settings/production.py`).

- **Development** – emails are printed to the console
  (`EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"`).
- **Production** – emails are sent via SMTP (`smtp.rosti.cz`, port 587, TLS).

The `DEFAULT_FROM_EMAIL` setting controls the sender address.

---

## Setting up the Wagtail page

After deploying, create the login page in Wagtail admin:

1. Open the Wagtail admin (`/admin/`).
2. Navigate to **Pages → Root page** (or wherever you want the page to live).
3. Add a child page of type **"Přihlášení uživatele"**.
4. Set the title, slug (e.g. `prihlaseni`), and enable **Show in menus**.
5. Publish the page.

The page will appear in the site navigation and serve the login form.

---

## Running the tests

```bash
cd src
DJANGO_SETTINGS_MODULE=msl_pu_website.settings.dev \
  python -m pytest msl_auth/tests.py -v
```
