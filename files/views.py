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
from rest_framework import status

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

# =====================================================
# ⚙ CONFIG
# =====================================================
UPLOAD_DIR = os.path.join(settings.MEDIA_ROOT, "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

MAX_FILE_MB = 10
MAX_FILE_BYTES = MAX_FILE_MB * 1024 * 1024


# =====================================================
# 🔔 WHATSAPP SAFETY
# =====================================================
def enforce_whatsapp_rules(request):
    """
    WhatsApp is OPTIONAL.
    This function only decides whether WhatsApp can be sent.
    It MUST NOT block file operations.
    """
    profile = getattr(request.user, "userprofile", None)

    if not profile:
        return False  # allow conversion

    if not profile.whatsapp_enabled:
        return False

    if not profile.whatsapp_number:
        return False

    today = timezone.now().date()
    if profile.last_whatsapp_date != today:
        profile.daily_whatsapp_count = 0
        profile.last_whatsapp_date = today
        profile.save()

    if profile.daily_whatsapp_count >= 5:
        return False

    return True


def mark_whatsapp_sent(profile):
    profile.daily_whatsapp_count += 1
    profile.save(update_fields=["daily_whatsapp_count"])


def safe_get_profile(user):
    return getattr(user, "userprofile", None)


class WhatsAppMixin:
    def send_whatsapp(self, request, file_obj, title):
        profile = safe_get_profile(request.user)

        if not enforce_whatsapp_rules(request):
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

        return FileResponse(
            obj.file.open("rb"),
            as_attachment=True,
            filename=obj.filename,
        )


# =====================================================
# 🔁 WORD → PDF
# =====================================================
class WordToPDFView(APIView, WhatsAppMixin):
    permission_classes = [IsAuthenticated]

    def post(self, request, file_id):
        error = enforce_whatsapp_rules(request)
        if error:
            return error

        original = get_object_or_404(File, id=file_id, user=request.user)

        try:
            filename = f"{uuid.uuid4()}.pdf"
            output_path = os.path.join(UPLOAD_DIR, filename)

            word_to_pdf(original.file.path, output_path)

            with open(output_path, "rb") as f:
                converted = File.objects.create(
                    user=request.user,
                    file=DjangoFile(f, name=filename),
                    filename=filename,
                )

            self.send_whatsapp(
                request, converted, "📄 Your converted PDF is ready:"
            )

            return Response(
                FileSerializer(converted, context={"request": request}).data,
                status=201,
            )

        except Exception:
            return Response(
                {"error": "Word → PDF failed. File may be unsupported."},
                status=400,
            )


# =====================================================
# 🔁 PDF → WORD
# =====================================================
class PDFToWordView(APIView, WhatsAppMixin):
    permission_classes = [IsAuthenticated]

    def post(self, request, file_id):
        error = enforce_whatsapp_rules(request)
        if error:
            return error

        original = get_object_or_404(File, id=file_id, user=request.user)

        if original.file.size > MAX_FILE_BYTES:
            return Response(
                {"error": "PDF too large for free tier conversion"},
                status=400,
            )

        try:
            filename = f"{uuid.uuid4()}.docx"
            output_path = os.path.join(UPLOAD_DIR, filename)

            pdf_to_word(original.file.path, output_path)

            with open(output_path, "rb") as f:
                converted = File.objects.create(
                    user=request.user,
                    file=DjangoFile(f, name=filename),
                    filename=filename,
                )

            self.send_whatsapp(
                request, converted, "📄 Your converted Word file is ready:"
            )

            return Response(
                FileSerializer(converted, context={"request": request}).data,
                status=201,
            )

        except Exception:
            return Response(
                {"error": "PDF too complex to convert on free tier"},
                status=400,
            )


# =====================================================
# ➕ MERGE PDFs
# =====================================================
class MergePDFView(APIView, WhatsAppMixin):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        error = enforce_whatsapp_rules(request)
        if error:
            return error

        ids = request.data.get("file_ids", [])
        files = File.objects.filter(id__in=ids, user=request.user)

        if files.count() < 2:
            return Response(
                {"error": "Select at least 2 PDF files"},
                status=400,
            )

        try:
            filename = f"{uuid.uuid4()}.pdf"
            output_path = os.path.join(UPLOAD_DIR, filename)

            merge_pdfs([f.file.path for f in files], output_path)

            with open(output_path, "rb") as f:
                merged = File.objects.create(
                    user=request.user,
                    file=DjangoFile(f, name=filename),
                    filename=filename,
                )

            self.send_whatsapp(
                request, merged, "📄 Your merged PDF is ready:"
            )

            return Response(
                FileSerializer(merged, context={"request": request}).data,
                status=201,
            )

        except Exception:
            return Response(
                {"error": "PDF merge failed. Files may be incompatible."},
                status=400,
            )


# =====================================================
# ✂ SPLIT PDF
# =====================================================
class SplitPDFView(APIView, WhatsAppMixin):
    permission_classes = [IsAuthenticated]

    def post(self, request, file_id):
        error = enforce_whatsapp_rules(request)
        if error:
            return error

        obj = get_object_or_404(File, id=file_id, user=request.user)

        tmpdir = tempfile.mkdtemp()
        try:
            output_files = split_pdf(obj.file.path, tmpdir)

            zip_name = f"{uuid.uuid4()}.zip"
            zip_path = os.path.join(UPLOAD_DIR, zip_name)

            with zipfile.ZipFile(zip_path, "w") as z:
                for p in output_files:
                    z.write(p, arcname=os.path.basename(p))

            with open(zip_path, "rb") as f:
                zip_file = File.objects.create(
                    user=request.user,
                    file=DjangoFile(f, name=zip_name),
                    filename="split_pages.zip",
                )

            self.send_whatsapp(
                request, zip_file, "📦 Your split PDF files are ready:"
            )

            return Response(
                FileSerializer(zip_file, context={"request": request}).data,
                status=201,
            )

        except Exception:
            return Response(
                {"error": "PDF split failed"},
                status=400,
            )

        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)


# =====================================================
# ✍ SIGN PDF (SAFE VERSION)
# =====================================================
class SignPDFView(APIView, WhatsAppMixin):
    permission_classes = [IsAuthenticated]

    def post(self, request, file_id):
        error = enforce_whatsapp_rules(request)
        if error:
            return error

        obj = get_object_or_404(File, id=file_id, user=request.user)
        signer = request.data.get("signer", "Signed User")

        try:
            filename = f"{uuid.uuid4()}.pdf"
            output_path = os.path.join(UPLOAD_DIR, filename)

            sign_pdf(obj.file.path, output_path, signer)

            with open(output_path, "rb") as f:
                signed = File.objects.create(
                    user=request.user,
                    file=DjangoFile(f, name=filename),
                    filename=filename,
                )

            self.send_whatsapp(
                request, signed, "✍ Your signed PDF is ready:"
            )

            return Response(
                FileSerializer(signed, context={"request": request}).data,
                status=201,
            )

        except Exception:
            return Response(
                {"error": "PDF signing failed. Unsupported PDF format."},
                status=400,
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

        return FileResponse(
            obj.file.open("rb"),
            as_attachment=True,
            filename=obj.filename,
        )
