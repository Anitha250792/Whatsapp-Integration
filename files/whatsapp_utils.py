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

    # 🔍 Detect ZIP file
    is_zip = file_obj.filename.lower().endswith(".zip")

    if is_zip:
        # 📦 ZIP → send only link
        send_whatsapp_message(
            profile.whatsapp_number,
            f"{title}\n\n⬇️ Download ZIP here:\n{public_url}"
        )
    else:
        # 📄 PDF → send as media
        send_whatsapp_message(
            profile.whatsapp_number,
            title,
            media_url=public_url
        )

    profile.increment_whatsapp()

def send_whatsapp_linking_instructions(profile):
    message = (
        "🔗 *Link WhatsApp to File Converter*\n\n"
        "To receive files on WhatsApp, please do this once:\n\n"
        "1️⃣ Open WhatsApp\n"
        "2️⃣ Send this message:\n"
        "*join construction-cage*\n"
        "3️⃣ Send it to this number:\n"
        "📞 +1 415 523 8886\n\n"
        "Or click below:\n"
        "https://wa.me/14155238886?text=join%20construction-cage\n\n"
        "✅ After this, files will be delivered automatically."
    )

    send_whatsapp_message(profile.whatsapp_number, message)
