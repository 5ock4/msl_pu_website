from .facebook import post_news_to_facebook
from .models import NewsPage


def on_news_page_published(sender, **kwargs):
    instance = kwargs.get("instance")
    if isinstance(instance, NewsPage):
        post_news_to_facebook(instance)
