from django.urls import path
from . import views

urlpatterns = [
    path("release-notes/", views.release_notes, name="release_notes"),
]
