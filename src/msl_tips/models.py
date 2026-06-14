from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from wagtail.admin.panels import FieldPanel
from wagtail.fields import RichTextField
from wagtail.models import Page

from msl_about.models import SeasonRounds, Team
from util.models import CategoryChoices


class TipsIndexPage(Page):
    """Container page acting as a top-nav dropdown for the tipping competition.

    Children: TipsRoundsPage ("Zadej tipy") + TipsLeaderboardPage ("Průběžné pořadí").
    """

    body = RichTextField(blank=True)

    content_panels = Page.content_panels + [
        FieldPanel("body"),
    ]

    subpage_types = [
        "msl_tips.TipsRoundsPage",
        "msl_tips.TipsLeaderboardPage",
    ]

    class Meta:
        verbose_name = "Tipovačka"
        verbose_name_plural = "Tipovačka"


def _resolve_season(request):
    """Pick season from `?season_year=`, fallback to latest, return (year, all_years)."""
    from .services import available_seasons, latest_tipping_season

    seasons = available_seasons()
    requested = request.GET.get("season_year")
    season_year = None
    if requested:
        try:
            requested_int = int(requested)
            if requested_int in seasons:
                season_year = requested_int
        except ValueError:
            pass
    if season_year is None:
        season_year = latest_tipping_season()
    return season_year, seasons


class TipsRoundsPage(Page):
    """Round cards — per-round entry point for submitting tips."""

    parent_page_types = ["msl_tips.TipsIndexPage"]
    subpage_types: list = []

    class Meta:
        verbose_name = "Zadej tipy"
        verbose_name_plural = "Zadej tipy"

    def get_context(self, request):
        from .services import build_round_cards

        context = super().get_context(request)
        season_year, seasons = _resolve_season(request)
        context.update({
            "season_year": season_year,
            "seasons": seasons,
            "round_cards": build_round_cards(season_year, request.user),
        })
        return context


class TipsLeaderboardPage(Page):
    """Season leaderboard table."""

    parent_page_types = ["msl_tips.TipsIndexPage"]
    subpage_types: list = []

    class Meta:
        verbose_name = "Průběžné pořadí"
        verbose_name_plural = "Průběžné pořadí"

    def get_context(self, request):
        from .services import leaderboard

        context = super().get_context(request)
        season_year, seasons = _resolve_season(request)
        context.update({
            "season_year": season_year,
            "seasons": seasons,
            "leaderboard": leaderboard(season_year) if season_year else [],
        })
        return context


class Tip(models.Model):
    """A single position tip (one of 5) by one user for one (round, category)."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="tips",
        verbose_name="Tipující",
    )
    round = models.ForeignKey(
        SeasonRounds,
        on_delete=models.CASCADE,
        related_name="tips",
        verbose_name="Kolo",
    )
    category = models.CharField(
        "Kategorie",
        max_length=10,
        choices=CategoryChoices.choices,
    )
    position = models.PositiveSmallIntegerField(
        "Pozice",
        validators=[MinValueValidator(1), MaxValueValidator(5)],
    )
    team = models.ForeignKey(
        Team,
        on_delete=models.PROTECT,
        related_name="tipped_for",
        verbose_name="Tým",
    )
    submitted_at = models.DateTimeField("Odesláno", auto_now_add=True)

    class Meta:
        verbose_name = "Tip"
        verbose_name_plural = "Tipy"
        constraints = [
            models.UniqueConstraint(
                fields=["user", "round", "category", "position"],
                name="unique_tip_per_slot",
            ),
            models.UniqueConstraint(
                fields=["user", "round", "category", "team"],
                name="unique_team_per_user_round_category",
            ),
            models.CheckConstraint(
                condition=models.Q(position__gte=1) & models.Q(position__lte=5),
                name="tip_position_between_1_and_5",
            ),
        ]
        ordering = ["round", "user_id", "category", "position"]

    def __str__(self):
        return f"{self.user_id} · {self.round} · {self.category} · #{self.position} · {self.team}"

    @property
    def display_name(self):
        profile = getattr(self.user, "msl_profile", None)
        if profile and profile.display_name:
            return profile.display_name
        return self.user.email
