from django.http import Http404
from django.shortcuts import render

from util.auth import is_msl_admin
from .release_notes import RELEASE_NOTES


def release_notes(request):
    if not is_msl_admin(request.user):
        raise Http404
    return render(request, "util/release_notes.html", {
        "release_notes": RELEASE_NOTES,
        "current_version": RELEASE_NOTES[0]["version"] if RELEASE_NOTES else "",
    })
