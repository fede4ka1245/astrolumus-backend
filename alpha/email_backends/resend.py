import logging

import requests
from django.conf import settings
from django.core.mail.backends.base import BaseEmailBackend

logger = logging.getLogger(__name__)

RESEND_DEFAULT_URL = "https://api.resend.com/emails"


class ResendBackend(BaseEmailBackend):
    """Sends mail via Resend HTTP API (works around blocked SMTP ports)."""

    def send_messages(self, email_messages):
        if not email_messages:
            return 0

        token = getattr(settings, "RESEND_API_TOKEN", None)
        if not token:
            if not self.fail_silently:
                raise RuntimeError("RESEND_API_TOKEN is not configured")
            logger.error("Resend: token missing, skipping send")
            return 0

        url = getattr(settings, "RESEND_API_URL", None) or RESEND_DEFAULT_URL
        sent = 0

        for msg in email_messages:
            try:
                payload = {
                    "from": msg.from_email,
                    "to": list(msg.to or []),
                    "subject": msg.subject,
                    "text": msg.body or "",
                }
                if msg.cc:
                    payload["cc"] = list(msg.cc)
                if msg.bcc:
                    payload["bcc"] = list(msg.bcc)
                if msg.reply_to:
                    payload["reply_to"] = list(msg.reply_to)
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
                        "Resend send failed: HTTP %s body=%s payload=%s",
                        resp.status_code,
                        resp.text[:500],
                        {**payload, "text": (payload.get("text") or "")[:120]},
                    )
                    if not self.fail_silently:
                        resp.raise_for_status()
                    continue
                logger.info(
                    "Resend sent to=%s subject=%s id=%s",
                    msg.to,
                    msg.subject,
                    (resp.json() or {}).get("id"),
                )
                sent += 1
            except Exception as exc:
                logger.exception("Resend send exception: %s", exc)
                if not self.fail_silently:
                    raise
        return sent
