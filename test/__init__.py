import os
import django

os.environ.setdefault(
    "DJANGO_SETTINGS_MODULE",
    "msl_pu_website.settings.dev"
)

django.setup()