from django.shortcuts import render

from .release_notes import RELEASE_NOTES


def release_notes(request):
    return render(request, "util/release_notes.html", {
        "release_notes": RELEASE_NOTES,
        "current_version": RELEASE_NOTES[0]["version"] if RELEASE_NOTES else "",
    })
