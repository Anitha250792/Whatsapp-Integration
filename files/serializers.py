# files/serializers.py
from rest_framework import serializers
from django.urls import reverse
from .models import File


class FileSerializer(serializers.ModelSerializer):
    download_url = serializers.SerializerMethodField()

    class Meta:
        model = File
        fields = ["id", "filename", "download_url"]

    def get_download_url(self, obj):
        request = self.context.get("request")
        if request is None:
            return None

        return request.build_absolute_uri(
            reverse("file-download", args=[obj.id])
        )
