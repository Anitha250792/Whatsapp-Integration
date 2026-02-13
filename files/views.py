import os
import uuid
import zipfile
import tempfile
import shutil

from django.http import FileResponse, Http404, HttpResponse
from django.core.files import File as DjangoFile
from django.shortcuts import get_object_or_404
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt

from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework.generics import ListAPIView

from .models import File
from .serializers import FileSerializer
from .converters import merge_pdfs, split_pdf
from .pdf_utils import sign_pdf

from django.utils import timezone
from uuid import UUID
from files.whatsapp_utils import try_send_whatsapp



CELERY_ENABLED = getattr(settings, "CELERY_ENABLED", False)

if CELERY_ENABLED:
    from files.tasks import word_to_pdf_task, pdf_to_word_task
# =====================================================
# ⚙ CONFIG
# =====================================================
UPLOAD_DIR = os.path.join(settings.MEDIA_ROOT, "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

MAX_FILE_MB = 10
MAX_FILE_BYTES = MAX_FILE_MB * 1024 * 1024

@csrf_exempt
def whatsapp_incoming(request):
    """
    Webhook called by Twilio when user replies on WhatsApp.
    This opens the 24-hour WhatsApp window.
    """
    from_number = request.POST.get("From", "")
    from_number = from_number.replace("whatsapp:", "")

    try:
        profile = request.user.userprofile  # fallback
    except Exception:
        from accounts.models import UserProfile
        try:
            profile = UserProfile.objects.get(
                whatsapp_number=from_number
            )
        except UserProfile.DoesNotExist:
            return HttpResponse("OK")

    profile.last_whatsapp_interaction = timezone.now()
    profile.save(update_fields=["last_whatsapp_interaction"])

    return HttpResponse("OK")

class SendFileToWhatsAppView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, file_id):
        file = get_object_or_404(File, id=file_id, user=request.user)
        profile = getattr(request.user, "userprofile", None)

        if (
            profile
            and profile.whatsapp_enabled
            and profile.can_send_whatsapp()
        ):
            public_url = request.build_absolute_uri(
                f"/files/public/{file.public_token}/"
            )

            try_send_whatsapp(
                request.user,
                request,
                file,
                "📄 File ready",
             )

        return Response({"message": "WhatsApp attempted"}, status=200)




# =====================================================
# 📂 LIST FILES
# =====================================================
class FileListView(ListAPIView):
    serializer_class = FileSerializer
    permission_classes = [] if settings.DEV_BYPASS_LOGIN else [IsAuthenticated]

    def get_queryset(self):
        if settings.DEV_BYPASS_LOGIN:
            return File.objects.all().order_by("-id")
        return File.objects.filter(user=self.request.user).order_by("-id")

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
# ⬇ DOWNLOAD
# =====================================================
class DownloadFileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, file_id):
        obj = get_object_or_404(File, id=file_id, user=request.user)

        if not obj.file or not os.path.exists(obj.file.path):
            raise Http404("File not found")

        return FileResponse(obj.file.open("rb"), as_attachment=True, filename=obj.filename)


# =====================================================
# 🔁 WORD → PDF (ASYNC)
# =====================================================
  
class WordToPDFView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, file_id):
        # 1️⃣ Server capability check
        if not settings.LOCAL_CONVERSION:
            return Response(
                {"error": "Word → PDF not supported on this server"},
                status=501,
            )

        # 2️⃣ Get original file
        original_file = get_object_or_404(
            File, id=file_id, user=request.user
        )

        # 3️⃣ Convert Word → PDF
        from docx2pdf import convert

        output_name = f"{uuid.uuid4()}.pdf"
        output_path = os.path.join(
            settings.MEDIA_ROOT, "uploads", output_name
        )

        convert(original_file.file.path, output_path)

        # 4️⃣ Save converted file to DB
        with open(output_path, "rb") as f:
            new_file = File.objects.create(
                user=request.user,
                file=DjangoFile(f, name=output_name),
                filename=output_name,
            )

        # 5️⃣ Build public URL (IMPORTANT for WhatsApp)
        public_url = request.build_absolute_uri(
            f"/files/public/{new_file.public_token}/"
        )

        # 6️⃣ WhatsApp send (SAFE, NON-BLOCKING)
        try_send_whatsapp(
            request.user,
            request,
            new_file,
            "✅ Word → PDF completed",
         )


        # 7️⃣ API response
        return Response(
            FileSerializer(
                new_file, context={"request": request}
            ).data,
            status=201,
        )

       
# =====================================================
# 🔁 PDF → WORD (ASYNC)
# =====================================================
class PDFToWordView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, file_id):
        return Response(
            {
                "error": "PDF → Word is disabled on this server. "
                         "This feature requires a background worker."
            },
            status=501,
        )

# =====================================================
# ➕ MERGE PDFs
# =====================================================
class MergePDFView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        ids = request.data.get("file_ids", [])
        files = File.objects.filter(id__in=ids, user=request.user)

        if files.count() < 2:
            return Response({"error": "Select at least 2 PDFs"}, status=400)

        names = [os.path.splitext(f.filename)[0] for f in files]
        filename = f"merged_{'_'.join(names[:2])}.pdf"
        output_path = os.path.join(settings.MEDIA_ROOT, "uploads", filename)

        merge_pdfs([f.file.path for f in files], output_path)

        with open(output_path, "rb") as f:
            new_file = File.objects.create(
                user=request.user,
                file=DjangoFile(f, name=filename),
                filename=filename,
            )

        public_url = request.build_absolute_uri(
            f"/files/public/{new_file.public_token}/"
        )

        try_send_whatsapp(
            request.user,
            request,
            new_file,
            "📄 PDFs merged successfully",
         )



        return Response(
            FileSerializer(new_file, context={"request": request}).data,
            status=201,
        )

