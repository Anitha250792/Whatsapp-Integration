from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import UploadedFile
from django.conf import settings
from .converters import pdf_to_word, word_to_pdf

import os

class FileUploadView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        for f in request.FILES.getlist("files"):
            UploadedFile.objects.create(user=request.user, file=f)
        return Response({"message": "Uploaded"})

class FileListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        files = UploadedFile.objects.filter(user=request.user)
        data = [{
            "id": f.id,
            "file": f.file.url,
            "filename": f.filename
        } for f in files]
        return Response(data)

class WordToPDFView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, file_id):
        file_obj = UploadedFile.objects.get(id=file_id, user=request.user)

        word_path = file_obj.file.path
        pdf_name = file_obj.filename.replace(".docx", ".pdf")
        pdf_path = os.path.join(settings.MEDIA_ROOT, pdf_name)

        word_to_pdf(word_path, pdf_path)

        return Response({
            "pdf_url": settings.MEDIA_URL + pdf_name
        })
    
class PDFToWordView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, file_id):
        file_obj = UploadedFile.objects.get(id=file_id, user=request.user)

        pdf_path = file_obj.file.path
        docx_name = file_obj.filename.replace(".pdf", ".docx")
        docx_path = os.path.join(settings.MEDIA_ROOT, docx_name)

        pdf_to_word(pdf_path, docx_path)

        return Response({
            "docx_url": settings.MEDIA_URL + docx_name
        })    