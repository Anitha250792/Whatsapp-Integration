# accounts/models.py
from django.db import models
from django.contrib.auth.models import User

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    whatsapp_number = models.CharField(max_length=15)

    def __str__(self):
        return f"{self.user.username} - {self.whatsapp_number}"