# =====================================================
# ✂ SPLIT PDF
# =====================================================
class SplitPDFView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, file_id):
        # 1️⃣ Get original PDF
        original_file = get_object_or_404(
            File, id=file_id, user=request.user
        )

        tmpdir = tempfile.mkdtemp()
        base_name = os.path.splitext(original_file.filename)[0]

        try:
            # 2️⃣ Split PDF into pages
            pages = split_pdf(original_file.file.path, tmpdir)

            # 3️⃣ Create ZIP file
            zip_name = f"{base_name}_split.zip"
            zip_path = os.path.join(
                settings.MEDIA_ROOT, "uploads", zip_name
            )

            with zipfile.ZipFile(zip_path, "w") as zipf:
                for i, page_path in enumerate(pages, start=1):
                    zipf.write(
                        page_path,
                        arcname=f"{base_name}_page_{i}.pdf",
                    )

            # 4️⃣ Save ZIP to DB
            with open(zip_path, "rb") as f:
                zip_file = File.objects.create(
                    user=request.user,
                    file=DjangoFile(f, name=zip_name),
                    filename=zip_name,
                )

            # 5️⃣ Public URL for WhatsApp
            public_url = request.build_absolute_uri(
                f"/files/public/{zip_file.public_token}/"
            )

            # 6️⃣ WhatsApp send (SAFE)
            profile = getattr(request.user, "userprofile", None)

            if (
                profile
                and profile.whatsapp_enabled
                and profile.can_send_whatsapp()
            ):
                try_send_whatsapp(
                    request.user,
                    request,
                    zip_file,
                     "📄 PDF split completed",
)


            # 7️⃣ API response
            return Response(
                FileSerializer(
                    zip_file, context={"request": request}
                ).data,
                status=201,
            )

        finally:
            # 8️⃣ Always clean temp files
            shutil.rmtree(tmpdir, ignore_errors=True)


# =====================================================
# ✍ SIGN PDF (SAFE + STABLE)
# =====================================================
class SignPDFView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, file_id):
        # 1️⃣ Validate signer
        signer = request.data.get("signer", "").strip()
        if not signer:
            return Response(
                {"error": "Signer name required"},
                status=400,
            )

        # 2️⃣ Get original file
        original_file = get_object_or_404(
            File, id=file_id, user=request.user
        )

        # 3️⃣ Sign PDF
        base_name = os.path.splitext(original_file.filename)[0]
        output_name = f"{base_name}_signed.pdf"

        output_path = os.path.join(
            settings.MEDIA_ROOT, "uploads", output_name
        )

        sign_pdf(
            original_file.file.path,
            output_path,
            signer,
        )

        # 4️⃣ Save signed file
        with open(output_path, "rb") as f:
            new_file = File.objects.create(
                user=request.user,
                file=DjangoFile(f, name=output_name),
                filename=output_name,
            )

        # 5️⃣ Build public URL
        public_url = request.build_absolute_uri(
            f"/files/public/{new_file.public_token}/"
        )

        # 6️⃣ WhatsApp send (SAFE, NON-BLOCKING)
        profile = getattr(request.user, "userprofile", None)

        if (
            profile
            and profile.whatsapp_enabled
            and profile.can_send_whatsapp()
        ):
            try_send_whatsapp(
                request.user,
                request,
                new_file,
                "✍️ PDF signed successfully",
             )


        # 7️⃣ API response
        return Response(
            FileSerializer(
                new_file, context={"request": request}
            ).data,
            status=201,
        )
        

# =====================================================
# 🌍 PUBLIC DOWNLOAD
# =====================================================
class PublicDownloadView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, token):
        try:
            token = UUID(token)  # ✅ convert string → UUID
        except ValueError:
            raise Http404("Invalid token")

        try:
            obj = File.objects.get(public_token=token)
        except File.DoesNotExist:
            raise Http404("File not found for this token")


        if not obj.file or not os.path.exists(obj.file.path):
            raise Http404("File not found")

        with open(obj.file.path, "rb") as f:
            response = HttpResponse(
                f.read(),
                content_type="application/octet-stream",
            )
            response["Content-Disposition"] = f'attachment; filename="{obj.filename}"'
            return response
        
@csrf_exempt
def whatsapp_status_callback(request):
    """
    Twilio webhook for WhatsApp delivery status
    """
    sid = request.POST.get("MessageSid")
    status = request.POST.get("MessageStatus")
    error_code = request.POST.get("ErrorCode")
    error_message = request.POST.get("ErrorMessage")

    print("📊 WhatsApp Status Update")
    print("SID:", sid)
    print("STATUS:", status)

    if error_code:
        print("❌ Error Code:", error_code)
        print("❌ Error Message:", error_message)

    if not sid:
        return HttpResponse("No SID", status=400)

    try:
        file = File.objects.filter(
            whatsapp_message_sid=sid
        ).first()

        if file:
            file.whatsapp_status = status
            file.save(update_fields=["whatsapp_status"])

    except Exception as e:
        print("❌ Status update failed:", e)

    return HttpResponse("OK")
