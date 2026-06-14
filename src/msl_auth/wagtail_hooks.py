from wagtail.admin.panels import FieldPanel
from wagtail.snippets.views.snippets import SnippetViewSet

from .models import UserProfile


class UserProfileViewSet(SnippetViewSet):
    model = UserProfile
    icon = "user"
    list_display = ["user", "display_name"]
    search_fields = ["display_name", "user__username", "user__email"]
    list_per_page = 30
    menu_label = "Profily uživatelů"
    menu_order = 210
    panels = [
        FieldPanel("user", read_only=True),
        FieldPanel("display_name", read_only=True),
    ]
