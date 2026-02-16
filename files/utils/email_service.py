from django.core.mail import EmailMessage
from django.conf import settings
import os

def send_converted_file_email(user_email, file_path):
    subject = "Your Converted File is Ready"
    message = "Hi,\n\nYour converted file is attached.\n\nThank you."

    email = EmailMessage(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [user_email],
    )

    if os.path.exists(file_path):
        email.attach_file(file_path)

    email.send()
