import smtplib
import ssl
from email.message import EmailMessage
from app.core.config import settings


def send_email(recipient: str, subject: str | None, body: str) -> None:
    msg = EmailMessage()
    msg["Subject"] = subject or "(sem assunto)"
    msg["From"] = settings.SMTP_USER
    msg["To"] = recipient
    msg.set_content(body)

    context = ssl.create_default_context()
    with smtplib.SMTP_SSL(settings.SMTP_HOST, settings.SMTP_PORT, context=context) as server:
        server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
        server.send_message(msg)