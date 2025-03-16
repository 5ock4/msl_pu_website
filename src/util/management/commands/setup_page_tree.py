import json
from pathlib import Path

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.core.files import File
from django.core.management.base import BaseCommand
from wagtail.models import Page, Site
from wagtail.images.models import Image

from about_msl.models import AboutMSLPage, HistoryPage, PointsAndFinancesPage, RoundsPage
import home
from home.models import HomePage
from news.models import NewsIndexPage, NewsPage


APP_DIR = Path(__file__).resolve().parent.parent.parent
FIXTURES_DIR = APP_DIR.joinpath("fixtures")


class Command(BaseCommand):
    """
    this command is used to create the initial wagtail cms page tree
    """

    help = "creates initial wagtail cms page tree"
    requires_system_checks = []

    def _setup(self):
        self._setup_root_page()
        self._setup_news_pages()
        self._setup_about_msl()

    def _setup_root_page(self):
        self.stdout.write("Setting up root page...")
        # Delete the default homepage created by wagtail migrations If migration is run
        # multiple times, it may have already been deleted
        Page.objects.filter(id=2).delete()

        root = Page.get_first_root_node()
        home_page = HomePage(
            title = "Domovská stránka",
            show_in_menus=True,
        )
        root.add_child(instance=home_page)
        # Create a site with the new LanguageRedirectionPage set as the root
        # Note: this is wagtail's Site model, not django's.
        Site.objects.create(
            hostname="msliga.cz",
            root_page=home_page,
            is_default_site=True,
            site_name="MS liga v PÚ",
        )


    def _setup_news_pages(self):
        """Creates the language specific home pages."""
        self.stdout.write("Setting up 'news'...")
        home_page = HomePage.objects.first()
        news_index_page = NewsIndexPage(
            title="Aktuality",
            slug="aktuality",
            show_in_menus=True
        )
        home_page.add_child(instance=news_index_page)
        if settings.DEBUG:
            news_index_page.add_child(
                instance=NewsPage(
                    title="První novinka",
                    author="Adam Strakos",
                    body="Lorem ipsum dolor sit amet, consectetur adipiscing elit.",
                )
            ),
            news_index_page.add_child(
                instance=NewsPage(
                    title="Druhá novinka",
                    author="Adam Strakos",
                    body="Lorem ipsum dolor sit amet, consectetur adipiscing elit.",
                )
            ),
            news_index_page.add_child(
                instance=NewsPage(
                    title="Třetí novinka",
                    author="Adam Strakos",
                    body="Lorem ipsum dolor sit amet, consectetur adipiscing elit.",
                )
            )

    def _setup_about_msl(self):
        self.stdout.write("Setting up 'about_msl'...")
        home_page = HomePage.objects.first()
        about_msl = AboutMSLPage(
            title="O MS lize",
            show_in_menus=True
        )
        home_page.add_child(instance=about_msl)
        about_msl.add_child(
            instance=HistoryPage(
                title="Historie",
                show_in_menus=True
            )
        )
        about_msl.add_child(
            instance=RoundsPage(
                title="Ligová kola",
                show_in_menus=True
            )
        )
        about_msl.add_child(
            instance=PointsAndFinancesPage(
                title="Body a fin. ohodnocení",
                show_in_menus=True
            )
        )

    def handle(self, raise_error=False, *args, **options):
        # Root Page and a default homepage are created by wagtail migrations so check
        # for > 2 here
        verbosity = options["verbosity"]
        checks = [Page.objects.all().count() > 2]
        if any(checks):
            # YOU SHOULD NEVER RUN THIS COMMAND WITHOUT PRIOR DB DUMP
            raise RuntimeError("Pages exists. Aborting.")

        self._setup()
        if verbosity > 0:
            msg = "Page Tree successfully created."
            self.stdout.write(msg)