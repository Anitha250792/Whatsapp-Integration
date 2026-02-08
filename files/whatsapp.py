from twilio.rest import Client
from django.conf import settings

def send_whatsapp_message(to_number: str, message: str, media_url: str | None = None):
    if not to_number:
        return

    client = Client(
        settings.TWILIO_ACCOUNT_SID,
        settings.TWILIO_AUTH_TOKEN,
    )

    kwargs = {
        "from_": settings.TWILIO_WHATSAPP_FROM,
        "to": f"whatsapp:{to_number.replace('whatsapp:', '')}",
        "body": message,
    }

    # ✅ THIS IS THE KEY
    if media_url:
        kwargs["media_url"] = [media_url]

    client.messages.create(**kwargs)
