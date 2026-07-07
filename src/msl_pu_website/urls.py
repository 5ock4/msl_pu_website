from django.conf import settings
from django.urls import include, path
from django.contrib import admin

from wagtail.admin import urls as wagtailadmin_urls
from wagtail import urls as wagtail_urls
from wagtail.documents import urls as wagtaildocs_urls

from search import views as search_views
from msl_about import views as msl_about_views
from msl_results import views as msl_results_views

urlpatterns = [
    path("django-admin/", admin.site.urls),
    path("admin/", include(wagtailadmin_urls)),
    path("documents/", include(wagtaildocs_urls)),
    path("search/", search_views.search, name="search"),
    path("upload-results/<int:round_id>/", msl_about_views.upload_results, name="upload_results"),
    path("upload-pozvanka/<int:round_id>/", msl_about_views.upload_pozvanka, name="upload_pozvanka"),
    path("upload-startovka/<int:round_id>/", msl_about_views.save_startovka, name="save_startovka"),
    path("save-video-url/<int:round_id>/", msl_about_views.save_video_url, name="save_video_url"),
    path("toggle-results-ready/<int:round_id>/", msl_about_views.toggle_results_ready, name="toggle_results_ready"),
    path('round/<int:round_id>/<str:category>', msl_results_views.round_detail, name='round_detail'),
    path("facebook/", include("msl_news.urls")),
    path("", include("msl_auth.urls")),
    path("", include("util.urls")),
    path("", include("msl_tips.urls")),
]


if settings.DEBUG:
    from django.conf.urls.static import static
    from django.contrib.staticfiles.urls import staticfiles_urlpatterns

    # Serve static and media files from development server
    urlpatterns += staticfiles_urlpatterns()
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

urlpatterns = urlpatterns + [
    # For anything not caught by a more specific rule above, hand over to
    # Wagtail's page serving mechanism. This should be the last pattern in
    # the list:
    path("", include(wagtail_urls)),
    # Alternatively, if you want Wagtail pages to be served from a subpath
    # of your site, rather than the site root:
    #    path("pages/", include(wagtail_urls)),
]
