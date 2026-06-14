"""Lightweight Telegram notifications for inbound leads.

Sends a message to the configured chat via the Bot API. No-ops silently when the
token/chat are not configured (e.g. local dev) and never raises into the request
path — a failed notification must not break accepting the lead.
"""
import logging

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


def send_telegram(text: str) -> None:
    token = (getattr(settings, "TELEGRAM_BOT_TOKEN", "") or "").strip()
    chat_id = (getattr(settings, "TELEGRAM_LEADS_CHAT_ID", "") or "").strip()
    if not token or not chat_id:
        return
    try:
        resp = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={
                "chat_id": chat_id,
                "text": text,
                "parse_mode": "HTML",
                "disable_web_page_preview": True,
            },
            timeout=8,
        )
        if not resp.ok:
            logger.warning("telegram notify failed: %s %s", resp.status_code, resp.text[:300])
    except Exception:  # network/timeout — never propagate into the request
        logger.exception("telegram notify error")
