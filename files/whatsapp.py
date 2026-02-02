import requests
from django.conf import settings

def send_whatsapp_message(phone, message):
    url = f"https://graph.facebook.com/v19.0/{settings.WHATSAPP_PHONE_NUMBER_ID}/messages"

    payload = {
        "messaging_product": "whatsapp",
        "to": phone,
        "type": "text",
        "text": {"body": message},
    }

    headers = {
        "Authorization": f"Bearer {settings.WHATSAPP_ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }

    response = requests.post(url, json=payload, headers=headers)
    response.raise_for_status()
    return response.json()
