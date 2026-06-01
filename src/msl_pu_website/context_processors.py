from util.release_notes import RELEASE_NOTES


def site_version(request):
    version = RELEASE_NOTES[0]["version"] if RELEASE_NOTES else ""
    return {"SITE_VERSION": version}
