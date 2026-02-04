# files/serializers.py
from rest_framework import serializers
from django.urls import reverse
from .models import File

class FileSerializer(serializers.ModelSerializer):
    public_url = serializers.SerializerMethodField()

    class Meta:
        model = File
        fields = ["id", "filename", "public_token", "public_url"]

    def get_public_url(self, obj):
        request = self.context.get("request")
        return request.build_absolute_uri(
            f"/files/public/{obj.public_token}/"
        )
