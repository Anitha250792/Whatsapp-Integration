from django.urls import path, include
from .views import (
    FileListView,
    UploadFileView,
    DownloadFileView,
    DeleteFileView,
    WordToPDFView,
    PDFToWordView,
    MergePDFView,
    SplitPDFView,
    SignPDFView,
    PublicDownloadView,
    SendFileToWhatsAppView,
    whatsapp_incoming,
)
from .views import whatsapp_status_callback


urlpatterns = [
    
    path("", FileListView.as_view()),
    path("upload/", UploadFileView.as_view()),
    path("download/<int:file_id>/", DownloadFileView.as_view(), name="file-download"),
    path("public/<str:token>/", PublicDownloadView.as_view(), name="file-public"),


    path("delete/<int:file_id>/", DeleteFileView.as_view()),

    path("convert/word-to-pdf/<int:file_id>/", WordToPDFView.as_view()),
    path("convert/pdf-to-word/<int:file_id>/", PDFToWordView.as_view()),
    path("merge/", MergePDFView.as_view()),
    path("split/<int:file_id>/", SplitPDFView.as_view()),
    path("sign/<int:file_id>/", SignPDFView.as_view()),
    path("send-whatsapp/<int:file_id>/", SendFileToWhatsAppView.as_view()),
    # files/urls.py
    path("webhooks/whatsapp/", whatsapp_incoming),
    path("webhooks/whatsapp-status/", whatsapp_status_callback),
  
    
]
