import datetime as dt

from django.contrib import admin, messages
from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.core.mail import send_mail
from django.shortcuts import render, redirect
from django.db import models
from django.db.utils import IntegrityError
from wagtail.fields import RichTextField
from wagtail.models import Page
from wagtail.admin.panels import FieldPanel
from django.db.models import Max
from django.utils import timezone
from django.utils.safestring import mark_safe
from wagtail.models import Site

from msl_about.forms import EnrollForm
from util.models import CategoryChoices


# ---------------------
# --- Wagtail Pages ---
# ---------------------
class AboutMSLPage(Page):
    class Meta:
        verbose_name = "O MSL"
        verbose_name_plural = "O MSL"

class CommonPage(Page):
    body = RichTextField(blank=True)

    content_panels = Page.content_panels + [
        FieldPanel('body'),
    ]

    class Meta:
        verbose_name = "Obecná stránka"
        verbose_name_plural = "Obecné stránky"


class RoundsPage(Page):
    def get_context(self, request):
        context = super().get_context(request)

        # Get the selected year from the request, default to current year if not specified
        selected_year = request.GET.get('season_year') or \
            SeasonRounds.objects.aggregate(Max('season_year'))['season_year__max']

        # Filter season_parameters based on the selected year
        season_rounds_filtered = SeasonRounds.objects \
            .filter(season_year=selected_year) \
            .order_by('datetime')

        context.update({
            'season_rounds_filtered': season_rounds_filtered,
            'selected_year': selected_year,
        })
        return context

    class Meta:
        verbose_name = "Ligová kola"
        verbose_name_plural = "Ligová kola"


class PointsAndFinancesPage(Page):
    def get_context(self, request):
        context = super().get_context(request)

        # Get the selected year from the request, default to current year if not specified
        selected_year = request.GET.get('season_year') or \
            SeasonParameters.objects.aggregate(Max('season_year'))['season_year__max']

        # Filter season_parameters based on the selected year
        filtered_season_parameters_men = SeasonParameters.objects \
            .filter(season_year=selected_year, category=CategoryChoices.MUZI) \
            .order_by('-points')
        filtered_season_parameters_women = SeasonParameters.objects \
            .filter(season_year=selected_year, category=CategoryChoices.ZENY) \
            .order_by('-points')
        filtered_season_parameters_35 = SeasonParameters.objects \
            .filter(season_year=selected_year, category=CategoryChoices.VETERANI) \
            .order_by('-points')
        penalizations = SeasonParametersPenalizations.objects \
            .filter(season_year=selected_year) \

        context.update({
            'filtered_season_parameters_men': filtered_season_parameters_men,
            'filtered_season_parameters_women': filtered_season_parameters_women,
            'filtered_season_parameters_35': filtered_season_parameters_35,
            'penalizations': penalizations,
            'selected_year': selected_year,
        })
        return context

    class Meta:
        verbose_name = "Body a fin. ohodnocení"
        verbose_name_plural = "Body a fin. ohodnocení"


class EnrollmentsPage(Page):
    def get_context(self, request):
        context = super().get_context(request)

        category = request.GET.get('category') or CategoryChoices.MUZI

        # Start with base queryset filtered by season_year
        enrollments_filtered = SeasonTeams.objects.filter(season_year=timezone.now().year)
        
        # Apply category filter if provided
        if category:
            enrollments_filtered = enrollments_filtered.filter(team__category=category)
        
        # Apply ordering
        enrollments_filtered = enrollments_filtered.order_by('date_registration')

        context.update({
            'enrollments_filtered': enrollments_filtered,
        })
        return context

    class Meta:
        verbose_name = "Přihlášky"
        verbose_name_plural = "Přihlášky"

