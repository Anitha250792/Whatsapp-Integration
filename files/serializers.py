# files/serializers.py
from rest_framework import serializers
from django.urls import reverse
from .models import File


# files/serializers.py
class FileSerializer(serializers.ModelSerializer):
    public_url = serializers.SerializerMethodField()

    class Meta:
        model = File
        fields = ["id", "filename", "public_url"]

    def get_public_url(self, obj):
        request = self.context.get("request")
        if not request:
            return None
        return request.build_absolute_uri(
            reverse("file-public", args=[obj.public_token])
        )

