import logging

import requests
from django.conf import settings
from django.core.mail.backends.base import BaseEmailBackend

logger = logging.getLogger(__name__)

MAILTRAP_DEFAULT_URL = "https://send.api.mailtrap.io/api/send"


class MailtrapBackend(BaseEmailBackend):
    """Sends mail via Mailtrap HTTP API (works around blocked SMTP ports)."""

    def send_messages(self, email_messages):
        if not email_messages:
            return 0

        token = getattr(settings, "MAILTRAP_API_TOKEN", None)
        if not token:
            if not self.fail_silently:
                raise RuntimeError("MAILTRAP_API_TOKEN is not configured")
            logger.error("Mailtrap: token missing, skipping send")
            return 0

        url = getattr(settings, "MAILTRAP_API_URL", None) or MAILTRAP_DEFAULT_URL
        sent = 0

        for msg in email_messages:
            try:
                payload = {
                    "from": _addr(msg.from_email, getattr(settings, "MAILTRAP_FROM_NAME", "Astrolumus")),
                    "to": [_addr(r) for r in (msg.to or [])],
                    "subject": msg.subject,
                    "text": msg.body or "",
                }
                if msg.cc:
                    payload["cc"] = [_addr(r) for r in msg.cc]
                if msg.bcc:
                    payload["bcc"] = [_addr(r) for r in msg.bcc]
                if getattr(msg, "alternatives", None):
                    for content, mimetype in msg.alternatives:
                        if mimetype == "text/html":
                            payload["html"] = content
                            break

                resp = requests.post(
                    url,
                    json=payload,
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Content-Type": "application/json",
                    },
                    timeout=15,
                )
                if resp.status_code >= 400:
                    logger.error(
                        "Mailtrap send failed: HTTP %s body=%s payload=%s",
                        resp.status_code,
                        resp.text[:500],
                        {**payload, "text": payload["text"][:120]},
                    )
                    if not self.fail_silently:
                        resp.raise_for_status()
                    continue
                logger.info("Mailtrap sent to %s subject=%s", msg.to, msg.subject)
                sent += 1
            except Exception as exc:
                logger.exception("Mailtrap send exception: %s", exc)
                if not self.fail_silently:
                    raise
        return sent


def _addr(value, name=None):
    """Accept either 'a@b.com' or 'Name <a@b.com>' or dict; return Mailtrap format."""
    if isinstance(value, dict):
        return value
    if "<" in value and ">" in value:
        nm, _, em = value.partition("<")
        em = em.rstrip(">").strip()
        nm = nm.strip().strip('"')
        return {"email": em, "name": nm or (name or "")}
    return {"email": value.strip(), **({"name": name} if name else {})}
