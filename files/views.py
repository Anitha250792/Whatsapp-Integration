import os
import uuid
import zipfile
import tempfile
import shutil

from django.http import FileResponse, Http404
from django.core.files import File as DjangoFile
from django.shortcuts import get_object_or_404
from django.conf import settings

from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework.generics import ListAPIView

from .models import File
from .serializers import FileSerializer
from .converters import merge_pdfs, split_pdf
from .pdf_utils import sign_pdf
from accounts.utils import send_whatsapp_if_allowed
from django.utils import timezone



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


class SendFileToWhatsAppView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, file_id):
        file = get_object_or_404(File, id=file_id, user=request.user)

        send_whatsapp_if_allowed(
            request.user,
            f"📄 File ready\n{file.public_url}"
        )

        return Response({"message": "File sent to WhatsApp"})

# =====================================================
# 🔔 WHATSAPP SAFETY (OPTIONAL – NEVER BLOCKS CORE)
# =====================================================
def enforce_whatsapp_rules(request):
    profile = getattr(request.user, "userprofile", None)
    if not profile or not profile.whatsapp_enabled or not profile.whatsapp_number:
        return False

    today = timezone.now().date()
    if profile.last_whatsapp_date != today:
        profile.daily_whatsapp_count = 0
        profile.last_whatsapp_date = today
        profile.save(update_fields=["daily_whatsapp_count", "last_whatsapp_date"])

    return profile.daily_whatsapp_count < 5


def mark_whatsapp_sent(profile):
    profile.daily_whatsapp_count += 1
    profile.save(update_fields=["daily_whatsapp_count"])


class WhatsAppMixin:
    def send_whatsapp(self, request, file_obj, title):
        profile = getattr(request.user, "userprofile", None)
        if not profile or not enforce_whatsapp_rules(request):
            return

        public_url = request.build_absolute_uri(
            f"/files/public/{file_obj.public_token}/"
        )

        send_whatsapp_message(
            profile.whatsapp_number,
            f"{title}\n{public_url}",
        )

        mark_whatsapp_sent(profile)


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
        if not settings.LOCAL_CONVERSION:
            return Response(
                {"error": "Word → PDF not supported on this server"},
                status=501
            )
        

        file = get_object_or_404(File, id=file_id, user=request.user)

        from docx2pdf import convert
        output_name = f"{uuid.uuid4()}.pdf"
        output_path = os.path.join(settings.MEDIA_ROOT, "uploads", output_name)

        convert(file.file.path, output_path)

        with open(output_path, "rb") as f:
            new_file = File.objects.create(
                user=request.user,
                file=DjangoFile(f, name=output_name),
                filename=output_name,
            )

        send_whatsapp_if_allowed(
            request.user,
            f"📄 Word → PDF ready\n{new_file.public_url}"
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

        send_whatsapp_if_allowed(
            request.user,
            f"📄 PDFs merged successfully\n{new_file.public_url}"
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
        obj = get_object_or_404(File, id=file_id, user=request.user)
        tmpdir = tempfile.mkdtemp()
        base = os.path.splitext(obj.filename)[0]

        try:
            pages = split_pdf(obj.file.path, tmpdir)
            zip_name = f"{base}_split.zip"
            zip_path = os.path.join(settings.MEDIA_ROOT, "uploads", zip_name)

            with zipfile.ZipFile(zip_path, "w") as zipf:
                for i, page in enumerate(pages, start=1):
                    zipf.write(page, arcname=f"{base}_page_{i}.pdf")

            with open(zip_path, "rb") as f:
                zip_file = File.objects.create(
                    user=request.user,
                    file=DjangoFile(f, name=zip_name),
                    filename=zip_name,
                )

            send_whatsapp_if_allowed(
                request.user,
                f"📄 PDF split completed\n{zip_file.public_url}"
            )

            return Response(
                FileSerializer(zip_file, context={"request": request}).data,
                status=201,
            )
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)


# =====================================================
# ✍ SIGN PDF (SAFE + STABLE)
# =====================================================
class SignPDFView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, file_id):
        signer = request.data.get("signer", "").strip()
        if not signer:
            return Response({"error": "Signer name required"}, status=400)

        original = get_object_or_404(File, id=file_id, user=request.user)

        output_name = f"signed_{uuid.uuid4()}.pdf"
        output_path = os.path.join(settings.MEDIA_ROOT, "uploads", output_name)

        sign_pdf(original.file.path, output_path, signer)

        with open(output_path, "rb") as f:
            new_file = File.objects.create(
                user=request.user,
                file=DjangoFile(f, name=output_name),
                filename=output_name,
            )

        send_whatsapp_if_allowed(
            request.user,
            f"✍️ PDF signed successfully\n{new_file.public_url}"
        )

        return Response(
            FileSerializer(new_file, context={"request": request}).data,
            status=201,
        )




        # ================= WHATSAPP (NON-BLOCKING) =================
        try:
            profile = getattr(request.user, "userprofile", None)

            if (
                profile
                and profile.whatsapp_enabled
                and profile.can_send_whatsapp()
            ):
                public_url = request.build_absolute_uri(
                    f"/files/public/{new_file.public_token}/"
                )

                send_whatsapp_message(
                    profile.whatsapp_number,
                    f"📄 Signed file ready\n{public_url}",
                )

                profile.increment_whatsapp()

        except Exception as e:
            # ⚠ WhatsApp should NEVER break signing
            print("⚠ WhatsApp failed:", e)

        return Response(
            {
                "message": "PDF signed successfully",
                "file": FileSerializer(new_file, context={"request": request}).data,
            },
            status=201,
        )



# =====================================================
# 🌍 PUBLIC DOWNLOAD
# =====================================================
class PublicDownloadView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, token):
        obj = get_object_or_404(File, public_token=token)

        if not obj.file or not os.path.exists(obj.file.path):
            raise Http404("File not found")

        return FileResponse(
            obj.file.open("rb"),
            as_attachment=True,
            filename=obj.filename
        )
    
