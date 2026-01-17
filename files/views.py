import os
import tempfile
import zipfile

from django.http import FileResponse
from django.shortcuts import get_object_or_404

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser

from .models import File
from .serializers import FileSerializer
from .converters import (
    word_to_pdf,
    pdf_to_word,
    merge_pdfs,
    split_pdf,
    sign_pdf,
)


# 📂 List uploaded files
class FileListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        files = File.objects.filter(user=request.user).order_by("-id")
        return Response(FileSerializer(files, many=True).data)


# ⬆ Upload file
class UploadFileView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser]

    def post(self, request):
        files = request.FILES.getlist("file")
        saved = []

        for f in files:
            obj = File.objects.create(
                user=request.user,
                file=f,
                filename=f.name,
            )
            saved.append(FileSerializer(obj).data)

        return Response(saved, status=201)


# ⬇ Download file (THIS MUST EXIST)
class DownloadFileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, file_id):
        file_obj = get_object_or_404(File, id=file_id, user=request.user)
        return FileResponse(
            open(file_obj.file.path, "rb"),
            as_attachment=True,
            filename=file_obj.filename,
        )


# ❌ Delete file
class DeleteFileView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, file_id):
        file_obj = get_object_or_404(File, id=file_id, user=request.user)
        file_obj.file.delete(save=False)
        file_obj.delete()
        return Response({"message": "File deleted"})


# 🔁 Word ➜ PDF
class WordToPDFView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, file_id):
        file_obj = get_object_or_404(File, id=file_id, user=request.user)

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            word_to_pdf(file_obj.file.path, tmp.name)
            return FileResponse(
                open(tmp.name, "rb"),
                as_attachment=True,
                filename="converted.pdf",
            )


# 🔁 PDF ➜ Word
class PDFToWordView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, file_id):
        file_obj = get_object_or_404(File, id=file_id, user=request.user)

        with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as tmp:
            pdf_to_word(file_obj.file.path, tmp.name)
            return FileResponse(
                open(tmp.name, "rb"),
                as_attachment=True,
                filename="converted.docx",
            )


# 📎 Merge PDFs
class MergePDFView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        ids = request.data.get("file_ids", [])
        files = File.objects.filter(id__in=ids, user=request.user)
        paths = [f.file.path for f in files]

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            merge_pdfs(paths, tmp.name)
            return FileResponse(
                open(tmp.name, "rb"),
                as_attachment=True,
                filename="merged.pdf",
            )


# ✂ Split PDF
class SplitPDFView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, file_id):
        file_obj = get_object_or_404(File, id=file_id, user=request.user)

        with tempfile.TemporaryDirectory() as tmpdir:
            split_pdf(file_obj.file.path, tmpdir)

            zip_path = os.path.join(tmpdir, "split_pages.zip")
            with zipfile.ZipFile(zip_path, "w") as zipf:
                for f in os.listdir(tmpdir):
                    if f.endswith(".pdf"):
                        zipf.write(os.path.join(tmpdir, f), f)

            return FileResponse(
                open(zip_path, "rb"),
                as_attachment=True,
                filename="split_pages.zip",
            )


# ✍ Sign PDF
class SignPDFView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, file_id):
        signer = request.data.get("signer", "Signed User")
        file_obj = get_object_or_404(File, id=file_id, user=request.user)

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            sign_pdf(file_obj.file.path, tmp.name, signer)
            return FileResponse(
                open(tmp.name, "rb"),
                as_attachment=True,
                filename="signed.pdf",
            )
