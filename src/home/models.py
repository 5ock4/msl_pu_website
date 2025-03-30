from wagtail.models import Page

from msl_about.models import Team


class HomePage(Page):
    def get_context(self, request):
        context = super().get_context(request)
        context["teams"] = Team.objects.all()
        return context