class EnrollPage(Page):
    year = models.IntegerField(
        verbose_name="Ročník",
        help_text="Ročník, do kterého se tým přihlašuje.",
        default=2025,
    )
    admin_email = models.EmailField(
        verbose_name="E-mail",
        help_text="E-mail, na který budou zaslány informace o přihlášení.",
        null=True,
    )

    content_panels = Page.content_panels + [
        FieldPanel('year'),
        FieldPanel('admin_email'),
    ]

    def serve(self, request):
        if request.method == 'POST':
            enroll_form = EnrollForm(request.POST)
            if enroll_form.is_valid():
                try:
                    team_name = enroll_form.cleaned_data['new_team']
                    team_category = enroll_form.cleaned_data['category']
                    team_representative = enroll_form.cleaned_data['team_representative']
                    team_representative_email = enroll_form.cleaned_data['team_representative_email']
                    
                    new_team = Team.objects.create(
                        name=team_name,
                        category=team_category,
                    )
                    SeasonTeams.objects.create(
                        season_year=self.year,
                        team=new_team,
                        team_representative=team_representative,
                        team_representative_email=team_representative_email,
                        date_registration=dt.date.today(),
                    )

                    send_mail(
                        f"Nová přihláška do MSL {self.year}",
                        f"Název družstva: {team_name}.\n"
                        f"Kategorie: {team_category}\n"
                        f"Jméno a příjmení zástupce týmu: {team_representative}\n"
                        f"Kontakt: {team_representative_email}",
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=[team_representative_email, self.admin_email],
                        fail_silently=False,
                    )

                    # Get the site for URL generation
                    site = Site.find_for_request(request)
                    home_url = site.root_page.url if site else '/'
                    
                    # Create message with a link to the enrollments section
                    success_message = (
                        f'Tým <b>{new_team.name}</b> byl úspěšně přihlášen do MSL! '
                        f'Na e-mail <b>{team_representative_email}</b> byly zaslány souhrné informace o přihlášení. '
                        f'Tým bude schválen zástupcem rady MSL a zaplacení přihlášky bude potvrzeno. '
                        f'Viz <a href="{home_url}#enrollments">seznam přihlášených týmů</a> na domovské stránce.'
                    )
                    messages.success(request, mark_safe(success_message))
                except IntegrityError as e:
                    if 'UNIQUE constraint failed' in str(e):
                        messages.error(request, f'Tým s názvem "{team_name}" v této kategorii již existuje.')
                    else:
                        messages.error(request, f'Nastala chyba při přihlašování týmu: {str(e)}')
                except Exception as e:
                    # Handle any other errors
                    messages.error(request, f'Nastala chyba při přihlašování týmu: {str(e)}')

                return redirect(self.url)
        else:
            enroll_form = EnrollForm()

        return render(request, 'msl_about/enroll_page.html', {
            'page': self,
            'enroll_form': enroll_form,
        })


# --------------------------------
# --- DB models for Admin view ---
# --------------------------------
class TeamManager(models.Manager):
    def get_by_natural_key(self, name, district, category):
        return self.get(name=name, district=district, category=category)


class Team(models.Model):
    name = models.CharField('Název týmu', max_length=50, blank=False)
    district = models.CharField('Okres', max_length=2, blank=False, default='*')
    category = models.CharField(
        'Kategorie',
        max_length=50,
        blank=False,
        choices=CategoryChoices.choices,
        default=CategoryChoices.MUZI
    )
    confirmed = models.BooleanField('Schváleno', default=False)

    objects = TeamManager()

    class Meta:
        verbose_name = "Tým"
        verbose_name_plural = "Týmy"
        constraints = [
            models.UniqueConstraint(
                fields=['name', 'district', 'category'],
                name='unique_team',
            )
        ]

    @property
    @admin.display(description='Kategorie')
    def team_category(self):
        """Returns the category of the team."""
        return self.get_category_display()

    def __str__(self):
        return f'{self.name} [{self.district}] - {self.team_category}'


