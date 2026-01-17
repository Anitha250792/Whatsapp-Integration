from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from django.shortcuts import get_object_or_404
from django.conf import settings
import os

from .models import File
from .serializers import FileSerializer
from .converters import pdf_to_word, word_to_pdf


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
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        uploaded_file = request.FILES.get("file")
        if not uploaded_file:
            return Response({"error": "No file provided"}, status=400)

        file_obj = File.objects.create(
            user=request.user,
            file=uploaded_file,
            filename=uploaded_file.name,
        )

        return Response(FileSerializer(file_obj).data, status=201)


# 📊 Dashboard health check (optional)
class DashboardView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({"message": "Dashboard API working"})


# 🔁 Word ➜ PDF
class WordToPDFView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, file_id):
        file_obj = get_object_or_404(File, id=file_id, user=request.user)

        input_path = file_obj.file.path
        output_path = os.path.join(
            settings.MEDIA_ROOT, f"{file_obj.id}_converted.pdf"
        )

        word_to_pdf(input_path, output_path)

        return Response({
            "pdf_url": settings.MEDIA_URL + os.path.basename(output_path)
        })


# 🔁 PDF ➜ Word
class PDFToWordView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, file_id):
        file_obj = get_object_or_404(File, id=file_id, user=request.user)

        input_path = file_obj.file.path
        output_path = os.path.join(
            settings.MEDIA_ROOT, f"{file_obj.id}_converted.docx"
        )

        pdf_to_word(input_path, output_path)

        return Response({
            "docx_url": settings.MEDIA_URL + os.path.basename(output_path)
        })
