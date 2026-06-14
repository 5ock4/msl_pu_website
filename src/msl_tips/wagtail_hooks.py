from wagtail.snippets.models import register_snippet
from wagtail.snippets.views.snippets import SnippetViewSet, SnippetViewSetGroup

from .models import Tip


class TipsViewSet(SnippetViewSet):
    model = Tip
    icon = "edit"
    list_display = ["display_name", "user", "round", "category", "position", "team", "submitted_at"]
    list_filter = {"round": ["exact"], "category": ["exact"], "position": ["exact"], "user__email": ["exact"]}
    search_fields = ["user__msl_profile__display_name", "user__email", "user__username"]
    list_per_page = 25
    menu_label = "Tipy"
    menu_order = 202


class TipsGroup(SnippetViewSetGroup):
    items = (TipsViewSet,)
    menu_icon = "edit"
    menu_label = "Tipovačka"
    menu_name = "tips"
    menu_order = 202


register_snippet(TipsGroup)
