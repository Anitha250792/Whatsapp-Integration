from django.urls import path
from .views import UploadFileView
from .views import DashboardView

urlpatterns = [
    path("upload/", UploadFileView.as_view()),
    path("dashboard/", DashboardView.as_view(), name="dashboard"),
]
