from wagtail.snippets.models import register_snippet
from wagtail.snippets.views.snippets import SnippetViewSet, SnippetViewSetGroup

from .models import Result


class ResultsViewSet(SnippetViewSet):
    model = Result
    icon = "clipboard-list"
    list_display = ["team_excel", "category_excel", "team", "round", "competitors_borrowed", "lp", "pp", "ranking_def", "points"]
    list_filter = {"round": ["exact"], "team__category": ["exact"]}
    list_per_page = 20
    menu_label = "Výsledky"
    menu_order = 201

class ResultsGroup(SnippetViewSetGroup):
    items = (ResultsViewSet,)
    menu_icon = "clipboard-list"
    menu_label = "Výsledky"
    menu_name = "results"
    menu_order = 201

register_snippet(ResultsGroup)