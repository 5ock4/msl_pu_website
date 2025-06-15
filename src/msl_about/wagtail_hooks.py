from wagtail.snippets.models import register_snippet
from wagtail.snippets.views.snippets import SnippetViewSet, SnippetViewSetGroup

from .models import SeasonParametersPenalizations, Team, SeasonTeams, SeasonParameters, SeasonRounds


class TeamViewSet(SnippetViewSet):
    model = Team
    icon = "cog"
    list_display = ["name", "district", "team_category"]
    list_filter = {"category": ["exact"], "district": ["exact"]}
    list_per_page = 20
    menu_label = "Týmy"
    menu_order = 201


class SeasonTeamsViewSet(SnippetViewSet):
    model = SeasonTeams
    icon = "cog"
    list_display = ["season_year", "team", "team_category", "team_representative", "team_representative_email", "date_registration", "reg_confirmed", "paid"]
    list_filter = {"season_year": ["exact"]}
    list_per_page = 20
    menu_label = "Přihlášky týmů"
    menu_order = 201


class SeasonParametersViewSet(SnippetViewSet):
    model = SeasonParameters
    icon = "cog"
    list_display = ["season_year", "category", "ranking_def", "points", "finance"]
    list_filter = {"season_year": ["exact"], "category": ["exact"], "ranking_def": ["exact"]}
    list_per_page = 20
    menu_label = "Parametry sezón"
    menu_order = 202

class SeasonParametersPenalizationsViewSet(SnippetViewSet):
    model = SeasonParametersPenalizations
    icon = "cog"
    list_display = ["season_year", "category", "competitors_borrowed", "penalization_points"]
    list_filter = {"season_year": ["exact"]}
    list_per_page = 20
    menu_label = "Penalizace v sezónách"
    menu_order = 202

class SeasonRoundsViewSet(SnippetViewSet):
    model = SeasonRounds
    icon = "cog"
    list_display = ["season_year", "round", "datetime", "date_registration", "categories", "results_ready"]
    list_filter = {"season_year": ["exact"]}
    list_per_page = 20
    menu_label = "Ligová kola"
    menu_order = 204


class AboutMSLGroup(SnippetViewSetGroup):
    items = (TeamViewSet, SeasonTeamsViewSet, SeasonParametersViewSet, SeasonParametersPenalizationsViewSet, SeasonRoundsViewSet)
    menu_icon = "cogs"
    menu_label = "Parametry MSL"
    menu_name = "msl_parameters"
    menu_order = 200

register_snippet(AboutMSLGroup)
