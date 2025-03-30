from django.contrib import admin
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from wagtail.fields import RichTextField
from wagtail.models import Page
from wagtail.admin.panels import FieldPanel
from django.db.models import Max


class CategoryChoices(models.TextChoices):
        MUZI = 'M', 'Muži'
        ZENY = 'Ž', 'Ženy'
        VETERANI = '35+', '35+'

# ---------------------
# --- Wagtail Pages ---
# ---------------------
class AboutMSLPage(Page):
    class Meta:
        verbose_name = "O MSL"
        verbose_name_plural = "O MSL"

class HistoryPage(Page):
    body = RichTextField(blank=True)

    content_panels = Page.content_panels + [
        FieldPanel('body'),
    ]

    class Meta:
        verbose_name = "Historie"
        verbose_name_plural = "Historie"


class RoundsPage(Page):

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
        season_parameters = SeasonParameters.objects.filter(season_year=selected_year).order_by('-points')
        
        context.update({
            'season_parameters': season_parameters,
            'selected_year': selected_year,
        })
        return context

    class Meta:
        verbose_name = "Body a fin. ohodnocení"
        verbose_name_plural = "Body a fin. ohodnocení"

# --------------------------------
# --- DB models for Admin view ---
# --------------------------------
class TeamManager(models.Manager):
    def get_by_natural_key(self, name, district, category):
        return self.get(name=name, district=district, category=category)


class Team(models.Model):
    name = models.CharField('Název týmu', max_length=50, blank=False)
    district = models.CharField('Okres', max_length=2, blank=False, default='XX')
    category = models.CharField(
        'Kategorie',
        max_length=50,
        blank=False,
        choices=CategoryChoices.choices,
        default=CategoryChoices.MUZI
    )

    objects = TeamManager()

    class Meta:
        verbose_name = "Tým"
        verbose_name_plural = "Týmy"
        constraints = [
            models.UniqueConstraint(fields=['name', 'district', 'category'], name='unique_team')
        ]

    def __str__(self):
        return f'{self.name} [{self.district}]'


class SeasonTeams(models.Model):
    
    season_year = models.IntegerField(
        'Sezóna (rok)',
        blank=False,
        validators=[MinValueValidator(2000), MaxValueValidator(2100)],
    )
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='season_teams', verbose_name='Tým')

    class Meta:
        verbose_name = "Tým v sezóně"
        verbose_name_plural = "Týmy v sezónách"
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
    ranking_def = models.CharField(
        'Definice umístění',
        unique=True,
        max_length=2,
    )
    points = models.IntegerField('Bodové ohodnocení', blank=False)
    finance = models.IntegerField('Finanční ohodnocení', blank=False)

    class Meta:
        verbose_name = "Parametry sezóny"
        verbose_name_plural = "Parametry sezón"
        constraints = [
            models.UniqueConstraint(fields=['season_year', 'ranking_def'], name='unique_season_parameters')
        ]

    def __str__(self):
        return f'Sezóna: {self.season_year}, Umístění: {self.ranking_def}.'


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


    class Meta:
        verbose_name = "Ligová kola"
        verbose_name_plural = "Ligová kola"
        constraints = [
            models.UniqueConstraint(fields=['season_year', 'round'], name='unique_season_rounds')
        ]

    def __str__(self):
        return f'Sezóna: {self.season_year}, Kolo: {self.round}'
