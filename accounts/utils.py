import os
from twilio.rest import Client

def send_whatsapp_if_allowed(user, message):
    """
    Sends WhatsApp message via Twilio if user enabled it.
    NEVER raises error (safe).
    """

    try:
        profile = getattr(user, "userprofile", None)
        if not profile:
            print("❌ No user profile")
            return

        if not profile.whatsapp_enabled:
            print("❌ WhatsApp disabled")
            return

        if not profile.whatsapp_number:
            print("❌ No WhatsApp number")
            return

        account_sid = os.getenv("TWILIO_ACCOUNT_SID")
        auth_token = os.getenv("TWILIO_AUTH_TOKEN")
        from_number = os.getenv("TWILIO_WHATSAPP_FROM")

        if not account_sid or not auth_token or not from_number:
            print("❌ Twilio ENV missing")
            return

        client = Client(account_sid, auth_token)

        client.messages.create(
            from_=from_number,
            to=f"whatsapp:{profile.whatsapp_number}",
            body=message,
        )

        print("✅ WhatsApp sent successfully")

    except Exception as e:
        # WhatsApp must NEVER break file conversion
        print("⚠ WhatsApp error:", e)
