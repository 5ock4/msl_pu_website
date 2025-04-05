import os
from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    """DEV ONLY: Dumps the entire DB and sets up everything anew."""

    help = "DEV ONLY: Dumps the entire DB and sets up everything anew."
    requires_system_checks = []

    # Delete sqlite db
    def delete_sqlite_db(self):
        db_path = settings.DATABASES['default']['NAME']
        if os.path.exists(db_path):
            os.remove(db_path)
            self.stdout.write(f"Deleted database at {db_path}")
        else:
            self.stdout.write(f"No database found at {db_path}")

    def handle(self, *args, **options):
        """entry point"""
        verbosity = options["verbosity"]
        if not settings.DEBUG:
            # YOU SHOULD NEVER TRUST THIS COMMAND FOR PRODUCTION USAGE.
            raise RuntimeError("Command can not be run in production.")

        self.delete_sqlite_db()

        call_command("migrate", verbosity=verbosity)
        if verbosity > 0:
            self.stdout.write("Migrations done.")
        call_command("total_setup", verbosity=verbosity)

        # Total setup only creates content when there was a dump created by our
        # ``total_dump`` command.
        if verbosity > 0:
            msg = "Migrations done. Generating content. Time to grab a coffee..."
            self.stdout.write(msg)
        # this is a wagtail specific management command to setup some initial Wagtail pages
        # only needed if you are using Wagtail
        call_command("setup_page_tree", verbosity=verbosity)
        # load fixtures
        call_command("loaddata", "teams.json", verbosity=verbosity)
        call_command("loaddata", "seasonteams.json", verbosity=verbosity)
        call_command("loaddata", "seasonparameters.json", verbosity=verbosity)
        call_command("loaddata", "seasonrounds.json", verbosity=verbosity)