import smtplib
from email.message import EmailMessage

from flask import current_app


def _build_message(*, to_email: str, subject: str, text_body: str, html_body: str | None = None):
    message = EmailMessage()
    message["From"] = current_app.config["MAIL_FROM"]
    message["To"] = to_email
    message["Subject"] = subject
    message.set_content(text_body)
    if html_body:
        message.add_alternative(html_body, subtype="html")
    return message


def send_mail(*, to_email: str, subject: str, text_body: str, html_body: str | None = None):
    mode = (current_app.config.get("MAIL_MODE") or "console").strip().lower()

    if mode == "off":
        current_app.logger.info("mail disabled: to=%s subject=%s", to_email, subject)
        return {"sent": False, "mode": "off"}

    if mode == "console":
        current_app.logger.info(
            "mail console mode\nTO: %s\nSUBJECT: %s\nBODY:\n%s",
            to_email,
            subject,
            text_body,
        )
        return {"sent": True, "mode": "console"}

    if mode != "smtp":
        raise RuntimeError("invalid_mail_mode")

    message = _build_message(
        to_email=to_email,
        subject=subject,
        text_body=text_body,
        html_body=html_body,
    )

    host = current_app.config.get("MAIL_HOST")
    port = int(current_app.config.get("MAIL_PORT") or 587)
    username = current_app.config.get("MAIL_USERNAME")
    password = current_app.config.get("MAIL_PASSWORD")
    use_tls = bool(current_app.config.get("MAIL_USE_TLS", True))
    use_ssl = bool(current_app.config.get("MAIL_USE_SSL", False))

    if not host:
        raise RuntimeError("mail_host_missing")

    if use_ssl:
        with smtplib.SMTP_SSL(host, port, timeout=15) as smtp:
            if username:
                smtp.login(username, password or "")
            smtp.send_message(message)
    else:
        with smtplib.SMTP(host, port, timeout=15) as smtp:
            smtp.ehlo()
            if use_tls:
                smtp.starttls()
                smtp.ehlo()
            if username:
                smtp.login(username, password or "")
            smtp.send_message(message)

    return {"sent": True, "mode": "smtp"}
