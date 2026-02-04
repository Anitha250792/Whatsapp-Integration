import requests
from django.conf import settings

def send_whatsapp_message(to_number, message):
    url = f"https://graph.facebook.com/v19.0/{settings.922813980922652}/messages"

    headers = {
        "Authorization": f"Bearer {settings.EAARrIXLNDUwBQmlPZAylIUL0jVYk79ilHijvm9Cp5RYzQfJHxp1E2wWbSIsAeZAVFsOdP4jwmmmbTeWenzgy4veWrHMpxf9Ptsra2qOHaBk2itoS8oZBsIxAZB8aU0BiXl4Ut7z0DFRdWAb6uDdY23tc6YUbKT2qrgLgN6McB31Ws6f6W0RxZBUDeUSs7P5oLVuhM2jZBJwB4RaZBfOhtfL5NaNJeezNNhlC2DjTEx01wEDjhjA5dRoIPAUXtGjIfCMTv4ITB3kFmg1XRGk5FsrY8gvnzZAo2O4TGwgNQwZDZD}",
        "Content-Type": "application/json",
    }

    payload = {
        "messaging_product": "whatsapp",
        "to": to_number,
        "type": "text",
        "text": {"body": message},
    }

    response = requests.post(url, json=payload, headers=headers)

    if response.status_code >= 400:
        raise Exception(response.text)

    return response.json()
