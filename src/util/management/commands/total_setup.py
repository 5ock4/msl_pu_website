from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    """Sets up initial project data & settings. Also in production!"""

    help = "Sets up initial project data & settings. Also in production!"

    def _set_site(self):
        """Sets the django and wagtail domains.

        Across all environments.
        """
        # TODO: So far not used - find out what to set when deploying to production...

    def setup_production(self):
        """PRODUCTION ONLY STUFF."""
        call_command("create_project_users", verbosity=self.verbosity)

    def setup_development(self):
        """DEVELOPMENT ONLY STUFF."""
        self.setup_production()

    def handle(self, *args, **options):
        """entry point"""
        self.verbosity = options["verbosity"]
        if not settings.DEBUG:
            if self.verbosity > 0:
                self.stdout.write("Setting up production defaults...")
            self.setup_production()
            return

        if self.verbosity > 0:
            self.stdout.write("Setting up sensible development defaults...")
        self.setup_development()