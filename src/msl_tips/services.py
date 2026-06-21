"""Shared business logic for the tipping competition."""
from __future__ import annotations

from collections import defaultdict
from typing import Iterable

from django.db.models import Case, IntegerField, Max, When
from django.db.models.functions import Greatest
from django.utils import timezone

from msl_about.models import SeasonRounds, SeasonTeams, Team
from msl_results.models import Result
from util.auth import is_msl_admin
from util.models import CategoryChoices

from .models import Tip


# ---------------------------------------------------------------------------
# Categories
# ---------------------------------------------------------------------------

_LABEL_TO_VALUE = {label.lower(): value for value, label in CategoryChoices.choices}


def parse_round_categories(round_obj: SeasonRounds) -> list[str]:
    """Map `SeasonRounds.categories` ('Muži, Ženy, 35+') to CategoryChoices values."""
    if not round_obj.categories:
        return []
    out: list[str] = []
    for raw in round_obj.categories.split(","):
        key = raw.strip().lower()
        if not key:
            continue
        value = _LABEL_TO_VALUE.get(key)
        if value and value not in out:
            out.append(value)
    return out


def category_label(value: str) -> str:
    return CategoryChoices(value).label


# ---------------------------------------------------------------------------
# Round helpers
# ---------------------------------------------------------------------------

def is_tipping_open(round_obj: SeasonRounds) -> bool:
    """True while users may submit new tip rows for this round."""
    if not round_obj.date_registration or not round_obj.datetime:
        return False
    now = timezone.now()
    today = now.date()
    return round_obj.date_registration <= today and now < round_obj.datetime


def is_results_visible(round_obj: SeasonRounds, is_admin: bool = False) -> bool:
    """True once the round has started AND results are published (or user is admin)."""
    if not round_obj.datetime or timezone.now() < round_obj.datetime:
        return False
    return is_admin or bool(round_obj.results_ready)


def season_teams_for(round_obj: SeasonRounds, category: str):
    """Teams registered for the round's season in the given category."""
    team_ids = SeasonTeams.objects.filter(
        season_year=round_obj.season_year,
        team__category=category,
    ).values_list("team_id", flat=True)
    return Team.objects.filter(id__in=team_ids).order_by("name", "district")


def actual_top5(round_obj: SeasonRounds, category: str) -> dict[int, Team]:
    """Use the same ordering as msl_results.round_detail to produce positions 1..5."""
    qs = (
        Result.objects.filter(round=round_obj, team__category=category)
        .annotate(
            max_lp_pp=Greatest("lp", "pp"),
            sort_column=Case(
                When(lp=0, then=9999),
                When(pp=0, then=9999),
                default="max_lp_pp",
                output_field=IntegerField(),
            ),
        )
        .order_by("sort_column")
        .select_related("team")
    )
    out: dict[int, Team] = {}
    for idx, result in enumerate(qs[:5], start=1):
        if result.team_id is None:
            continue
        # Skip rows that effectively didn't finish (both 0)
        if result.lp == 0 and result.pp == 0:
            continue
        out[idx] = result.team
    return out


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------

def _top5_cache(round_obj: SeasonRounds, categories: Iterable[str]) -> dict[str, dict[int, Team]]:
    return {cat: actual_top5(round_obj, cat) for cat in categories}


def score_user_round(user, round_obj: SeasonRounds) -> dict:
    """Score one user for one round. Returns points, total_tips, hits_by_position."""
    categories = parse_round_categories(round_obj)
    top = _top5_cache(round_obj, categories) if is_results_visible(round_obj, is_msl_admin(user)) else {}

    tips = Tip.objects.filter(user=user, round=round_obj)
    total_tips = tips.count()
    points = 0
    hits = {i: 0 for i in range(1, 6)}

    if top:
        for tip in tips:
            correct = top.get(tip.category, {}).get(tip.position)
            if correct and correct.id == tip.team_id:
                points += 1
                hits[tip.position] += 1

    return {
        "points": points,
        "total_tips": total_tips,
        "hits_by_position": hits,
    }


def leaderboard(season_year: int | None, is_admin: bool = False) -> list[dict]:
    """Season leaderboard sorted by points DESC, then total_tips DESC."""
    if not season_year:
        return []

    rounds = list(SeasonRounds.objects.filter(season_year=season_year))
    if not rounds:
        return []

    # Pre-compute top-5 only for rounds whose results are visible
    top_by_round: dict[int, dict[str, dict[int, Team]]] = {}
    for r in rounds:
        if is_results_visible(r, is_admin):
            top_by_round[r.id] = _top5_cache(r, parse_round_categories(r))

    tip_qs = (
        Tip.objects
        .filter(round__season_year=season_year)
        .select_related("user", "user__msl_profile", "team")
    )

    stats: dict[int, dict] = defaultdict(lambda: {
        "user": None,
        "points": 0,
        "total_tips": 0,
        "hits": {i: 0 for i in range(1, 6)},
    })

    for tip in tip_qs:
        row = stats[tip.user_id]
        row["user"] = tip.user
        row["total_tips"] += 1
        top = top_by_round.get(tip.round_id, {}).get(tip.category, {})
        correct = top.get(tip.position)
        if correct and correct.id == tip.team_id:
            row["points"] += 1
            row["hits"][tip.position] += 1

    out = []
    for row in stats.values():
        user = row["user"]
        profile = getattr(user, "msl_profile", None)
        display_name = (profile.display_name if profile and profile.display_name else user.email)
        out.append({
            "user": user,
            "display_name": display_name,
            "points": row["points"],
            "total_tips": row["total_tips"],
            "hits": row["hits"],
        })

    out.sort(key=lambda r: (r["points"], r["total_tips"]), reverse=True)
    return out


# ---------------------------------------------------------------------------
# Index page helpers
# ---------------------------------------------------------------------------

def latest_tipping_season() -> int | None:
    """Most recent season that has at least one round defined."""
    return SeasonRounds.objects.aggregate(Max("season_year"))["season_year__max"]


def available_seasons() -> list[int]:
    """All seasons that have at least one round, newest first."""
    return list(
        SeasonRounds.objects
        .values_list("season_year", flat=True)
        .distinct()
        .order_by("-season_year")
    )


def build_round_cards(season_year: int | None, user) -> list[dict]:
    """Per-round cards for the index page: state, links, optional user score."""
    if not season_year:
        return []
    admin = is_msl_admin(user)
    rounds = SeasonRounds.objects.filter(season_year=season_year).order_by("datetime")
    round_ids = [r.id for r in rounds]
    rounds_with_tips = set(
        Tip.objects.filter(round_id__in=round_ids)
        .order_by()
        .values_list("round_id", flat=True)
        .distinct()
    )
    user_rounds_with_tips: set[int] = set()
    if user.is_authenticated:
        user_rounds_with_tips = set(
            Tip.objects.filter(user=user, round_id__in=round_ids)
            .order_by()
            .values_list("round_id", flat=True)
            .distinct()
        )
    cards = []
    for r in rounds:
        tipping_open = is_tipping_open(r)
        results_visible = is_results_visible(r, admin)
        user_has_tips = r.id in user_rounds_with_tips
        round_has_tips = r.id in rounds_with_tips
        user_score = None
        if user.is_authenticated and (results_visible or user_has_tips):
            user_score = score_user_round(user, r)
        cards.append({
            "round": r,
            "categories": parse_round_categories(r),
            "tipping_open": tipping_open,
            "results_visible": results_visible,
            "user_score": user_score,
            "user_has_tips": user_has_tips,
            "round_has_tips": round_has_tips,
        })
    return cards
