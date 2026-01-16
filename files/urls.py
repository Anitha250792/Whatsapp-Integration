from django.urls import path
from .views import UploadFileView
from .views import DashboardView
from .views import WordToPDFView
from .views import PDFToWordView

urlpatterns = [
    path("", FileListView.as_view()),
    path("upload/", UploadFileView.as_view()),
    path("dashboard/", DashboardView.as_view(), name="dashboard"),
    path("convert/word-to-pdf/<int:file_id>/", WordToPDFView.as_view()),
    path("convert/pdf-to-word/<int:file_id>/", PDFToWordView.as_view()),
]
