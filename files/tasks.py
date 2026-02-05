import os
import uuid
import tempfile
import shutil

from celery import shared_task
from django.conf import settings
from django.core.files import File as DjangoFile
from django.contrib.auth import get_user_model

from .models import File
from .converters import word_to_pdf, pdf_to_word
from .whatsapp import send_whatsapp_message

User = get_user_model()

UPLOAD_DIR = os.path.join(settings.MEDIA_ROOT, "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)


# =====================================================
# 🔁 WORD → PDF (ASYNC, LIBREOFFICE)
# =====================================================
@shared_task(bind=True, autoretry_for=(Exception,), retry_kwargs={"max_retries": 3, "countdown": 10})
def word_to_pdf_task(self, file_id, user_id):
    file = File.objects.get(id=file_id)
    user = User.objects.get(id=user_id)
    profile = getattr(user, "userprofile", None)

    tmpdir = tempfile.mkdtemp()

    try:
        pdf_path = word_to_pdf(file.file.path, tmpdir)
        filename = os.path.basename(pdf_path)

        with open(pdf_path, "rb") as f:
            new_file = File.objects.create(
                user=user,
                file=DjangoFile(f, name=filename),
                filename=filename,
            )

        # 🔔 WhatsApp (SAFE)
        if profile and profile.whatsapp_enabled and profile.can_send_whatsapp():
            public_url = f"{settings.FRONTEND_URL}/files/public/{new_file.public_token}/"

            send_whatsapp_message(
                profile.whatsapp_number,
                f"✅ Word → PDF completed\n{public_url}",
            )
            profile.increment_whatsapp()

        return new_file.id

    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


# =====================================================
# 🔁 PDF → WORD (ASYNC)
# =====================================================
@shared_task(bind=True, autoretry_for=(Exception,), retry_kwargs={"max_retries": 3, "countdown": 10})
def pdf_to_word_task(self, file_id, user_id):
    original = File.objects.get(id=file_id)
    user = User.objects.get(id=user_id)
    profile = getattr(user, "userprofile", None)

    filename = f"{os.path.splitext(original.filename)[0]}.docx"
    output_path = os.path.join(UPLOAD_DIR, f"{uuid.uuid4()}_{filename}")

    pdf_to_word(original.file.path, output_path)

    with open(output_path, "rb") as f:
        new_file = File.objects.create(
            user=user,
            file=DjangoFile(f, name=filename),
            filename=filename,
        )

    # 🔔 WhatsApp (SAFE)
    if profile and profile.whatsapp_enabled and profile.can_send_whatsapp():
        public_url = f"{settings.FRONTEND_URL}/files/public/{new_file.public_token}/"

        send_whatsapp_message(
            profile.whatsapp_number,
            f"✅ PDF → Word completed\n{public_url}",
        )
        profile.increment_whatsapp()

    return new_file.id
