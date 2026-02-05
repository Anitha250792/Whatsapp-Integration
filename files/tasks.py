# files/tasks.py
import os
import uuid

from celery import shared_task
from django.conf import settings
from django.core.files import File as DjangoFile

from .models import File
from .converters import word_to_pdf, pdf_to_word
from .whatsapp import send_whatsapp_message

UPLOAD_DIR = os.path.join(settings.MEDIA_ROOT, "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

@shared_task(bind=True, autoretry_for=(Exception,), retry_kwargs={"max_retries": 3, "countdown": 10})
def word_to_pdf_task(self, file_id, user_id, whatsapp_number=None):
    original = File.objects.get(id=file_id)

    filename = f"word_to_pdf_{uuid.uuid4()}.pdf"
    output_path = os.path.join(UPLOAD_DIR, filename)

    word_to_pdf(original.file.path, output_path)

    with open(output_path, "rb") as f:
        new_file = File.objects.create(
            user_id=user_id,
            file=DjangoFile(f, name=filename),
            filename=filename,
        )

    if whatsapp_number:
        send_whatsapp_message(
            whatsapp_number,
            f"✅ Word → PDF completed\n{settings.BASE_URL}/files/public/{new_file.public_token}/"
        )

    return new_file.id


@shared_task(bind=True, autoretry_for=(Exception,), retry_kwargs={"max_retries": 3, "countdown": 10})
def pdf_to_word_task(self, file_id, user_id, whatsapp_number=None):
    original = File.objects.get(id=file_id)

    filename = f"pdf_to_word_{uuid.uuid4()}.docx"
    output_path = os.path.join(UPLOAD_DIR, filename)

    pdf_to_word(original.file.path, output_path)

    with open(output_path, "rb") as f:
        new_file = File.objects.create(
            user_id=user_id,
            file=DjangoFile(f, name=filename),
            filename=filename,
        )

    if whatsapp_number:
        send_whatsapp_message(
            whatsapp_number,
            f"✅ PDF → Word completed\n{settings.BASE_URL}/files/public/{new_file.public_token}/"
        )

    return new_file.id


