import datetime as dt

from django.test import TestCase
from django.utils import timezone

from msl_about.models import SeasonRounds


class SeasonRoundsTests(TestCase):
    def test_delegates_field_is_stored(self):
        round_obj = SeasonRounds.objects.create(
            season_year=2026,
            round="Brušperk [FM]",
            datetime=timezone.make_aware(dt.datetime(2026, 6, 6, 12, 0)),
            date_registration=dt.date(2026, 5, 24),
            categories="Muži, Ženy, 35+",
            delegates="Markéta Strakošová",
        )

        self.assertEqual(round_obj.delegates, "Markéta Strakošová")
