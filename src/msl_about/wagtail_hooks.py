from wagtail.snippets.models import register_snippet
from wagtail.snippets.views.snippets import SnippetViewSet, SnippetViewSetGroup

from .models import Team, SeasonTeams, SeasonParameters, SeasonRounds


class TeamViewSet(SnippetViewSet):
    model = Team
    icon = "cog"
    list_display = ["name", "district", "category"]
    list_filter = {"category": ["exact"], "district": ["exact"]}
    list_per_page = 20
    menu_label = "Týmy"
    menu_order = 201


class SeasonTeamsViewSet(SnippetViewSet):
    model = SeasonTeams
    icon = "cog"
    list_display = ["season_year", "team", "team_category"]
    list_filter = {"season_year": ["exact"]}
    list_per_page = 20
    menu_label = "Týmy v sezónách"
    menu_order = 201


class SeasonParametersViewSet(SnippetViewSet):
    model = SeasonParameters
    icon = "cog"
    list_display = ["season_year", "ranking_def", "points", "finance"]
    list_filter = {"season_year": ["exact"], "ranking_def": ["exact"]}
    list_per_page = 20
    menu_label = "Parametry sezón"
    menu_order = 202


class SeasonRoundsViewSet(SnippetViewSet):
    model = SeasonRounds
    icon = "cog"
    list_display = ["season_year", "round", "datetime", "date_registration", "categories", "results_ready"]
    list_filter = {"season_year": ["exact"]}
    list_per_page = 20
    menu_label = "Ligová kola"
    menu_order = 203


class AboutMSLGroup(SnippetViewSetGroup):
    items = (TeamViewSet, SeasonTeamsViewSet, SeasonParametersViewSet, SeasonRoundsViewSet)
    menu_icon = "cog"
    menu_label = "Parametry MSL"
    menu_name = "msl_parameters"
    menu_order = 200

register_snippet(AboutMSLGroup)
