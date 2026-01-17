# files/views.py
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


class FileListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        files = File.objects.filter(user=request.user).order_by("-id")
        return Response(FileSerializer(files, many=True).data)


class UploadFileView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser]

    def post(self, request):
        uploaded = request.FILES.get("file")
        obj = File.objects.create(
            user=request.user,
            file=uploaded,
            filename=uploaded.name
        )
        return Response(FileSerializer(obj).data, status=201)


class DeleteFileView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, file_id):
        file_obj = get_object_or_404(File, id=file_id, user=request.user)
        file_obj.file.delete(save=False)
        file_obj.delete()
        return Response({"message": "Deleted"})


class WordToPDFView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, file_id):
        file_obj = get_object_or_404(File, id=file_id, user=request.user)

        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
        word_to_pdf(file_obj.file.path, tmp.name)

        return FileResponse(
            open(tmp.name, "rb"),
            as_attachment=True,
            filename="converted.pdf"
        )


class PDFToWordView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, file_id):
        file_obj = get_object_or_404(File, id=file_id, user=request.user)

        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".docx")
        pdf_to_word(file_obj.file.path, tmp.name)

        return FileResponse(
            open(tmp.name, "rb"),
            as_attachment=True,
            filename="converted.docx"
        )


class MergePDFView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        ids = request.data.get("file_ids", [])
        files = File.objects.filter(id__in=ids, user=request.user)

        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
        merge_pdfs([f.file.path for f in files], tmp.name)

        return FileResponse(
            open(tmp.name, "rb"),
            as_attachment=True,
            filename="merged.pdf"
        )


class SplitPDFView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, file_id):
        file_obj = get_object_or_404(File, id=file_id, user=request.user)

        with tempfile.TemporaryDirectory() as tmpdir:
            split_pdf(file_obj.file.path, tmpdir)

            zip_path = os.path.join(tmpdir, "split_pages.zip")
            with zipfile.ZipFile(zip_path, "w") as zipf:
                for f in os.listdir(tmpdir):
                    zipf.write(os.path.join(tmpdir, f), f)

            return FileResponse(
                open(zip_path, "rb"),
                as_attachment=True,
                filename="split_pages.zip"
            )


class SignPDFView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, file_id):
        signer = request.GET.get("signer", "Signed User")
        file_obj = get_object_or_404(File, id=file_id, user=request.user)

        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
        sign_pdf(file_obj.file.path, tmp.name, signer)

        return FileResponse(
            open(tmp.name, "rb"),
            as_attachment=True,
            filename="signed.pdf"
        )
