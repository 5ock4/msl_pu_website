# Copilot instructions — MSL PÚ website

Wagtail (Django 6) CMS for the MSL PÚ firesport league. Python 3.13, PDM, SQLite (dev), Bootstrap 5.3.

For project layout, app overview and dev FAQ see [../README.md](../README.md).
For passwordless login internals see [../docs/magic_link_auth.md](../docs/magic_link_auth.md).

## Run / build / test

All commands run from the repo root unless noted. Manage dependencies with `pdm`.

| Task | Command |
|---|---|
| Dev server | VS Code "Run and Debug" → `runserver` (see `.vscode/launch.json`), or `python src/manage.py runserver localhost:8000` |
| Migrations | `python src/manage.py makemigrations` then `python src/manage.py migrate` |
| Tests (whole project) | `cd src && pytest` (uses `DJANGO_SETTINGS_MODULE=msl_pu_website.settings.dev` from `src/pyproject.toml`) |
| Tests (one app) | `cd src && pytest msl_auth/tests.py -v` |
| Recompile custom Bootstrap | `sass src/msl_pu_website/static/scss/custom-bootstrap.scss src/msl_pu_website/static/css/custom-bootstrap.css` — required after any `.scss` edit; the compiled CSS is checked in |
| Reset DB + reseed pages | `python src/manage.py total_reset` then `total_setup` (custom commands in `src/util/management/commands/`) |

## Conventions

- **App layout** — each top-level folder under `src/` is a Wagtail/Django app (`home`, `msl_news`, `msl_about`, `msl_results`, `msl_tips`, `msl_auth`, `util`, `search`). `msl_pu_website/` is the project entry point (settings, base templates, static assets).
- **Settings** — split into `settings/base.py`, `settings/dev.py`, `settings/production.py`. Dev is the default for `manage.py` and pytest.
- **Templates** — live in each app's `templates/<app_name>/`. `msl_pu_website/templates/base.html` is the parent for all pages.
- **Reusable helpers** — put shared code in `src/util/` (e.g. `navigation_tags.py`, `magic_link_auth.py`). Don't duplicate across apps.
- **Branches & commits** — `feature/...`, `fix/...`, `chore/...`; commit messages follow [Conventional Commits](https://www.conventionalcommits.org/).
- **Czech UI strings** — user-facing copy and page-type verbose names are Czech (e.g. "Přihlášení uživatele", "Aktuality", "Výsledky"). Keep that when adding pages.

## Auth (magic links + display name)

`src/msl_auth/` + `src/util/magic_link_auth.py` implement passwordless login via django-sesame with single-use enforcement (`UsedToken`), per-IP/per-email rate limiting, and same-origin referrer policy. Authenticated users are gated by `msl_auth.middleware.RequireDisplayNameMiddleware` until they set a public `UserProfile.display_name`; the Django `username` field stays email-based so `username == 'RadaMSL'` admin checks keep working. **Don't** weaken `SESAME_MAX_AGE`, single-use checks, or the redirect-without-token pattern — see [../docs/magic_link_auth.md](../docs/magic_link_auth.md) for the threat model.

## Deployment

`main` auto-deploys via `.github/workflows/deploy.yml` (rsync to server, `pdm sync --prod`, `migrate`, `update_index`, `collectstatic`, supervisor restart). The deployed DB and `media/` are **not** synced — they live on the server. Never commit `db.sqlite3` changes or files under `src/media/`.

## Gotchas

- `Dockerfile` targets Python 3.8 and `requirements.txt` (legacy from the Wagtail starter). The real deploy uses PDM + Python 3.13 via the GitHub Actions workflow — prefer that over Docker unless you're updating both.
- After a rebase, run `python src/manage.py migrate` even if you didn't touch models (other branches may have added migrations).
- Tests for the round-results Excel preprocessor live in `test/` at the repo root (not under `src/`), and use fixture `.xlsx` files committed alongside them.
- Test renderings of templates that extend `base.html` need `@override_settings(STORAGES=...)` with a non-manifest staticfiles backend, otherwise `ManifestStaticFilesStorage` errors on missing manifest entries (see `SetupUsernameViewTests` in `src/msl_auth/tests.py` for the pattern).
