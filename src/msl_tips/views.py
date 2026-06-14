from django.contrib import messages
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.db import IntegrityError, transaction
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render

from msl_about.models import SeasonRounds

from .models import Tip
from .services import (
    actual_top5,
    category_label,
    is_results_visible,
    is_tipping_open,
    parse_round_categories,
    score_user_round,
    season_teams_for,
)


def _build_category_block(round_obj, category, user, *, include_actual):
    """Render data for one (round, category) block on the tipping screen / overview."""
    teams = list(season_teams_for(round_obj, category))
    existing = {
        t.position: t for t in Tip.objects.filter(user=user, round=round_obj, category=category).select_related("team")
    }
    actual = actual_top5(round_obj, category) if include_actual else {}
    slots = []
    for pos in range(1, 6):
        tip = existing.get(pos)
        correct_team = actual.get(pos)
        is_correct = bool(tip and correct_team and tip.team_id == correct_team.id)
        slots.append({
            "position": pos,
            "tip": tip,
            "locked": tip is not None,
            "correct_team": correct_team,
            "is_correct": is_correct,
        })
    return {
        "category": category,
        "category_label": category_label(category),
        "teams": teams,
        "slots": slots,
    }


def round_tips(request, round_id):
    """User's own tipping screen for one round."""
    round_obj = get_object_or_404(SeasonRounds, id=round_id)
    categories = parse_round_categories(round_obj)
    tipping_open = is_tipping_open(round_obj) and request.user.is_authenticated
    results_visible = is_results_visible(round_obj)

    if request.method == "POST":
        if not request.user.is_authenticated:
            messages.error(request, "Pro odeslání tipů se musíš přihlásit.")
            return redirect("msl_tips:round_tips", round_id=round_obj.id)
        if not is_tipping_open(round_obj):
            messages.error(request, "Tipování pro toto kolo je uzavřeno.")
            return redirect("msl_tips:round_tips", round_id=round_obj.id)

        created = 0
        errors: list[str] = []

        for category in categories:
            allowed_team_ids = set(season_teams_for(round_obj, category).values_list("id", flat=True))
            existing = Tip.objects.filter(user=request.user, round=round_obj, category=category)
            taken_positions = set(existing.values_list("position", flat=True))
            taken_team_ids = set(existing.values_list("team_id", flat=True))

            # collect intended new tips for this category
            chosen_in_post: dict[int, int] = {}
            for pos in range(1, 6):
                if pos in taken_positions:
                    continue
                raw = request.POST.get(f"tip_{category}_{pos}", "").strip()
                if not raw:
                    continue
                try:
                    team_id = int(raw)
                except ValueError:
                    errors.append(f"{category_label(category)} – pozice {pos}: neplatný tým.")
                    continue
                if team_id not in allowed_team_ids:
                    errors.append(f"{category_label(category)} – pozice {pos}: tým není v této kategorii.")
                    continue
                if team_id in taken_team_ids or team_id in chosen_in_post.values():
                    errors.append(
                        f"{category_label(category)} – tým je již použit v jiné pozici."
                    )
                    continue
                chosen_in_post[pos] = team_id

            for pos, team_id in chosen_in_post.items():
                try:
                    with transaction.atomic():
                        Tip.objects.create(
                            user=request.user,
                            round=round_obj,
                            category=category,
                            position=pos,
                            team_id=team_id,
                        )
                    created += 1
                except IntegrityError:
                    errors.append(
                        f"{category_label(category)} – pozice {pos}: tip nelze uložit (kolize)."
                    )

        if created:
            messages.success(request, f"Uloženo tipů: {created}.")
        for err in errors:
            messages.error(request, err)
        if not created and not errors:
            messages.info(request, "Nebyly vybrány žádné nové tipy.")
        return redirect("msl_tips:round_tips", round_id=round_obj.id)

    blocks = (
        [_build_category_block(round_obj, c, request.user, include_actual=results_visible)
         for c in categories]
        if request.user.is_authenticated else []
    )
    user_score = (
        score_user_round(request.user, round_obj)
        if request.user.is_authenticated and results_visible
        else None
    )

    return render(request, "msl_tips/round_tips.html", {
        "round": round_obj,
        "blocks": blocks,
        "tipping_open": tipping_open,
        "results_visible": results_visible,
        "user_score": user_score,
    })


def round_tips_overview(request, round_id):
    """All users' tips for one round (only after the round has started)."""
    round_obj = get_object_or_404(SeasonRounds, id=round_id)
    if not is_results_visible(round_obj):
        raise Http404("Přehled tipů bude dostupný po startu kola.")

    categories = parse_round_categories(round_obj)

    user_ids = list(
        Tip.objects.filter(round=round_obj)
        .order_by()
        .values_list("user_id", flat=True)
        .distinct()
    )

    actual_by_cat = {c: actual_top5(round_obj, c) for c in categories}

    rows: list[dict] = []
    tips_by_user_cat: dict[tuple[int, str], dict[int, Tip]] = {}
    for tip in Tip.objects.filter(round=round_obj).select_related("team", "user", "user__msl_profile"):
        tips_by_user_cat.setdefault((tip.user_id, tip.category), {})[tip.position] = tip

    for uid in user_ids:
        user = None
        per_category: dict[str, dict[int, dict]] = {c: {} for c in categories}
        total_points = 0
        total_tips = 0
        for cat in categories:
            actual = actual_by_cat[cat]
            for pos in range(1, 6):
                tip = tips_by_user_cat.get((uid, cat), {}).get(pos)
                if tip is not None:
                    user = tip.user
                    total_tips += 1
                correct_team = actual.get(pos)
                is_correct = bool(tip and correct_team and tip.team_id == correct_team.id)
                if is_correct:
                    total_points += 1
                per_category[cat][pos] = {
                    "tip": tip,
                    "correct_team": correct_team,
                    "is_correct": is_correct,
                }

        # Reshape to a list of position rows, each with cells aligned to `categories`.
        position_rows = []
        for pos in range(1, 6):
            cells = [per_category[c][pos] for c in categories]
            position_rows.append({"position": pos, "cells": cells})

        profile = getattr(user, "msl_profile", None) if user else None
        display_name = (profile.display_name if profile and profile.display_name else (user.email if user else "—"))
        rows.append({
            "user": user,
            "display_name": display_name,
            "position_rows": position_rows,
            "points": total_points,
            "total_tips": total_tips,
        })

    rows.sort(key=lambda r: (r["points"], r["total_tips"]), reverse=True)

    paginator = Paginator(rows, 10)
    try:
        page_obj = paginator.page(request.GET.get("page", 1))
    except PageNotAnInteger:
        page_obj = paginator.page(1)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages)

    actual_rows = []
    for cat in categories:
        actual_rows.append({
            "category": cat,
            "category_label": category_label(cat),
            "slots": [
                {"position": pos, "team": actual_by_cat[cat].get(pos)}
                for pos in range(1, 6)
            ],
        })

    return render(request, "msl_tips/round_tips_overview.html", {
        "round": round_obj,
        "category_labels": [category_label(c) for c in categories],
        "rows": page_obj.object_list,
        "page_obj": page_obj,
        "paginator": paginator,
        "actual_rows": actual_rows,
    })
