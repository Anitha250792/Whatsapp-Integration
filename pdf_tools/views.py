import os
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from files.models import UploadedFile

from .utils.merge_pdf import merge_pdfs
from .utils.split_pdf import split_pdf
from .utils.sign_pdf import sign_pdf
from .utils.word_to_pdf import word_to_pdf
from .utils.pdf_to_word import pdf_to_word


class ConvertPDFView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        action = request.data.get("action")

        output_dir = os.path.join(settings.MEDIA_ROOT, "outputs")
        os.makedirs(output_dir, exist_ok=True)

        # 🔹 MERGE PDF
        if action == "merge":
            files = request.FILES.getlist("files")

            if len(files) < 2:
                return Response({"error": "At least two PDFs required"}, status=400)

            output_path = os.path.join(output_dir, "merged.pdf")
            merge_pdfs(files, output_path)

            return Response({
                "message": "PDF merged successfully",
                "file_url": request.build_absolute_uri(
                    settings.MEDIA_URL + "outputs/merged.pdf"
                )
            })

        # 🔹 SPLIT PDF
        if action == "split":
            file = request.FILES.get("file")

            split_pdf(file, output_dir)

            return Response({"message": "PDF split successfully"})

        # 🔹 SIGN PDF
        if action == "sign":
            file = request.FILES.get("file")

            output_path = os.path.join(output_dir, "signed.pdf")
            sign_pdf(output_path)

            return Response({
                "message": "PDF signed successfully",
                "file_url": request.build_absolute_uri(
                    settings.MEDIA_URL + "outputs/signed.pdf"
                )
            })

        # 🔹 WORD → PDF
        if action == "word_to_pdf":
            file = request.FILES.get("file")

            output_path = os.path.join(output_dir, "converted.pdf")
            word_to_pdf(file, output_path)

            return Response({
                "message": "Word converted to PDF",
                "file_url": request.build_absolute_uri(
                    settings.MEDIA_URL + "outputs/converted.pdf"
                )
            })

        # 🔹 PDF → WORD
        if action == "pdf_to_word":
            file = request.FILES.get("file")

            output_path = os.path.join(output_dir, "converted.docx")
            pdf_to_word(file, output_path)

            return Response({
                "message": "PDF converted to Word",
                "file_url": request.build_absolute_uri(
                    settings.MEDIA_URL + "outputs/converted.docx"
                )
            })

        return Response({"error": "Invalid action"}, status=400)


class ShareFileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, file_id):
        obj = get_object_or_404(File, id=file_id, user=request.user)

        public_url = request.build_absolute_uri(
            f"/api/files/public/{obj.public_token}/"
        )

        return Response({
            "filename": obj.filename,
            "download_url": public_url,
            "whatsapp_url": (
                "https://wa.me/?text="
                f"Download%20file:%20{public_url}"
            )
        })

