import os
import uuid
import zipfile
import tempfile
import shutil

from django.http import FileResponse, Http404
from django.core.files import File as DjangoFile
from django.shortcuts import get_object_or_404
from django.conf import settings
from django.utils import timezone

from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework.generics import ListAPIView

from files.whatsapp import send_whatsapp_message
from .models import File
from .serializers import FileSerializer
from .converters import (
    word_to_pdf,
    pdf_to_word,
    merge_pdfs,
    split_pdf,
    sign_pdf,
)
CELERY_ENABLED = getattr(settings, "CELERY_ENABLED", False)

if CELERY_ENABLED:
    from files.tasks import word_to_pdf_task, pdf_to_word_task
# =====================================================
# ⚙ CONFIG
# =====================================================
UPLOAD_DIR = os.path.join(settings.MEDIA_ROOT, "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

MAX_FILE_MB = 10
MAX_FILE_BYTES = MAX_FILE_MB * 1024 * 1024


# =====================================================
# 🔔 WHATSAPP SAFETY (OPTIONAL – NEVER BLOCKS CORE)
# =====================================================
def enforce_whatsapp_rules(request):
    profile = getattr(request.user, "userprofile", None)
    if not profile or not profile.whatsapp_enabled or not profile.whatsapp_number:
        return False

    today = timezone.now().date()
    if profile.last_whatsapp_date != today:
        profile.daily_whatsapp_count = 0
        profile.last_whatsapp_date = today
        profile.save(update_fields=["daily_whatsapp_count", "last_whatsapp_date"])

    return profile.daily_whatsapp_count < 5


def mark_whatsapp_sent(profile):
    profile.daily_whatsapp_count += 1
    profile.save(update_fields=["daily_whatsapp_count"])


class WhatsAppMixin:
    def send_whatsapp(self, request, file_obj, title):
        profile = getattr(request.user, "userprofile", None)
        if not profile or not enforce_whatsapp_rules(request):
            return

        public_url = request.build_absolute_uri(
            f"/files/public/{file_obj.public_token}/"
        )

        send_whatsapp_message(
            profile.whatsapp_number,
            f"{title}\n{public_url}",
        )

        mark_whatsapp_sent(profile)


# =====================================================
# 📂 LIST FILES
# =====================================================
class FileListView(ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = FileSerializer

    def get_queryset(self):
        return File.objects.filter(user=self.request.user).order_by("-id")

    def get_serializer_context(self):
        return {"request": self.request}


# =====================================================
# ⬆ UPLOAD
# =====================================================
class UploadFileView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        uploaded_file = request.FILES.get("file")

        if not uploaded_file:
            return Response({"error": "No file uploaded"}, status=400)

        if uploaded_file.size > MAX_FILE_BYTES:
            return Response(
                {"error": f"File too large. Max {MAX_FILE_MB}MB allowed"},
                status=400,
            )

        obj = File.objects.create(
            user=request.user,
            file=uploaded_file,
            filename=uploaded_file.name,
        )

        return Response(
            FileSerializer(obj, context={"request": request}).data,
            status=201,
        )


# =====================================================
# ❌ DELETE
# =====================================================
class DeleteFileView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, file_id):
        obj = get_object_or_404(File, id=file_id, user=request.user)
        obj.file.delete(save=False)
        obj.delete()
        return Response({"message": "Deleted"}, status=200)


# =====================================================
# ⬇ DOWNLOAD
# =====================================================
class DownloadFileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, file_id):
        obj = get_object_or_404(File, id=file_id, user=request.user)

        if not obj.file or not os.path.exists(obj.file.path):
            raise Http404("File not found")

        return FileResponse(obj.file.open("rb"), as_attachment=True, filename=obj.filename)


# =====================================================
# 🔁 WORD → PDF (ASYNC)
# =====================================================
class WordToPDFView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, file_id):
        original = get_object_or_404(File, id=file_id, user=request.user)

        # 🚫 Web-only deployment (Render)
        if not CELERY_ENABLED:
            return Response(
                {
                    "message": "Word → PDF conversion queued. Processing will occur in background worker."
                },
                status=202,
            )

        # ✅ Worker-enabled environment
        profile = getattr(request.user, "userprofile", None)
        whatsapp = profile.whatsapp_number if profile else None

        word_to_pdf_task.delay(
            file_id=original.id,
            user_id=request.user.id,
            whatsapp_number=whatsapp,
        )

        return Response(
            {"message": "Word → PDF conversion started"},
            status=202,
        )


