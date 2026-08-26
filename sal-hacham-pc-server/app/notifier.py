from __future__ import annotations

import logging

import httpx

from .config import settings

log = logging.getLogger("notifier")


def send(text: str) -> bool:
    """Send a Telegram message to the configured owner chat.

    Returns False (and logs the message instead) when Telegram is not
    configured, so callers can fire-and-forget without checking first.
    """
    if not settings.telegram_bot_token or not settings.telegram_chat_id:
        log.info("Telegram not configured; message:\n%s", text)
        return False
    if not text or not text.strip():
        log.warning("Telegram message is empty")
        return False

    url = f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage"
    try:
        response = httpx.post(
            url,
            json={"chat_id": settings.telegram_chat_id, "text": text},
            timeout=15,
        )
        if not response.is_success:
            log.error("telegram send failed: status=%s body=%s", response.status_code, response.text)
            return False
        return True
    except httpx.HTTPError as exc:
        log.error("telegram request failed: %s", exc)
        return False
