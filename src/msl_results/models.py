from django.db import models

# Create your models here.
from wagtail.models import Page
from django.db.models import Max

from msl_about.models import SeasonParameters
from util.models import CategoryChoices


class ResultsPage(Page):
    """
    A page that displays the results of a competition.
    """

    class Meta:
        verbose_name = "Výsledky"
        verbose_name_plural = "Výsledky"

    def get_context(self, request):
        context = super().get_context(request)

        # Get the selected year from the request, default to current year if not specified
        selected_year = request.GET.get('season_year') or \
            SeasonParameters.objects.aggregate(Max('season_year'))['season_year__max']

        # Filter results based on the selected year
        filtered_results_men = Result.objects \
            .filter(season_year=selected_year, category=CategoryChoices.MUZI) \
            .order_by('-points')
        filtered_results_women = Result.objects \
            .filter(season_year=selected_year, category=CategoryChoices.ZENY) \
            .order_by('-points')
        filtered_results_35 = Result.objects \
            .filter(season_year=selected_year, category=CategoryChoices.VETERANI) \
            .order_by('-points')

        context.update({
            'selected_year': selected_year,
        })
        return context
    

class Result(models.Model):
    """
    A model that stores the results of a competition.
    """

    team = models.ForeignKey(
        'msl_about.Team',
        on_delete=models.CASCADE,
        related_name='result_team',
        verbose_name='Tým'
    )
    round = models.ForeignKey(
        'msl_about.SeasonRounds',
        on_delete=models.CASCADE,
        related_name='result_team',
        verbose_name='Kolo'
    )
    competitors_borrowed = models.IntegerField('Půjčení závodníci', default=0)
    lp = models.FloatField('LP', default=0.0)
    pp = models.FloatField('PP', default=0.0)
    points = models.IntegerField('Body', default=0)

    class Meta:
        verbose_name = "Výsledek"
        verbose_name_plural = "Výsledky"