class SeasonTeams(models.Model):
    
    season_year = models.IntegerField(
        'Sezóna (rok)',
        blank=False,
        validators=[MinValueValidator(2000), MaxValueValidator(2100)],
    )
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='season_teams', verbose_name='Tým')
    team_representative = models.CharField('Zástupce týmu', max_length=100, null=True)
    team_representative_email = models.EmailField('E-mail', null=True)
    date_registration = models.DateField('Datum registrace', blank=True, null=True)
    reg_confirmed = models.BooleanField('Schválení registrace', default=False)
    paid = models.BooleanField('Zaplaceno', default=False)
    # For manual adjustment in case of equal points in one season
    results_priority = models.IntegerField('Priorita výsledků', default=0)

    class Meta:
        verbose_name = "Přihláška týmu"
        verbose_name_plural = "Přihlášky týmů"
        constraints = [
            models.UniqueConstraint(fields=['season_year', 'team'], name='unique_season_teams')
        ]

    def __str__(self):
        return f'Sezóna: {self.season_year}, {self.team}'

    @property
    @admin.display(description='Kategorie')
    def team_category(self):
        """Returns the category of the team."""
        return self.team.get_category_display()


class SeasonParameters(models.Model):
    season_year = models.IntegerField(
        'Sezóna (rok)',
        blank=False,
        validators=[MinValueValidator(2000), MaxValueValidator(2100)],
    )
    category = models.CharField(
        'Kategorie',
        max_length=50,
        blank=False,
        choices=CategoryChoices.choices,
        default=CategoryChoices.MUZI
    )
    ranking_def = models.CharField(
        'Definice umístění',
        max_length=2,
    )
    points = models.IntegerField('Bodové ohodnocení', blank=False)
    finance = models.IntegerField('Finanční ohodnocení', blank=False)

    class Meta:
        verbose_name = "Parametry sezóny"
        verbose_name_plural = "Parametry sezón"
        constraints = [
            models.UniqueConstraint(fields=['season_year', 'category', 'ranking_def'], name='unique_season_parameters')
        ]

    def __str__(self):
        return f'Sezóna: {self.season_year}, Umístění: {self.ranking_def}.'


class SeasonParametersPenalizations(models.Model):
    season_year = models.IntegerField(
        'Sezóna (rok)',
        blank=False,
        null=False,
        validators=[MinValueValidator(2000), MaxValueValidator(2100)],
    )
    category = models.CharField(
        'Kategorie',
        max_length=50,
        blank=False,
        null=False,
        choices=CategoryChoices.choices,
        default=CategoryChoices.MUZI
    )
    competitors_borrowed = models.IntegerField('Půjčení závodníci', blank=False, null=False)
    penalization_points = models.IntegerField('Penalizace bodů', blank=False, null=False)

    class Meta:
        verbose_name = "Penalizace v sezóně"
        verbose_name_plural = "Penalizace v sezónách"
        constraints = [
            models.UniqueConstraint(fields=['season_year', 'category', 'competitors_borrowed'], name='unique_season_penalizations')
        ]

class SeasonRoundsManager(models.Manager):
    def get_by_natural_key(self, season_year, round):
        return self.get(season_year=season_year, round=round)

class SeasonRounds(models.Model):
    season_year = models.IntegerField(
        'Sezóna (rok)',
        blank=False,
        validators=[MinValueValidator(2000), MaxValueValidator(2100)],
    )
    round = models.CharField(
        'Kolo',
        max_length=50,
        blank=False,
    )
    datetime = models.DateTimeField('Datum konání', blank=False)
    date_registration = models.DateField('Datum začátku registrace', blank=False)
    categories = models.CharField('Soutěžní kategorie', max_length=20, blank=False, default='Muži, Ženy')
    results_ready = models.BooleanField('Výsledky uveřejněny', default=False)

    @classmethod
    def get_next_round(cls):
        """
        Returns the next upcoming round based on datetime.
        If no future rounds exist, returns None.
        """
        now = timezone.now()
        try:
            return cls.objects.filter(datetime__gt=now).order_by('datetime').first()
        except cls.DoesNotExist:
            return None
            
    def format_date(self):
        """
        Returns the formatted date of the round for display.
        """
        return self.datetime.strftime("%d.%m.%Y")

    class Meta:
        verbose_name = "Ligová kola"
        verbose_name_plural = "Ligová kola"
        constraints = [
            models.UniqueConstraint(fields=['season_year', 'round'], name='unique_season_rounds')
        ]

    def __str__(self):
        return f'Sezóna: {self.season_year}, Kolo: {self.round}'
