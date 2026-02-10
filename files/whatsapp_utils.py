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

    send_whatsapp_message(
        profile.whatsapp_number,
        title,
        media_url=public_url,
    )

    profile.increment_whatsapp()
