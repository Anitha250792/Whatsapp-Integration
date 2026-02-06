def send_whatsapp_if_allowed(user, message):
    try:
        profile = user.userprofile
    except:
        return

    if not profile.whatsapp_enabled:
        return

    if not profile.can_send_whatsapp():
        return

    send_whatsapp_message(profile.whatsapp_number, message)
    profile.increment_whatsapp()
