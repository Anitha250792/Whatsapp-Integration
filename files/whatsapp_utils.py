from django.utils import timezone
from files.whatsapp import send_whatsapp_message


def try_send_whatsapp(user, request, file_obj, title):
    profile = getattr(user, "userprofile", None)

    if not profile:
        return
    if not profile.whatsapp_enabled:
        return
    if not profile.whatsapp_number:
        return
    if not profile.can_send_whatsapp():
        return

    public_url = request.build_absolute_uri(
        f"/files/public/{file_obj.public_token}/"
    )

    is_zip = file_obj.filename.lower().endswith(".zip")

    # ✅ SEND MESSAGE
    if is_zip:
        sid = send_whatsapp_message(
            profile.whatsapp_number,
            f"{title}\n\n⬇️ Download ZIP here:\n{public_url}"
        )
    else:
        sid = send_whatsapp_message(
            profile.whatsapp_number,
            title,
            media_url=public_url
        )

    # ✅ SAVE STATUS + SID
    if sid:
        file_obj.whatsapp_message_sid = sid
        file_obj.whatsapp_status = "sent"
        file_obj.save(update_fields=[
            "whatsapp_message_sid",
            "whatsapp_status"
        ])

        profile.increment_whatsapp()


def send_whatsapp_linking_instructions(profile):
    message = (
        "🔗 *Link WhatsApp to File Converter*\n\n"
        "To receive files automatically:\n\n"
        "1️⃣ Open WhatsApp\n"
        "2️⃣ Send this message:\n"
        "*join construction-cage*\n"
        "3️⃣ Send it to:\n"
        "📞 +1 415 523 8886\n\n"
        "Or tap:\n"
        "https://wa.me/14155238886?text=join%20construction-cage\n\n"
        "✅ After linking, files will be delivered automatically."
    )

    send_whatsapp_message(profile.whatsapp_number, message)
