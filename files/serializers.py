# files/serializers.py
from rest_framework import serializers
from django.urls import reverse
from .models import File


class FileSerializer(serializers.ModelSerializer):
    download_url = serializers.SerializerMethodField()
    public_url = serializers.SerializerMethodField()

    class Meta:
        model = File
        fields = [
            "id",
            "filename",
            "download_url",  # 🔐 authenticated download
            "public_url",    # 🌍 WhatsApp share link
        ]

    def get_download_url(self, obj):
        request = self.context.get("request")
        if request is None:
            return None

        url = reverse("file-download", args=[obj.id])
        return request.build_absolute_uri(url)

    def get_public_url(self, obj):
        request = self.context.get("request")
        if request is None:
            return None

        url = reverse("file-public", args=[obj.public_token])
        return request.build_absolute_uri(url)
