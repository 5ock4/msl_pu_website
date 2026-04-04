from django.urls import path

from . import views

urlpatterns = [
    path("facebook/auth/", views.facebook_oauth_initiate, name="facebook_oauth_initiate"),
    path("facebook/auth/callback/", views.facebook_oauth_callback, name="facebook_oauth_callback"),
]
