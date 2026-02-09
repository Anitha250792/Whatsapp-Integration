from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    whatsapp_number = models.CharField(max_length=20, blank=True)
    whatsapp_enabled = models.BooleanField(default=False)

    last_whatsapp_interaction = models.DateTimeField(null=True, blank=True)
    whatsapp_count = models.PositiveIntegerField(default=0)

    def can_send_whatsapp(self):
        return self.whatsapp_count < 100  # or your limit

    def increment_whatsapp(self):
        self.whatsapp_count += 1
        self.save(update_fields=["whatsapp_count"])

    def within_24h_window(self):
        if not self.last_whatsapp_interaction:
            return False
        return timezone.now() - self.last_whatsapp_interaction < timezone.timedelta(hours=24)
