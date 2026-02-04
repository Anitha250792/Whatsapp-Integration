# files/whatsapp.py
import requests
from django.conf import settings


def send_whatsapp_message(to_number, message_text):
    """
    Sends a WhatsApp message using Meta WhatsApp Cloud API
    """

    if not settings.WHATSAPP_ACCESS_TOKEN or not settings.WHATSAPP_PHONE_NUMBER_ID:
        raise ValueError("WhatsApp credentials are not configured")

    url = f"https://graph.facebook.com/v19.0/{settings.WHATSAPP_PHONE_NUMBER_ID}/messages"

    headers = {
        "Authorization": f"Bearer {settings.WHATSAPP_ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }

    payload = {
        "messaging_product": "whatsapp",
        "to": to_number,
        "type": "text",
        "text": {
            "body": message_text
        },
    }

    response = requests.post(url, json=payload, headers=headers, timeout=15)

    if response.status_code not in (200, 201):
        raise Exception(
            f"WhatsApp API error {response.status_code}: {response.text}"
        )

    return response.json()
