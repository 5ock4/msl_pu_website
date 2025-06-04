from django.db import models

# Create your models here.
from wagtail.models import Page
from django.db.models import Max

from msl_about.models import SeasonParameters, SeasonRounds, Team
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

        # Get all rounds for the selected year
        rounds = SeasonRounds.objects.filter(season_year=selected_year).order_by('datetime')

        def get_teams_with_results(category):
            """Helper function to get teams with results for a specific category"""
            # Get all teams that have results in the selected year for this category
            teams = Result.objects.filter(
                round__season_year=selected_year, 
                team__category=category
            ).values_list('team', flat=True).distinct()

            # Prepare data structure for results
            teams_with_results = []
            for team_id in teams:
                team = Team.objects.get(id=team_id)
                team_results = Result.objects.filter(
                    team=team, 
                    round__season_year=selected_year, 
                    team__category=category
                ).select_related('round')

                # Create a dictionary to map round to points
                round_points_dict = {result.round.id: result.points for result in team_results}

                # Create ordered list of points for each round
                round_points = [round_points_dict.get(round.id) for round in rounds]
                total_points = sum(points for points in round_points if points is not None)

                teams_with_results.append({
                    'team': team,
                    'round_points': round_points,
                    'total_points': total_points
                })

            # Sort by total points descending
            teams_with_results.sort(key=lambda x: x['total_points'], reverse=True)
            return teams_with_results

        # Get results for all categories
        teams_with_results_men = get_teams_with_results(CategoryChoices.MUZI)
        teams_with_results_women = get_teams_with_results(CategoryChoices.ZENY)
        teams_with_results_35 = get_teams_with_results(CategoryChoices.VETERANI)

        context.update({
            'rounds': rounds,
            'selected_year': selected_year,
            'rounds': rounds,
            'teams_with_results_men': teams_with_results_men,
            'teams_with_results_women': teams_with_results_women,
            'teams_with_results_35': teams_with_results_35,
        })

        return context


class Result(models.Model):
    """
    A model that stores the results of a competition.
    """

    team_excel = models.CharField(
        'Tým z Excelu',
        max_length=100,
        blank=True,
        null=True,
    )
    team = models.ForeignKey(
        'msl_about.Team',
        on_delete=models.CASCADE,
        related_name='result_team',
        verbose_name='Tým',
        blank=True,
        null=True,
    )
    category_excel = models.CharField(
        'Kategorie',
        max_length=50,
        choices=CategoryChoices.choices,
        default=CategoryChoices.MUZI,
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
    ranking_def = models.CharField(
        'Definice umístění',
        max_length=2,
        default='U',
    )
    points = models.IntegerField('Body', default=0)

    class Meta:
        verbose_name = "Výsledek"
        verbose_name_plural = "Výsledky"
