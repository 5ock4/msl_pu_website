from django.conf import settings
from django.db import migrations


def create_missing_profiles(apps, schema_editor):
    User = apps.get_model(*settings.AUTH_USER_MODEL.split("."))
    UserProfile = apps.get_model("msl_auth", "UserProfile")
    existing = set(UserProfile.objects.values_list("user_id", flat=True))
    to_create = [
        UserProfile(user_id=uid)
        for uid in User.objects.exclude(pk__in=existing).values_list("pk", flat=True)
    ]
    UserProfile.objects.bulk_create(to_create)


class Migration(migrations.Migration):

    dependencies = [
        ("msl_auth", "0002_userprofile"),
    ]

    operations = [
        migrations.RunPython(create_missing_profiles, migrations.RunPython.noop),
    ]
