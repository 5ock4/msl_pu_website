from django.db import models
from django.db.models import Max, Sum

# Create your models here.
from wagtail.models import Page
from django.db.models import Max

from msl_about.models import SeasonParameters, SeasonRounds, Team
from util.models import FREE_BORROWED_COMPETITORS_IN_SEASON, CategoryChoices, RankingDefChoices


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
        SELECTED_YEAR = request.GET.get('season_year') or \
            SeasonParameters.objects.aggregate(Max('season_year'))['season_year__max']
        SELECTED_CATEGORY = request.GET.get('category')
        # Controls whether we display total points or total prize money
        metric_param = request.GET.get('metric')

        user = request.user
        is_admin = user.is_authenticated and (user.is_staff or user.is_superuser or user.username == 'RadaMSL')
        RESULTS_METRIC = 'prize_money' if metric_param == 'prize_money' else 'points'

        # Get all rounds for the selected year
        rounds = SeasonRounds.objects.filter(season_year=SELECTED_YEAR).order_by('datetime')

        def get_teams_with_results(category):
            """Helper function to get teams with results for a specific category"""
             # Get all teams that have results in the selected year for this category
            results_gate = (
                models.Q(round__results_excel__isnull=False) | models.Q(round__results_ready=True)
                if is_admin else models.Q(round__results_ready=True)
            )
            teams = Result.objects.filter(
                results_gate,
                round__season_year=SELECTED_YEAR,
                team__category=category
            ).values_list('team', flat=True).distinct()

            # Prepare data structure for results
            teams_with_results = []
            for team_id in teams:
                team = Team.objects.get(id=team_id)
                # Get results_priority from SeasonTeams for the selected year
                season_team = team.season_teams.filter(season_year=SELECTED_YEAR).first()
                results_priority = season_team.results_priority if season_team else 0

                team_results = Result.objects.filter(
                    team=team, 
                    round__season_year=SELECTED_YEAR, 
                    team__category=category
                ).select_related('round').order_by('round__datetime')

                # Create a dictionary for quick lookup
                results_by_round = {result.round.id: result for result in team_results}

                # Create ordered list of points for each round
                team_round_stats = []
                for round in rounds:
                    result = results_by_round.get(round.id)
                    team_round_stats.append({
                        'points': result.points if result else None,
                        'lp': result.lp if result else None,
                        'pp': result.pp if result else None,
                        'competitors_borrowed': result.competitors_borrowed if result else None,
                        'ranking_def': result.ranking_def if result else None,
                        'prize_money': result.prize_money if result else None,
                    })

                total_points = sum(s['points'] for s in team_round_stats if s['points'] is not None)
                total_prize_money = sum(s['prize_money'] for s in team_round_stats if s['prize_money'] is not None)

                if RESULTS_METRIC == 'prize_money':
                    display_total = total_prize_money
                else:
                    display_total = total_points

                teams_with_results.append({
                    'team': team,
                    'team_round_stats': team_round_stats,
                    'total_points': total_points,
                    'display_total': display_total,
                    'results_priority': results_priority,
                })

            # -------
            # SORTING
            # -------
            teams_with_results.sort(key=lambda x: (x['total_points'], x['results_priority']), reverse=True)
            return teams_with_results

        # Get results for all categories
        teams_with_results = get_teams_with_results(SELECTED_CATEGORY or CategoryChoices.MUZI)

        display_total_label = 'Body' if RESULTS_METRIC == 'points' else 'Prize Money'

        context.update({
            'rounds': rounds,
            'selected_year': SELECTED_YEAR,
            'rounds': rounds,
            'teams_with_results': teams_with_results,
            'display_total_metric': RESULTS_METRIC,
            'display_total_label': display_total_label,
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
    # Calculated fields by RoundResultsPreprocessor
    ranking_def = models.CharField(
        'Definice umístění',
        max_length=2,
        choices=RankingDefChoices.choices,
        default=RankingDefChoices.U.value,
        help_text='Automaticky vypočtené pole pro definici umístění (např. N, D, U) ale také integer pořadí ve stringu!'
    )
    penalty_points = models.IntegerField('Penalizace', default=0, help_text='Automaticky vypočtené penalizace za půjčené závodníky, neúčast nebo diskvalifikaci pro dané kolo a kategorii.')
    points = models.IntegerField('Body po penalizaci', default=0, help_text='Automaticky vypočtené body po penalizacich.')
    prize_money = models.IntegerField('Finance', default=0, help_text='Automaticky vypočtené prize money pro dané kolo a kategorii.')

    class Meta:
        verbose_name = "Výsledek"
        verbose_name_plural = "Výsledky"

    @staticmethod
    def penalties_allowed(team: Team, round: SeasonRounds) -> bool:
        """Check if penalties are allowed for the given team and round based on season parameters"""
        total_borrowed = (
            Result.objects
            .filter(team=team, round__season_year=round.season_year)
            .exclude(round=round)
            .aggregate(total=Sum('competitors_borrowed'))['total'] or 0
        )
        return total_borrowed >= FREE_BORROWED_COMPETITORS_IN_SEASON
