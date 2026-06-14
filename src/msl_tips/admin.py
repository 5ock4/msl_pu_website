from django.contrib import admin

from .models import Tip


@admin.register(Tip)
class TipAdmin(admin.ModelAdmin):
    list_display = ("user", "round", "category", "position", "team", "submitted_at")
    list_filter = ("round", "category")
    search_fields = (
        "user__email",
        "user__username",
        "user__msl_profile__display_name",
        "team__name",
    )
    raw_id_fields = ("user", "round", "team")
    readonly_fields = ("submitted_at",)
