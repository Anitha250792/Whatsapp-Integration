from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser
from django.shortcuts import get_object_or_404
from django.conf import settings
import os

from .models import File
from .serializers import FileSerializer
from .converters import (
    word_to_pdf, pdf_to_word,
    sign_pdf, merge_pdfs, split_pdf
)


# 📂 List uploaded files
class FileListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        files = File.objects.filter(user=request.user).order_by("-id")
        serializer = FileSerializer(files, many=True)
        return Response(serializer.data)
    

class DeleteFileView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, file_id):
        file_obj = get_object_or_404(File, id=file_id, user=request.user)

        # delete file from storage
        file_obj.file.delete(save=False)

        # delete db record
        file_obj.delete()

        return Response({"message": "File deleted successfully"})


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
                filename=f.name
            )
            saved.append(FileSerializer(obj).data)

        return Response(saved, status=201)


# 📊 Dashboard health check (optional)
class DownloadFileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, file_id):
        file_obj = get_object_or_404(File, id=file_id, user=request.user)
        return Response({"url": file_obj.file.url})


# 🔁 Word ➜ PDF
class WordToPDFView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, file_id):
        file_obj = get_object_or_404(File, id=file_id, user=request.user)
        out = os.path.join(settings.MEDIA_ROOT, f"{file_id}.pdf")
        word_to_pdf(file_obj.file.path, out)
        return Response({"pdf_url": settings.MEDIA_URL + f"{file_id}.pdf"})


# 🔁 PDF ➜ Word
class PDFToWordView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, file_id):
        file_obj = get_object_or_404(File, id=file_id, user=request.user)
        out = os.path.join(settings.MEDIA_ROOT, f"{file_id}.docx")
        pdf_to_word(file_obj.file.path, out)
        return Response({"docx_url": settings.MEDIA_URL + f"{file_id}.docx"})

class MergePDFView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        ids = request.data.get("file_ids", [])
        files = File.objects.filter(id__in=ids, user=request.user)

        paths = [f.file.path for f in files]
        out = os.path.join(settings.MEDIA_ROOT, "merged.pdf")
        merge_pdfs(paths, out)

        return Response({"merged_pdf": settings.MEDIA_URL + "merged.pdf"})


class SplitPDFView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, file_id):
        file_obj = get_object_or_404(File, id=file_id, user=request.user)
        output_dir = settings.MEDIA_ROOT
        split_pdf(file_obj.file.path, output_dir)

        return Response({"message": "PDF split successfully"})


class SignPDFView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, file_id):
        signer = request.data.get("signer", "Signed User")
        file_obj = get_object_or_404(File, id=file_id, user=request.user)

        out = os.path.join(settings.MEDIA_ROOT, f"{file_id}_signed.pdf")
        sign_pdf(file_obj.file.path, out, signer)

        return Response({"signed_pdf": settings.MEDIA_URL + f"{file_id}_signed.pdf"})
