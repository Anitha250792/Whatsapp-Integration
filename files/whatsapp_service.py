from files.whatsapp import send_whatsapp_message

def send_file_whatsapp(user, request, file_obj, text):
    profile = getattr(user, "userprofile", None)

    if not profile or not profile.whatsapp_enabled:
        return False

    public_url = request.build_absolute_uri(
        f"/files/public/{file_obj.public_token}/"
    )

    # 🔐 24-hour rule
    if profile.within_24h_window():
        send_whatsapp_message(
            profile.whatsapp_number,
            text,
            media_url=public_url
        )
    else:
        # 🚨 Outside 24h → TEMPLATE REQUIRED
        send_whatsapp_message(
            profile.whatsapp_number,
            "📄 Your file is ready. Please reply YES to receive it."
        )
        return False

    profile.increment_whatsapp()
    return True
