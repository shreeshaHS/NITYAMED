"""Email delivery service supporting HTTPS Gmail relay webhook, IPv4 SMTP, and dev logging."""

from email.message import EmailMessage
import logging
import smtplib
import socket

import httpx

from app.core.config import get_settings

logger = logging.getLogger("nityamed.email")


def _resolve_ipv4_host(host: str, port: int) -> str:
    """Resolve IPv4 address so containers without IPv6 routes don't hit ENETUNREACH."""
    try:
        infos = socket.getaddrinfo(host, port, socket.AF_INET, socket.SOCK_STREAM)
        if infos:
            return str(infos[0][4][0])
    except OSError:
        pass
    return host


def _send_via_webhook(
    webhook_url: str, secret: str, to_email: str, subject: str, body: str
) -> tuple[bool, str]:
    """Send email over HTTPS (port 443) via a private relay such as Google Apps Script."""
    try:
        resp = httpx.post(
            webhook_url,
            json={"secret": secret, "to": to_email, "subject": subject, "body": body},
            follow_redirects=True,
            timeout=12.0,
        )
        resp.raise_for_status()
        try:
            data = resp.json()
            if isinstance(data, dict) and data.get("ok") is False:
                err = str(data.get("error") or "Webhook rejected email request")
                return False, f"Email webhook error: {err}"
        except ValueError:
            pass
        return True, f"Email delivered via HTTPS webhook to {to_email}."
    except Exception as exc:
        logger.warning("Email webhook failed to %s: %s", to_email, exc)
        return False, f"Email webhook error: {exc}"


def send_email_detailed(to_email: str, subject: str, body: str) -> tuple[bool, str]:
    """Send a plain-text email via HTTPS webhook or SMTP without raising transport errors."""
    settings = get_settings()
    if settings.email_webhook_url:
        return _send_via_webhook(
            settings.email_webhook_url, settings.email_webhook_secret, to_email, subject, body
        )

    if not settings.smtp_host or not settings.smtp_user or not settings.smtp_password:
        logger.info("Dev email to %s | Subject: %s | Body: %s", to_email, subject, body)
        return False, "SMTP is not configured; logged in local dev mode."

    sender = settings.smtp_from_email or settings.smtp_user
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = to_email
    msg.set_content(body)

    try:
        connect_host = _resolve_ipv4_host(settings.smtp_host, settings.smtp_port)
        if settings.smtp_port == 465:
            with smtplib.SMTP_SSL(connect_host, settings.smtp_port, timeout=10) as server:
                server.login(settings.smtp_user, settings.smtp_password)
                server.send_message(msg)
        else:
            with smtplib.SMTP(connect_host, settings.smtp_port, timeout=10) as server:
                server.starttls()
                server.login(settings.smtp_user, settings.smtp_password)
                server.send_message(msg)
        return True, f"SMTP email sent successfully to {to_email}."
    except Exception as exc:
        logger.warning("SMTP delivery failed to %s: %s", to_email, exc)
        return False, f"SMTP delivery error: {exc}"


def send_email(to_email: str, subject: str, body: str) -> bool:
    """Send an email and return whether external delivery succeeded."""
    sent, _ = send_email_detailed(to_email, subject, body)
    return sent


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
