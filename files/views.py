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
        return Response(
            {
                "error": "Word → PDF is disabled on this server. "
                         "This feature requires a background worker."
            },
            status=501,
        )


# =====================================================
# 🔁 PDF → WORD (ASYNC)
# =====================================================
class PDFToWordView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, file_id):
        return Response(
            {
                "error": "PDF → Word is disabled on this server. "
                         "This feature requires a background worker."
            },
            status=501,
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

        # ✅ Clean filename
        names = [
            os.path.splitext(f.filename)[0]
            for f in files
            if f.filename.lower().endswith(".pdf")
        ]

        base_name = "_".join(names[:2])  # avoid very long names
        filename = f"merged_{base_name}.pdf"

        output_path = os.path.join(UPLOAD_DIR, filename)

        # ✅ Merge safely
        merge_pdfs([f.file.path for f in files], output_path)

        # ✅ Save merged file to DB
        with open(output_path, "rb") as f:
            new_file = File.objects.create(
                user=request.user,
                file=DjangoFile(f, name=filename),
                filename=filename,
            )

        # 🔔 WhatsApp auto-send (optional)
        self.send_whatsapp(
            request,
            new_file,
            "✅ PDFs merged successfully",
        )

        return Response(
            FileSerializer(new_file, context={"request": request}).data,
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
        base_name = os.path.splitext(obj.filename)[0]

        try:
            # 1️⃣ Split PDF into pages
            page_paths = split_pdf(obj.file.path, tmpdir)

            if not page_paths:
                return Response(
                    {"error": "PDF split failed"},
                    status=500,
                )

            # 2️⃣ Create ZIP
            zip_filename = f"{base_name}_split_pages.zip"
            zip_path = os.path.join(UPLOAD_DIR, zip_filename)

            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
                for index, page_path in enumerate(page_paths, start=1):
                    page_name = f"{base_name}_page_{index}.pdf"
                    zipf.write(page_path, arcname=page_name)

            # 3️⃣ Save ZIP to DB
            with open(zip_path, "rb") as f:
                zip_file = File.objects.create(
                    user=request.user,
                    file=DjangoFile(f, name=zip_filename),
                    filename=zip_filename,
                )

            # 4️⃣ WhatsApp (ONE message only)
            self.send_whatsapp(
                request,
                zip_file,
                "✅ PDF split completed (ZIP)",
            )

            # 5️⃣ Return ZIP info
            return Response(
                FileSerializer(zip_file, context={"request": request}).data,
                status=201,
            )

        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)


# =====================================================
# ✍ SIGN PDF (SAFE + STABLE)
# =====================================================
class SignPDFView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, file_id):
        obj = get_object_or_404(File, id=file_id, user=request.user)
        signer = request.data.get("signer", "Signed User")

        name, ext = os.path.splitext(obj.filename)
        safe_name = name.replace(" ", "_")
        filename = f"{safe_name}_signed{ext}"

        # ✅ always use temp directory
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            output_path = tmp.name

        try:
            # 🧠 SIGN PDF
            sign_pdf(obj.file.path, output_path, signer)

            # 💾 SAVE TO DB
            with open(output_path, "rb") as f:
                new_file = File.objects.create(
                    user=request.user,
                    file=DjangoFile(f, name=filename),
                    filename=filename,
                )

        except Exception as e:
            print("❌ SIGN ERROR:", e)
            return Response(
                {"error": "Failed to sign PDF"},
                status=500
            )

        finally:
            if os.path.exists(output_path):
                os.remove(output_path)

        # ================= WHATSAPP (NON-BLOCKING) =================
        try:
            profile = getattr(request.user, "userprofile", None)

            if (
                profile
                and profile.whatsapp_enabled
                and profile.can_send_whatsapp()
            ):
                public_url = request.build_absolute_uri(
                    f"/files/public/{new_file.public_token}/"
                )

                send_whatsapp_message(
                    profile.whatsapp_number,
                    f"📄 Signed file ready\n{public_url}",
                )

                profile.increment_whatsapp()

        except Exception as e:
            # ⚠ WhatsApp should NEVER break signing
            print("⚠ WhatsApp failed:", e)

        return Response(
            {
                "message": "PDF signed successfully",
                "file": FileSerializer(new_file, context={"request": request}).data,
            },
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
