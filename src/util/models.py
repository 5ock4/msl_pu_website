from django.db import models
from wagtail.models import Page
from wagtail.fields import RichTextField
from wagtail.admin.panels import FieldPanel


class CategoryChoices(models.TextChoices):
    MUZI = 'M', 'Muži'
    ZENY = 'Ž', 'Ženy'
    VETERANI = '35+', '35+'

class GDPRPage(Page):
    body = RichTextField(blank=True)
    
    content_panels = Page.content_panels + [
        FieldPanel("body"),
    ]