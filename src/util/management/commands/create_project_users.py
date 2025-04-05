from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand


User = get_user_model()
# some random team members generated via https://uinames.com/
USERS = [
    {
        "username": "as",
        "email": "",
        "password": "as",
        "first_name": "Adam",
        "last_name": "Strakos",
    },
]


class Command(BaseCommand):
    """Creates project users.

    In development we simply set ``1234`` as password. In production we create users
    without valid passwords, so we can simply do a password reset procedure.
    """

    help = "Creates project users."
    requires_system_checks = []

    def handle(self, *args, **options):
        verbosity = options["verbosity"]
     
        for user_data in USERS:
            username = user_data.get("username")
            created = False
            created_user = None
            if not User.objects.filter(username=username).exists():
                created_user = User.objects.create_superuser(**user_data)
                created = True
            if verbosity > 0:
                self.stdout.write(
                    f"{username} {"created" if created else "exists"}"
                )
            #  When we run in production, make sure this command doesnt set 1234 as
            #  valid password lol.
            if not settings.DEBUG and created_user:
                # By using unusable password we get superusers which can then reset
                # their password.
                created_user.set_unusable_password()
                created_user.save()
                if verbosity > 0:
                    self.stdout.write("\tProduction run: set invalid password.")
