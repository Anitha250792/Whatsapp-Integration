from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    whatsapp_number = models.CharField(max_length=15, blank=True)
    whatsapp_enabled = models.BooleanField(default=True)

    daily_whatsapp_count = models.PositiveIntegerField(default=0)
    last_whatsapp_date = models.DateField(null=True, blank=True)

    DAILY_LIMIT = 5  # free plan

    def can_send_whatsapp(self):
        today = timezone.now().date()

        if self.last_whatsapp_date != today:
            self.daily_whatsapp_count = 0
            self.last_whatsapp_date = today
            self.save()

        return self.daily_whatsapp_count < self.DAILY_LIMIT

    def increment_whatsapp(self):
        self.daily_whatsapp_count += 1
        self.save()

    def __str__(self):
        return self.user.username
