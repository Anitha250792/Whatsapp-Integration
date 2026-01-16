from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import UploadedFile

class UploadFileView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        file = request.FILES.get("file")

        UploadedFile.objects.create(
            user=request.user,
            file=file,
            original_name=file.name
        )

        return Response({"message": "File uploaded successfully"})
    
class DashboardView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({
            "message": f"Welcome {request.user.email}"
        })    
