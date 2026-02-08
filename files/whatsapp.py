from twilio.rest import Client
from django.conf import settings

def send_whatsapp_message(to_number: str, message: str):
    """
    Sends WhatsApp message via Twilio
    """
    if not to_number:
        return

    client = Client(
        settings.TWILIO_ACCOUNT_SID,
        settings.TWILIO_AUTH_TOKEN,
    )

    client.messages.create(
        from_=settings.TWILIO_WHATSAPP_FROM,
        to=f"whatsapp:{to_number.replace('whatsapp:', '')}",
        body=message,
    )
