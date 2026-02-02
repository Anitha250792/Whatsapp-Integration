import os
import uuid
import zipfile
import tempfile
import shutil

from django.http import FileResponse, Http404
from django.core.files import File as DjangoFile
from django.shortcuts import get_object_or_404
from django.conf import settings

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
# 🔧 GLOBAL UPLOAD DIR (CREATE ONCE)
# =====================================================
UPLOAD_DIR = os.path.join(settings.MEDIA_ROOT, "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)


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
# ⬇ DOWNLOAD (AUTH)
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
class WordToPDFView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, file_id):
        original = get_object_or_404(File, id=file_id, user=request.user)

        if not original.filename.lower().endswith(".docx"):
            return Response({"error": "Only .docx files allowed"}, status=400)

        filename = f"{uuid.uuid4()}.pdf"
        output_path = os.path.join(UPLOAD_DIR, filename)

        word_to_pdf(original.file.path, output_path)

        with open(output_path, "rb") as f:
            converted = File.objects.create(
                user=request.user,
                file=DjangoFile(f, name=filename),
                filename=filename,
            )

        self.send_whatsapp(request, converted, "📄 Your converted PDF is ready:")

        return Response(
            FileSerializer(converted, context={"request": request}).data,
            status=201,
        )


# =====================================================
# 🔁 PDF → WORD
# =====================================================
class PDFToWordView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, file_id):
        original = get_object_or_404(File, id=file_id, user=request.user)

        if not original.filename.lower().endswith(".pdf"):
            return Response({"error": "Only PDF files allowed"}, status=400)

        filename = f"{uuid.uuid4()}.docx"
        output_path = os.path.join(UPLOAD_DIR, filename)

        pdf_to_word(original.file.path, output_path)

        with open(output_path, "rb") as f:
            converted = File.objects.create(
                user=request.user,
                file=DjangoFile(f, name=filename),
                filename=filename,
            )

        self.send_whatsapp(request, converted, "📄 Your converted Word file is ready:")

        return Response(
            FileSerializer(converted, context={"request": request}).data,
            status=201,
        )


# =====================================================
# ➕ MERGE PDFs
# =====================================================
class MergePDFView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        ids = request.data.get("file_ids", [])

        if not isinstance(ids, list) or len(ids) < 2:
            return Response({"error": "Select at least 2 PDFs"}, status=400)

        files = File.objects.filter(id__in=ids, user=request.user)

        filename = f"{uuid.uuid4()}.pdf"
        output_path = os.path.join(UPLOAD_DIR, filename)

        merge_pdfs([f.file.path for f in files], output_path)

        with open(output_path, "rb") as f:
            merged = File.objects.create(
                user=request.user,
                file=DjangoFile(f, name=filename),
                filename=filename,
            )

        self.send_whatsapp(request, merged, "📄 Your merged PDF is ready:")

        return Response(
            FileSerializer(merged, context={"request": request}).data,
            status=201,
        )


# =====================================================
# ✂ SPLIT PDF
# =====================================================
class SplitPDFView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, file_id):
        obj = get_object_or_404(File, id=file_id, user=request.user)

        tmpdir = tempfile.mkdtemp()
        try:
            output_files = split_pdf(obj.file.path, tmpdir)

            zip_name = f"{uuid.uuid4()}.zip"
            zip_path = os.path.join(UPLOAD_DIR, zip_name)

            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
                for p in output_files:
                    z.write(p, arcname=os.path.basename(p))

            with open(zip_path, "rb") as f:
                zip_file = File.objects.create(
                    user=request.user,
                    file=DjangoFile(f, name=zip_name),
                    filename="split_pages.zip",
                )

            self.send_whatsapp(request, zip_file, "📦 Your split PDF files are ready:")

            return Response(
                FileSerializer(zip_file, context={"request": request}).data,
                status=201,
            )
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)


# =====================================================
# ✍ SIGN PDF
# =====================================================
class SignPDFView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, file_id):
        signer = request.data.get("signer", "Signed User")
        obj = get_object_or_404(File, id=file_id, user=request.user)

        filename = f"{uuid.uuid4()}.pdf"
        output_path = os.path.join(UPLOAD_DIR, filename)

        sign_pdf(obj.file.path, output_path, signer)

        with open(output_path, "rb") as f:
            signed = File.objects.create(
                user=request.user,
                file=DjangoFile(f, name=filename),
                filename=filename,
            )

        self.send_whatsapp(request, signed, "✍ Your signed PDF is ready:")

        return Response(
            FileSerializer(signed, context={"request": request}).data,
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

        return FileResponse(
            obj.file.open("rb"),
            as_attachment=True,
            filename=obj.filename,
        )


# =====================================================
# 🔔 WHATSAPP HELPER (SAFE)
# =====================================================
def safe_get_profile(user):
    return getattr(user, "userprofile", None)


class WhatsAppMixin:
    def send_whatsapp(self, request, file_obj, title):
        profile = safe_get_profile(request.user)
        if not profile or not profile.whatsapp_number:
            return

        public_url = request.build_absolute_uri(
            f"/files/public/{file_obj.public_token}/"
        )
        send_whatsapp_message(
            profile.whatsapp_number,
            f"{title}\n{public_url}",
        )


# Inject mixin
WordToPDFView.send_whatsapp = WhatsAppMixin.send_whatsapp
PDFToWordView.send_whatsapp = WhatsAppMixin.send_whatsapp
MergePDFView.send_whatsapp = WhatsAppMixin.send_whatsapp
SplitPDFView.send_whatsapp = WhatsAppMixin.send_whatsapp
SignPDFView.send_whatsapp = WhatsAppMixin.send_whatsapp
