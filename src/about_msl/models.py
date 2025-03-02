from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.contrib import admin

from wagtail.admin.panels import FieldPanel


# Create your models here.
class Team(models.Model):
    class CategoryChoices(models.TextChoices):
        MUZI = 'M', 'Muži'
        ZENY = 'Ž', 'Ženy'
        VETERANI = '35+', '35+'

    name = models.CharField('Název týmu', max_length=50, blank=False)
    district = models.CharField('Okres', max_length=2, blank=False, default='XX')
    category = models.CharField(
        'Kategorie',
        max_length=50,
        blank=False,
        choices=CategoryChoices.choices,
        default=CategoryChoices.MUZI
    )

    class Meta:
        verbose_name = "Tým"
        verbose_name_plural = "Týmy"
        constraints = [
            models.UniqueConstraint(fields=['name', 'district', 'category'], name='unique_team')
        ]

    def __str__(self):
        return f'{self.name} [{self.district}]'


class SeasonTeams(models.Model):
    
    season = models.IntegerField(
        'Sezóna (rok)',
        blank=False,
        validators=[MinValueValidator(2000), MaxValueValidator(2100)],
    )
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='season_teams', verbose_name='Tým')

    class Meta:
        verbose_name = "Tým v sezóně"
        verbose_name_plural = "Týmy v sezónách"
        constraints = [
            models.UniqueConstraint(fields=['season', 'team'], name='unique_season_teams')
        ]

    def __str__(self):
        return f'Sezóna: {self.season}, {self.team}'
    
    @property
    @admin.display(description='Kategorie')
    def team_category(self):
        """Returns the category of the team."""
        return self.team.get_category_display()


class SeasonParameters(models.Model):
    season = models.IntegerField(
        'Sezóna (rok)',
        blank=False,
        validators=[MinValueValidator(2000), MaxValueValidator(2100)],
    )
    ranking = models.IntegerField(
        'Umístění',
        blank=False,
        validators=[
            MinValueValidator(1, 'Umístění musí být alespoň 1'),
            MaxValueValidator(50, 'Umístění nemůže být větší než 50')
        ])
    points = models.IntegerField('Bodové ohodnocení', blank=False)
    finance = models.IntegerField('Finanční ohodnocení', blank=False)

    class Meta:
        verbose_name = "Parametry sezóny"
        verbose_name_plural = "Parametry sezón"
        constraints = [
            models.UniqueConstraint(fields=['season', 'ranking'], name='unique_season_parameters')
        ]

    def __str__(self):
        return f'Sezóna: {self.season}, Umístění: {self.ranking}.'


class SeasonRounds(models.Model):
    season = models.IntegerField(
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
            models.UniqueConstraint(fields=['season', 'round'], name='unique_season_rounds')
        ]

    def __str__(self):
        return f'Sezóna: {self.season}, Kolo: {self.round}'
