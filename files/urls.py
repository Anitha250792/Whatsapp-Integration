from django.urls import path
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
)


urlpatterns = [
    path("", FileListView.as_view()),
    path("upload/", UploadFileView.as_view()),
    path("download/<int:file_id>/", DownloadFileView.as_view()),
    path("delete/<int:file_id>/", DeleteFileView.as_view()),

    path("convert/word-to-pdf/<int:file_id>/", WordToPDFView.as_view()),
    path("convert/pdf-to-word/<int:file_id>/", PDFToWordView.as_view()),

    path("merge/", MergePDFView.as_view()),
    path("split/<int:file_id>/", SplitPDFView.as_view()),
    path("sign/<int:file_id>/", SignPDFView.as_view()),
    
]
