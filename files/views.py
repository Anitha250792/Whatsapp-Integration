from django.http import FileResponse, Http404
from django.core.files import File as DjangoFile
from django.shortcuts import get_object_or_404
from django.conf import settings

from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework.generics import ListAPIView

import tempfile
import os
import uuid
import zipfile
import mimetypes

from .models import File
from .serializers import FileSerializer
from .converters import word_to_pdf, pdf_to_word, merge_pdfs, split_pdf, sign_pdf


# ==============================
# 📂 LIST FILES
# ==============================
class FileListView(ListAPIView):
    serializer_class = FileSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return File.objects.filter(user=self.request.user)

    def get_serializer_context(self):
        return {"request": self.request}


# ==============================
# ⬆ UPLOAD
# ==============================
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
            status=201
        )


# ==============================
# ❌ DELETE
# ==============================
class DeleteFileView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, file_id):
        obj = get_object_or_404(File, id=file_id, user=request.user)
        obj.file.delete(save=False)
        obj.delete()
        return Response({"message": "Deleted"})


# ==============================
# ⬇ DOWNLOAD (AUTH)
# ==============================
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


# ==============================
# 🔁 WORD → PDF
# ==============================
class WordToPDFView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, file_id):
        original = get_object_or_404(File, id=file_id, user=request.user)

        if not original.filename.lower().endswith(".docx"):
            return Response({"error": "Only .docx allowed"}, status=400)

        filename = f"{uuid.uuid4()}.pdf"
        output_path = os.path.join(settings.MEDIA_ROOT, "uploads", filename)

        try:
            word_to_pdf(original.file.path, output_path)

            with open(output_path, "rb") as f:
                converted = File.objects.create(
                    user=request.user,
                    file=DjangoFile(f, name=filename),
                    filename=filename,
                )

            return Response(
                FileSerializer(converted, context={"request": request}).data
            )

        except Exception as e:
            print("WORD→PDF ERROR:", e)
            return Response({"error": str(e)}, status=500)


# ==============================
# 🔁 PDF → WORD
# ==============================
class PDFToWordView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, file_id):
        original = get_object_or_404(File, id=file_id, user=request.user)

        if not original.filename.lower().endswith(".pdf"):
            return Response({"error": "Only PDF allowed"}, status=400)

        filename = f"{uuid.uuid4()}.docx"
        output_path = os.path.join(settings.MEDIA_ROOT, "uploads", filename)

        try:
            pdf_to_word(original.file.path, output_path)

            with open(output_path, "rb") as f:
                converted = File.objects.create(
                    user=request.user,
                    file=DjangoFile(f, name=filename),
                    filename=filename,
                )

            return Response(
                FileSerializer(converted, context={"request": request}).data
            )

        except Exception as e:
            print("PDF→WORD ERROR:", e)
            return Response({"error": str(e)}, status=500)


# ==============================
# ➕ MERGE PDFs
# ==============================
class MergePDFView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        ids = request.data.get("file_ids", [])
        if len(ids) < 2:
            return Response({"error": "Select at least 2 PDFs"}, status=400)

        files = File.objects.filter(id__in=ids, user=request.user)

        tmp = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
        tmp.close()

        merge_pdfs([f.file.path for f in files], tmp.name)

        return FileResponse(
            open(tmp.name, "rb"),
            as_attachment=True,
            filename="merged.pdf",
        )


# ==============================
# ✂ SPLIT PDF
# ==============================
class SplitPDFView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, file_id):
        obj = get_object_or_404(File, id=file_id, user=request.user)

        tmpdir = tempfile.mkdtemp()
        output_files = split_pdf(obj.file.path, tmpdir)

        zip_path = os.path.join(tmpdir, "split_pages.zip")
        with zipfile.ZipFile(zip_path, "w") as z:
            for p in output_files:
                z.write(p, arcname=os.path.basename(p))

        return FileResponse(
            open(zip_path, "rb"),
            as_attachment=True,
            filename="split_pages.zip",
        )


# ==============================
# ✍ SIGN PDF
# ==============================
class SignPDFView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, file_id):
        signer = request.data.get("signer", "Signed User")
        obj = get_object_or_404(File, id=file_id, user=request.user)

        tmp = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
        tmp.close()

        sign_pdf(obj.file.path, tmp.name, signer)

        return FileResponse(
            open(tmp.name, "rb"),
            as_attachment=True,
            filename="signed.pdf",
        )


# ==============================
# 🌍 PUBLIC DOWNLOAD
# ==============================
class PublicDownloadView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, token):
        obj = get_object_or_404(File, public_token=token)

        return FileResponse(
            obj.file.open("rb"),
            as_attachment=True,
            filename=obj.filename,
        )
