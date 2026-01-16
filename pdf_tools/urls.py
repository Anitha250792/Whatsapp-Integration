from django.urls import path
from .views import ShareFileView, ConvertPDFView

urlpatterns = [
    path("convert/", ConvertPDFView.as_view()),
    path("share/<int:file_id>/", ShareFileView.as_view()),
]
