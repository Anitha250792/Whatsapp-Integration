from django.utils import timezone
from files.whatsapp import send_whatsapp_message
from files.whatsapp_templates import send_template_message

FILE_READY_TEMPLATE_SID = "HXxxxxxxxxxxxxxxxx"  # from Twilio


def try_send_whatsapp(user, request, file_obj, title):
    profile = getattr(user, "userprofile", None)

    if not profile or not profile.whatsapp_enabled:
        return False

    if not profile.whatsapp_number or not profile.can_send_whatsapp():
        return False

    public_url = request.build_absolute_uri(
        f"/files/public/{file_obj.public_token}/"
    )

    # ✅ 24-hour window check
    if profile.within_24h_window():
        sent = send_whatsapp_message(
            to=profile.whatsapp_number,
            body=title,
            media_url=public_url,
        )
    else:
        # ❌ Outside 24h → TEMPLATE REQUIRED
        sent = send_template_message(
            to=profile.whatsapp_number,
            template_sid=FILE_READY_TEMPLATE_SID,
            variables={
                "1": title,
                "2": public_url,
            }
        )

    if sent:
        profile.increment_whatsapp()

    return sent
