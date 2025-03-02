from wagtail.models import Page

from about_msl.models import Team


class HomePage(Page):
    def get_context(self, request):
        context = super().get_context(request)
        context["teams"] = Team.objects.all()
        return context

