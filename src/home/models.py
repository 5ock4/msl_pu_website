from django.db.models import Q
from django.utils import timezone
from wagtail.models import Page

from msl_about.models import SeasonRounds, Team


class HomePage(Page):
    def get_context(self, request):
        context = super().get_context(request)
        context["teams"] = Team.objects.all()
        context["next_round"] = SeasonRounds.get_next_round()
        current_year = timezone.now().year
        context["rounds_with_pdfs"] = (
            SeasonRounds.objects
            .filter(season_year=current_year)
            .filter(Q(pozvanka_pdf__isnull=False) | Q(startovka_text__gt=''))
            .order_by('datetime')
        )
        return context
