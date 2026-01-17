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
