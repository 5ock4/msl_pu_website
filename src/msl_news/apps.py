from django.apps import AppConfig


class MslNewsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "msl_news"

    def ready(self):
        from wagtail.signals import page_published
        from .signals import on_news_page_published

        page_published.connect(on_news_page_published, dispatch_uid="msl_news.post_to_facebook")
