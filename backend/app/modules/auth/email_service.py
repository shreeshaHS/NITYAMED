"""Email delivery service supporting SMTP in production and safe dev logging."""

from email.message import EmailMessage
import logging
import smtplib

from app.core.config import get_settings

logger = logging.getLogger("nityamed.email")


def send_email(to_email: str, subject: str, body: str) -> bool:
    """Send a plain-text email via SMTP if configured.

    Returns True when sent via SMTP, or False when running in local dev-log mode.
    """
    settings = get_settings()
    if not settings.smtp_host or not settings.smtp_user or not settings.smtp_password:
        logger.info("Dev email to %s | Subject: %s | Body: %s", to_email, subject, body)
        return False

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = settings.smtp_from_email or settings.smtp_user
    msg["To"] = to_email
    msg.set_content(body)

    if settings.smtp_port == 465:
        with smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_port, timeout=10) as server:
            server.login(settings.smtp_user, settings.smtp_password)
            server.send_message(msg)
    else:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as server:
            server.starttls()
            server.login(settings.smtp_user, settings.smtp_password)
            server.send_message(msg)
    return True


def send_verification_email(to_email: str, otp_code: str) -> bool:
    """Send a 6-digit email verification code."""
    return send_email(
        to_email,
        "NityaMed — Verify Your Email Address",
        (
            "Welcome to NityaMed!\n\n"
            f"Your 6-digit email verification code is: {otp_code}\n\n"
            "This code expires in 15 minutes. If you did not register on NityaMed, please ignore this email."
        ),
    )


def send_password_reset_email(to_email: str, otp_code: str) -> bool:
    """Send a 6-digit password reset code."""
    return send_email(
        to_email,
        "NityaMed — Password Reset Code",
        (
            "We received a request to reset your NityaMed password.\n\n"
            f"Your 6-digit password reset code is: {otp_code}\n\n"
            "This code expires in 15 minutes. Never share this code with anyone."
        ),
    )


def send_reminder_email(to_email: str, subject: str, preview_text: str) -> bool:
    """Send a privacy-masked medication or refill reminder backup email."""
    return send_email(
        to_email,
        subject,
        (
            f"{preview_text}\n\n"
            "Please open the NityaMed app to confirm your dose or review your stock.\n"
            "Informational continuity aid only — NityaMed does not provide medical advice."
        ),
    )
