from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework import status
import tempfile, os, zipfile

from .models import File
from .serializers import FileSerializer
from .converters import (
    word_to_pdf,
    pdf_to_word,
    merge_pdfs,
    split_pdf,
    sign_pdf,
)
import mimetypes

# 📂 List files
class FileListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        files = File.objects.filter(user=request.user).order_by("-id")
        serializer = FileSerializer(
            files,
            many=True,
            context={"request": request}
        )
        return Response(serializer.data)

# ⬆ Upload
class UploadFileView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]   # 🔥 REQUIRED

    def post(self, request):
        file = request.FILES.get("file")

        if not file:
            return Response({"error": "No file uploaded"}, status=400)

        uploaded = File.objects.create(
            user=request.user,
            file=file,
            filename=file.name
        )

        return Response({
            "id": uploaded.id,
            "filename": uploaded.filename,
        }, status=201)


# ❌ Delete
class DeleteFileView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, file_id):
        obj = get_object_or_404(File, id=file_id, user=request.user)
        obj.file.delete()
        obj.delete()
        return Response({"message": "Deleted"})


# ⬇ Download
class DownloadFileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, file_id):
        obj = get_object_or_404(File, id=file_id, user=request.user)

        file_path = obj.file.path
        if not os.path.exists(file_path):
            raise Http404("File not found")

        content_type, _ = mimetypes.guess_type(file_path)
        content_type = content_type or "application/octet-stream"

        response = FileResponse(
            open(file_path, "rb"),
            content_type=content_type,
        )

        # 🔥 CRITICAL for WhatsApp
        response["Content-Disposition"] = f'attachment; filename="{obj.filename}"'
        response["X-Content-Type-Options"] = "nosniff"

        return response


# 🔁 Word → PDF
class WordToPDFView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, file_id):
        obj = get_object_or_404(File, id=file_id, user=request.user)
        tmp = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
        word_to_pdf(obj.file.path, tmp.name)
        return FileResponse(open(tmp.name, "rb"), as_attachment=True)


# 🔁 PDF → Word
class PDFToWordView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, file_id):
        file_obj = get_object_or_404(File, id=file_id, user=request.user)

        try:
            with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as tmp:
                pdf_to_word(file_obj.file.path, tmp.name)
                return FileResponse(
                    open(tmp.name, "rb"),
                    as_attachment=True,
                    filename="converted.docx"
                )
        except ValueError:
            return Response(
                {"error": "Scanned PDFs need OCR"},
                status=status.HTTP_400_BAD_REQUEST
            )


# ➕ Merge
class MergePDFView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        ids = request.data.get("file_ids", [])
        files = File.objects.filter(id__in=ids, user=request.user)

        tmp = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
        merge_pdfs([f.file.path for f in files], tmp.name)
        return FileResponse(open(tmp.name, "rb"), as_attachment=True)


# ✂ Split
class SplitPDFView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, file_id):
        obj = get_object_or_404(File, id=file_id, user=request.user)
        tmpdir = tempfile.mkdtemp()
        split_pdf(obj.file.path, tmpdir)

        zip_path = os.path.join(tmpdir, "split.zip")
        with zipfile.ZipFile(zip_path, "w") as z:
            for f in os.listdir(tmpdir):
                if f.endswith(".pdf"):
                    z.write(os.path.join(tmpdir, f), f)

        return FileResponse(open(zip_path, "rb"), as_attachment=True)


# ✍ Sign
class SignPDFView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, file_id):
        signer = request.data.get("signer", "Signed User")
        obj = get_object_or_404(File, id=file_id, user=request.user)
        tmp = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
        sign_pdf(obj.file.path, tmp.name, signer)
        return FileResponse(open(tmp.name, "rb"), as_attachment=True)

# views.py
class PublicDownloadFileView(APIView):
    permission_classes = []

    def get(self, request, token):
        obj = get_object_or_404(File, public_token=token)
        return FileResponse(
            obj.file.open("rb"),
            as_attachment=True,
            filename=obj.filename,
        )

