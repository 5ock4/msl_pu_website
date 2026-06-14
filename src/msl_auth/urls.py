from django.urls import path

from . import views

app_name = "msl_auth"

urlpatterns = [
    path("auth/verify/", views.verify_magic_link, name="magic_link_verify"),
    path("auth/logout/", views.logout_view, name="magic_link_logout"),
    path("auth/setup-username/", views.setup_username, name="setup_username"),
]
