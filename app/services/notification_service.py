import requests
from app.config import settings

def send_notification(message: str):
    """
    Sends a message to Slack webhook if configured.
    Falls back to local logging if not set.
    """
    if not settings.SLACK_WEBHOOK_URL or settings.SLACK_WEBHOOK_URL.strip() == "":
        print(f"[NOTIFICATION - LOCAL LOG] {message}")
        return

    try:
        payload = {"text": message}
        # Timeout 5 seconds as requested
        response = requests.post(settings.SLACK_WEBHOOK_URL, json=payload, timeout=5)

        if response.status_code != 200:
            print(f"[NOTIFICATION ERROR] Slack returned {response.status_code}: {response.text}")

    except Exception as e:
        # notification failures must never raise exceptions to the main app
        print(f"[NOTIFICATION ERROR] Failed to send Slack notification: {str(e)}")
