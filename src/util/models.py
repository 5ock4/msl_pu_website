from django.db import models
from wagtail.models import Page
from wagtail.fields import RichTextField
from wagtail.admin.panels import FieldPanel

#############
# Constants #
#############
D_NU_PENALTY_POINTS = 5
FREE_BORROWED_COMPETITORS_IN_SEASON = 2

class CategoryChoices(models.TextChoices):
    MUZI = 'M', 'Muži'
    ZENY = 'Ž', 'Ženy'
    VETERANI = '35+', '35+'


class RankingDefChoices(models.TextChoices):
    U = 'U', 'Účast'
    NU = 'NU', 'Neúčast'
    N = 'N', 'Nedokončeno'
    D = 'D', 'Diskvalifikace'


class GDPRPage(Page):
    body = RichTextField(blank=True)
    
    content_panels = Page.content_panels + [
        FieldPanel("body"),
    ]
