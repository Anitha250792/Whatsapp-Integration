import os
import base64
import mimetypes
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Attachment
from django.conf import settings


def send_converted_file_email(user_email, file_path):

    print("🚀 EMAIL FUNCTION CALLED")
    print("📨 Sending to:", user_email)
    print("DEBUG API KEY:", settings.SENDGRID_API_KEY)

    try:
        message = Mail(
            from_email=settings.DEFAULT_FROM_EMAIL,
            to_emails=user_email,
            subject="ANI TEST 98765",
            plain_text_content="Hi,\n\nYour converted file is attached.\n\nThank you."
        )

        with open(file_path, "rb") as f:
            file_data = f.read()
            encoded_file = base64.b64encode(file_data).decode()

        file_type, _ = mimetypes.guess_type(file_path)
        if file_type is None:
            file_type = "application/octet-stream"

        attachment = Attachment(
            file_content=encoded_file,
            file_name=os.path.basename(file_path),
            file_type=file_type,
            disposition="attachment",
        )

        message.add_attachment(attachment)

        sg = SendGridAPIClient(settings.SENDGRID_API_KEY)
        response = sg.send(message)

        print("📧 Email sent successfully:", response.status_code)

    except Exception as e:
        print("❌ Email failed:", str(e))
