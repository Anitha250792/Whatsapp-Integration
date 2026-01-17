from django.urls import path
from .views import *

urlpatterns = [
    path("upload/", UploadFileView.as_view()),
    path("download/<int:file_id>/", DownloadFileView.as_view()),
    path("delete/<int:file_id>/", DeleteFileView.as_view()),

    path("convert/word-to-pdf/<int:file_id>/", WordToPDFView.as_view()),
    path("convert/pdf-to-word/<int:file_id>/", PDFToWordView.as_view()),
]
