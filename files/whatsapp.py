from django.conf import settings
from twilio.rest import Client


def send_whatsapp_message(to, body, media_url=None):
    # ✅ Check Twilio config
    if not all([
        getattr(settings, "TWILIO_ACCOUNT_SID", None),
        getattr(settings, "TWILIO_AUTH_TOKEN", None),
        getattr(settings, "TWILIO_WHATSAPP_FROM", None),
    ]):
        print("⚠️ Twilio not configured, skipping WhatsApp")
        return False

    try:
        client = Client(
            settings.TWILIO_ACCOUNT_SID,
            settings.TWILIO_AUTH_TOKEN
        )

        message = client.messages.create(
            from_=settings.TWILIO_WHATSAPP_FROM,
            to=f"whatsapp:{to}" if not to.startswith("whatsapp:") else to,
            body=body,
            media_url=[media_url] if media_url else None,
        )

        # ✅ IMPORTANT LOGS
        print("📨 WhatsApp SID:", message.sid)
        print("📊 WhatsApp STATUS:", message.status)

        return True

    except Exception as e:
        print("❌ WhatsApp failed:", str(e))
        return False
