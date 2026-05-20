from django.shortcuts import get_object_or_404, redirect
from django.contrib.auth.decorators import user_passes_test
from django.contrib import messages
from django.db import transaction
from wagtail.documents.models import Document

from msl_results.round_results_preprocessor import RoundResultsPreprocessor
from .models import SeasonRounds, RoundsPage, RoundDocumentEdit

MAX_PDF_SIZE_MB = 2
MAX_PDF_SIZE = MAX_PDF_SIZE_MB * 1024 * 1024
MAX_STARTOVKA_CHARS = 5_000
MAX_STARTOVKA_LINES = 200


def is_wagtail_admin(user):
    return user.is_authenticated and (user.is_staff or user.is_superuser or user.username == 'RadaMSL')


def _is_valid_pdf(uploaded_file):
    uploaded_file.seek(0)
    magic = uploaded_file.read(5)
    uploaded_file.seek(0)
    return magic == b'%PDF-' and uploaded_file.content_type == 'application/pdf'


@user_passes_test(is_wagtail_admin)
def upload_results(request, round_id):
    round_obj = get_object_or_404(SeasonRounds, id=round_id)

    if request.method == 'POST' and request.FILES.get('results_file'):
        round_results_manipulator = RoundResultsPreprocessor(round_obj, request.FILES['results_file'])
        round_results_manipulator.store_to_results_model()

        messages.success(request, f'Výsledky pro kolo {round_obj.round} úspěšně vloženy!')

    return _redirect_to_rounds_page()


def upload_pozvanka(request, round_id):
    round_obj = get_object_or_404(SeasonRounds, id=round_id)

    if request.method == 'POST' and request.FILES.get('pozvanka_file'):
        uploaded_file = request.FILES['pozvanka_file']
        if not round_obj.uploads_open:
            messages.error(request, f'Nahrávání dokumentů pro kolo {round_obj.round} je uzavřeno.')
        elif uploaded_file.size > MAX_PDF_SIZE:
            messages.error(request, f'Soubor pozvánky je příliš velký (max {MAX_PDF_SIZE_MB} MB).')
        elif not _is_valid_pdf(uploaded_file):
            messages.error(request, 'Soubor pozvánky není platný PDF soubor.')
        else:
            doc = None
            try:
                with transaction.atomic():
                    round_obj = SeasonRounds.objects.select_for_update().get(id=round_id)
                    first_edit = RoundDocumentEdit.objects.filter(
                        round=round_obj, doc_type='pozvanka'
                    ).order_by('edited_at').first()
                    if first_edit and first_edit.edited_by != request.user.email:
                        messages.error(request, f'Pozvánku pro toto kolo může upravovat pouze {first_edit.edited_by}.')
                    else:
                        old_doc = round_obj.pozvanka_pdf
                        doc = Document(title=f'Pozvánka {round_obj}', file=uploaded_file)
                        doc.save()
                        round_obj.pozvanka_pdf = doc
                        round_obj.save()
                        if old_doc:
                            old_doc.delete()
                        RoundDocumentEdit.objects.create(
                            round=round_obj, doc_type='pozvanka',
                            edited_by=request.user.email, detail=uploaded_file.name,
                        )
                        doc = None  # transaction committed, no cleanup needed
                        messages.success(request, f'Pozvánka pro kolo {round_obj.round} úspěšně nahrána!')
            except Exception:
                if doc is not None:
                    doc.file.storage.delete(doc.file.name)
                raise

    return _redirect_to_rounds_page()


def save_startovka(request, round_id):
    round_obj = get_object_or_404(SeasonRounds, id=round_id)

    if request.method == 'POST':
        if not round_obj.uploads_open:
            messages.error(request, f'Nahrávání dokumentů pro kolo {round_obj.round} je uzavřeno.')
        else:
            text = request.POST.get('startovka_text', '')
            if len(text) > MAX_STARTOVKA_CHARS:
                messages.error(request, f'Startovka je příliš dlouhá (max {MAX_STARTOVKA_CHARS} znaků).')
            elif text.count('\n') + 1 > MAX_STARTOVKA_LINES:
                messages.error(request, f'Startovka obsahuje příliš mnoho řádků (max {MAX_STARTOVKA_LINES}).')
            else:
                with transaction.atomic():
                    round_obj = SeasonRounds.objects.select_for_update().get(id=round_id)
                    first_edit = RoundDocumentEdit.objects.filter(
                        round=round_obj, doc_type='startovka'
                    ).order_by('edited_at').first()
                    if first_edit and first_edit.edited_by != request.user.email:
                        messages.error(request, f'Startovku pro toto kolo může upravovat pouze {first_edit.edited_by}.')
                    else:
                        round_obj.startovka_text = text
                        round_obj.save()
                        team_count = len([l for l in text.splitlines() if l.strip()])
                        RoundDocumentEdit.objects.create(
                            round=round_obj, doc_type='startovka',
                            edited_by=request.user.email, detail=f'{team_count} týmů',
                        )
                        messages.success(request, f'Startovka pro kolo {round_obj.round} úspěšně uložena!')

    return _redirect_to_rounds_page()


def _redirect_to_rounds_page():
    try:
        rounds_page = RoundsPage.objects.live().first()
        if rounds_page:
            return redirect(rounds_page.url)
    except Exception:
        pass
    return redirect('/')
