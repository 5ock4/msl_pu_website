from pathlib import Path

from django.conf import settings
from django.core.files import File
from django.core.management.base import BaseCommand
from wagtail.models import Page, Site
from wagtail.documents.models import Document

from msl_about.models import AboutMSLPage, CommonPage, EnrollmentsPage, PointsAndFinancesPage, RoundsPage
import home
from home.models import HomePage
from msl_about.models import EnrollPage
from msl_news.models import NewsIndexPage, NewsPage
from util.models import GDPRPage


APP_DIR = Path(__file__).resolve().parent.parent.parent
FIXTURES_DIR = APP_DIR.joinpath("fixtures")
DOCUMENTS_DIR = APP_DIR.joinpath("sample_documents")  # Path to sample documents


class Command(BaseCommand):
    """
    this command is used to create the initial wagtail cms page tree
    """

    help = "creates initial wagtail cms page tree"
    requires_system_checks = []

    def _setup(self):
        self._setup_root_page()
        self._setup_msl_news()
        self._setup_msl_about()
        self._setup_gdpr_page()
        self._setup_documents()

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


    def _setup_msl_news(self):
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
                    title="Nové stránky MS ligy",
                    author="Adam Strakoš",
                    body="<p>Vítejte na nových stránkách MS ligy v PÚ.</p> <p>Po nějakou dobu poběží nové stránky paralelně se "
                         "starými, ale nové věci budou přidávány pouze tady na nový web. " \
                         "Historické výsledky a jiná data budou postupně přeneseny na nové stránky. " \
                         "Zároveň zde chybí stále asi nejdůležitější funkcionalita, a to \"výsledky\" a \"tipování\" - ta bude " \
                         "dořešena během tohoto měsíce před prvním kolem MSL v Brušperku. " \
                         "Také možná dojde k drobným designovým úpravám.</p> <p>Pokud by někdo narazil na nějakou nefunkčnost " \
                         "nebo nesrovnalost, dejte mi prosím vědět na mail nebo přes soc. sítě (viz patička webu). "
                         "Jinak prosím o strpení - dělám to ve volném čase a zadarmo.</p> <p>Díky za pochopení a " \
                         "možná se uvidíme na zahajovacím kole v Brušperku. 😋</p>"
                )
            ),
            # news_index_page.add_child(
            #     instance=NewsPage(
            #         title="Druhá novinka",
            #         author="Adam Strakos",
            #         body="Lorem ipsum dolor sit amet, consectetur adipiscing elit.",
            #     )
            # ),
            # news_index_page.add_child(
            #     instance=NewsPage(
            #         title="Třetí novinka",
            #         author="Adam Strakos",
            #         body="Lorem ipsum dolor sit amet, consectetur adipiscing elit.",
            #     )
            # )

    def _setup_msl_about(self):
        self.stdout.write("Setting up 'msl_about'...")
        home_page = HomePage.objects.first()
        msl_about = AboutMSLPage(
            title="O MS lize",
            show_in_menus=True
        )
        home_page.add_child(instance=msl_about)
        msl_about.add_child(
            instance=CommonPage(
                title="Dokumenty",
                show_in_menus=True
            )
        )
        msl_about.add_child(
            instance=RoundsPage(
                title="Ligová kola",
                show_in_menus=True
            )
        )
        msl_about.add_child(
            instance=PointsAndFinancesPage(
                title="Body a fin. ohodnocení",
                show_in_menus=True
            )
        )
        msl_about.add_child(
            instance=EnrollmentsPage(
                title="Přihlášené týmy do MSL 2025",
                show_in_menus=False
            )
        )
        enroll_page = EnrollPage(
            title="Přihláška do MSL 2025",
            year=2025,
            admin_email="rada.msl@seznam.cz",
            slug="prihlaska-do-ms-ligy",
            show_in_menus=True
        )
        home_page.add_child(instance=enroll_page)

    def _setup_gdpr_page(self):
        self.stdout.write("Setting up 'gdpr_page'...")
        home_page = HomePage.objects.first()
        gdpr_page = GDPRPage(
            title="Informace o zpracování osobních údajů (GDPR)",
            slug="gdpr",
            show_in_menus=False,
            body="""
                <h2>I. Základní ustanovení</h2>
                <p>Správcem osobních údajů podle čl. 4 bod 7 nařízení Evropského parlamentu a Rady (EU) 2016/679 o ochraně fyzických osob v souvislosti se zpracováním osobních údajů a o volném pohybu těchto údajů (dále jen: „GDPR") je MORAVSKOSLEZSKÁ LIGA v požárním útoku !, spolek se sídlem Lubno 303, 73911 Frýdlant nad Ostravicí (dále jen: „správce").</p>
                <p>Kontaktní údaje správce jsou<br>
                Radomír Viej<br>
                email: rawio@seznam.cz</p>
                <p>Osobními údaji se rozumí veškeré informace o identifikované nebo identifikovatelné fyzické osobě; identifikovatelnou fyzickou osobou je fyzická osoba, kterou lze přímo či nepřímo identifikovat, zejména odkazem na určitý identifikátor, například jméno, identifikační číslo, lokační údaje, síťový identifikátor nebo na jeden či více zvláštních prvků fyzické, fyziologické, genetické, psychické, ekonomické, kulturní nebo společenské identity této fyzické osoby.</p>
                <p>Správce nejmenoval pověřence pro ochranu osobních údajů.</p>

                <h2>II. Zdroje a kategorie zpracovávaných osobních údajů</h2>
                <p>Správce zpracovává osobní údaje, které jste mu poskytl/a nebo osobní údaje, které správce získal na základě registrace na webu či vyplňování přihlášek.</p>
                <p>Správce zpracovává Vaše identifikační a kontaktní údaje a údaje nezbytné pro plnění smlouvy.</p>

                <h2>III. Zákonný důvod a účel zpracování osobních údajů</h2>
                <p>Zákonným důvodem zpracování osobních údajů je</p>
                <ul>
                <li>plnění smlouvy mezi Vámi a správcem podle čl. 6 odst. 1 písm. b) GDPR,</li>
                <li>oprávněný zájem správce na poskytování přímého marketingu (zejména pro zasílání obchodních sdělení a newsletterů) podle čl. 6 odst. 1 písm. f) GDPR,</li>
                <li>Váš souhlas se zpracováním pro účely poskytování přímého marketingu (zejména pro zasílání obchodních sdělení a newsletterů) podle čl. 6 odst. 1 písm. a) GDPR ve spojení s § 7 odst. 2 zákona č. 480/2004 Sb., o některých službách informační společnosti v případě, že nedošlo k registraci nebo vyplnění přihlášky.</li>
                </ul>
                <p>Účelem zpracování osobních údajů je</p>
                <ul>
                <li>vyřízení Vaší přihlášky a výkon práv a povinností vyplývajících ze vztahu mezi Vámi a správcem; při vyplnění přihlášky jsou vyžadovány osobní údaje, které jsou nutné pro úspěšné vyřízení (jméno a adresa, kontakt), poskytnutí osobních údajů je nutným požadavkem pro registraci do ligy,</li>
                <li>zasílání obchodních sdělení a činění dalších marketingových aktivit.</li>
                </ul>
                <p>Ze strany správce nedochází k automatickému individuálnímu rozhodování ve smyslu čl. 22 GDPR. S takovým zpracováním jste poskytl/a svůj výslovný souhlas.</p>

                <h2>IV. Doba uchovávání údajů</h2>
                <p>Správce uchovává osobní údaje</p>
                <ul>
                <li>po dobu nezbytnou k výkonu práv a povinností vyplývajících ze vztahu mezi Vámi a správcem a uplatňování nároků z těchto smluvních vztahů (po dobu 15 let od ukončení smluvního vztahu).</li>
                <li>po dobu, než je odvolán souhlas se zpracováním osobních údajů pro účely marketingu, nejdéle 15 let, jsou-li osobní údaje zpracovávány na základě souhlasu.</li>
                </ul>
                <p>Po uplynutí doby uchovávání osobních údajů správce osobní údaje vymaže.</p>

                <h2>V. Příjemci osobních údajů (subdodavatelé správce)</h2>
                <p>Příjemci osobních údajů jsou osoby</p>
                <ul>
                <li>podílející se na správě ligy a její organizaci,</li>
                <li>zajišťující provozování webu ligy,</li>
                <li>zajišťující marketingové služby.</li>
                </ul>
                <p>Správce má v úmyslu předat osobní údaje do třetí země (do země mimo EU) nebo mezinárodní organizaci. Příjemci osobních údajů ve třetích zemích jsou poskytovatelé mailingových služeb.</p>
            """
        )
        home_page.add_child(instance=gdpr_page)

    def _setup_documents(self):
        """Adds sample documents to the Documents page."""
        self.stdout.write("Setting up documents...")

        # Find the Documents page
        documents_page = CommonPage.objects.filter(title="Dokumenty").first()

        if not documents_page:
            self.stdout.write(self.style.WARNING("Documents page not found, skipping document attachment"))
            return

        # Check if the documents directory exists
        if not DOCUMENTS_DIR.exists():
            DOCUMENTS_DIR.mkdir(parents=True)
            self.stdout.write(self.style.WARNING(f"Created documents directory at {DOCUMENTS_DIR}"))
            return

        # Get all files from the documents directory
        document_files = [f for f in DOCUMENTS_DIR.iterdir() if f.is_file()]

        # Upload each document
        document_links = []
        for doc_path in document_files:
            with open(doc_path, 'rb') as doc_file:
                # Create the document in Wagtail
                document = Document(
                    title=doc_path.stem.replace('_', ' ').title(),
                    file=File(doc_file, name=doc_path.name)
                )
                document.save()

                # Create a rich text link to the document
                document_links.append(f'<li><a href="{document.file.url}">{document.title}</a></li>')

                self.stdout.write(f"Added document: {document.title}")

        # If the page has a body field, update it with links to documents
        # if hasattr(documents_page, 'body'):
        #     documents_page.body = f"""
        #     <h2>Sezóna 2025</h2>
        #     <ul>
        #     {''.join(document_links)}
        #     </ul>
        #     """
        #     documents_page.save()

        self.stdout.write(self.style.SUCCESS(f"Added {len(document_files)} documents to the Documents page"))

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
