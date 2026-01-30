from django.db import models
from django.contrib.auth.models import User
import uuid


class File(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    file = models.FileField(upload_to="uploads/")
    filename = models.CharField(max_length=255)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    public_token = models.UUIDField(default=uuid.uuid4, unique=True)

    def __str__(self):
        return self.filename