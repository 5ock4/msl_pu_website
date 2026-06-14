from django.urls import path

from . import views


app_name = "msl_tips"

urlpatterns = [
    path("tipovacka/round/<int:round_id>/", views.round_tips, name="round_tips"),
    path("tipovacka/round/<int:round_id>/prehled/", views.round_tips_overview, name="round_tips_overview"),
]