# =====================================================
# 🔁 PDF → WORD (ASYNC)
# =====================================================
class PDFToWordView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, file_id):
        original = get_object_or_404(File, id=file_id, user=request.user)

        if not original.filename.lower().endswith(".pdf"):
            return Response({"error": "Only PDF allowed"}, status=400)

        # 🚫 Web-only deployment (Render)
        if not CELERY_ENABLED:
            return Response(
                {
                    "message": "PDF → Word conversion queued. Processing will occur in background worker."
                },
                status=202,
            )

        # ✅ Worker-enabled environment
        profile = getattr(request.user, "userprofile", None)
        whatsapp = profile.whatsapp_number if profile else None

        pdf_to_word_task.delay(
            file_id=original.id,
            user_id=request.user.id,
            whatsapp_number=whatsapp,
        )

        return Response(
            {"message": "PDF → Word conversion started"},
            status=202,
        )

# =====================================================
# ➕ MERGE PDFs
# =====================================================
class MergePDFView(APIView, WhatsAppMixin):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        ids = request.data.get("file_ids", [])
        files = File.objects.filter(id__in=ids, user=request.user)

        if files.count() < 2:
            return Response({"error": "Select at least 2 PDFs"}, status=400)

        filename = f"merged_{uuid.uuid4()}.pdf"
        output_path = os.path.join(UPLOAD_DIR, filename)

        merge_pdfs([f.file.path for f in files], output_path)

        with open(output_path, "rb") as f:
            db_file = File.objects.create(
                user=request.user,
                file=DjangoFile(f, name=filename),
                filename=filename,
            )

        # 🔔 WhatsApp (optional)
        self.send_whatsapp(request, db_file, "✅ PDFs merged successfully")

        return Response(
            FileSerializer(db_file, context={"request": request}).data,
            status=201,
        )

# =====================================================
# ✂ SPLIT PDF
# =====================================================
class SplitPDFView(APIView, WhatsAppMixin):
    permission_classes = [IsAuthenticated]

    def post(self, request, file_id):
        obj = get_object_or_404(File, id=file_id, user=request.user)
        tmpdir = tempfile.mkdtemp()
        created_files = []

        try:
            pages = split_pdf(obj.file.path, tmpdir)

            for path in pages:
                name = os.path.basename(path)

                with open(path, "rb") as f:
                    new_file = File.objects.create(
                        user=request.user,
                        file=DjangoFile(f, name=name),
                        filename=name,
                    )
                    created_files.append(new_file)

            # 🔔 WhatsApp (send first file link)
            if created_files:
                self.send_whatsapp(
                    request,
                    created_files[0],
                    "✅ PDF split completed",
                )

            return Response(
                FileSerializer(
                    created_files,
                    many=True,
                    context={"request": request},
                ).data,
                status=201,
            )
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)


# =====================================================
# ✍ SIGN PDF
# =====================================================
class SignPDFView(APIView, WhatsAppMixin):
    permission_classes = [IsAuthenticated]

    def post(self, request, file_id):
        obj = get_object_or_404(File, id=file_id, user=request.user)
        signer = request.data.get("signer", "Signed User")

        filename = f"signed_{uuid.uuid4()}.pdf"
        output_path = os.path.join(UPLOAD_DIR, filename)

        sign_pdf(obj.file.path, output_path, signer)

        with open(output_path, "rb") as f:
            signed_file = File.objects.create(
                user=request.user,
                file=DjangoFile(f, name=filename),
                filename=filename,
            )

        self.send_whatsapp(
            request,
            signed_file,
            "✍️ PDF signed successfully",
        )

        return Response(
            FileSerializer(signed_file, context={"request": request}).data,
            status=201,
        )


# =====================================================
# 🌍 PUBLIC DOWNLOAD
# =====================================================
class PublicDownloadView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, token):
        obj = get_object_or_404(File, public_token=token)

        if not obj.file or not os.path.exists(obj.file.path):
            raise Http404("File not found")

        return FileResponse(obj.file.open("rb"), as_attachment=True, filename=obj.filename)
