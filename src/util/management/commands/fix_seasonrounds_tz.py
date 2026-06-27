from zoneinfo import ZoneInfo

from django.core.management.base import BaseCommand

from msl_about.models import SeasonRounds

PRAGUE = ZoneInfo("Europe/Prague")
UTC = ZoneInfo("UTC")


class Command(BaseCommand):
    """
    One-time fix: shift SeasonRounds.datetime from "stored as Prague local but
    labelled UTC" to correct UTC.

    Background: the database was populated with TIME_ZONE="UTC", so values
    entered in the Wagtail admin as Prague local time (e.g. 10:00 CET) were
    stored as-is (10:00 UTC). After switching TIME_ZONE to "Europe/Prague"
    those values would display 1-2 hours too late. This command reinterprets
    every stored value as a naive Prague local time and converts it to the
    correct UTC equivalent, respecting DST per round date.
    """

    help = "One-time fix: reinterpret SeasonRounds.datetime as Prague local and convert to correct UTC."

    def add_arguments(self, parser):
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Write changes to the database (default is dry run).",
        )

    def handle(self, *args, **options):
        apply = options["apply"]

        if not apply:
            self.stdout.write("DRY RUN — pass --apply to write changes\n")

        rounds = SeasonRounds.objects.order_by("datetime")
        if not rounds.exists():
            self.stdout.write("No SeasonRounds found.")
            return

        for r in rounds:
            stored_utc = r.datetime  # aware UTC, but value is actually Prague local time
            naive = stored_utc.replace(tzinfo=None)
            prague_aware = naive.replace(tzinfo=PRAGUE)
            correct_utc = prague_aware.astimezone(UTC)

            offset_h = (correct_utc - stored_utc).total_seconds() / 3600
            self.stdout.write(
                f"Round {r.id:>3} (kolo {r.round_number}): "
                f"{stored_utc.strftime('%Y-%m-%d %H:%M')} UTC  ->  "
                f"{correct_utc.strftime('%Y-%m-%d %H:%M')} UTC  "
                f"(shift {offset_h:+.0f}h)"
            )

            if apply:
                r.datetime = correct_utc
                r.save(update_fields=["datetime"])

        if not apply:
            self.stdout.write("\nNo changes written. Re-run with --apply to apply.")
        else:
            self.stdout.write(self.style.SUCCESS("\nDone."))
