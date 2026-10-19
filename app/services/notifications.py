"""Optional Slack notifications.

Slack is used only when SLACK_ENABLED=true AND SLACK_WEBHOOK_URL is set. Otherwise every call is a no-op
apart from a debug log line. Failures are logged and never propagate to the caller.
"""

import logging

import httpx

from ..config import settings

logger = logging.getLogger(__name__)


def notify(message: str) -> bool:
    """Send a notification. Returns True if it was delivered to Slack."""
    if not settings.slack_active:
        logger.debug("[notification skipped - Slack disabled] %s", message)
        return False
    try:
        resp = httpx.post(settings.SLACK_WEBHOOK_URL, json={"text": message}, timeout=5)
        if resp.status_code != 200:
            logger.warning("Slack returned %s: %s", resp.status_code, resp.text[:200])
            return False
        return True
    except Exception as e:
        logger.warning("Slack notification failed: %s", e)
        return False
