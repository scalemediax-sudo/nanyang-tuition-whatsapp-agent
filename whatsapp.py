import os
import logging
import requests

logger = logging.getLogger(__name__)

WHATSAPP_TOKEN = os.environ.get("WHATSAPP_TOKEN")
PHONE_NUMBER_ID = os.environ.get("WHATSAPP_PHONE_NUMBER_ID")

GRAPH_API_URL = "https://graph.facebook.com/v19.0"


# ── Inbound ────────────────────────────────────────────────────────────────────

def parse_message(payload: dict) -> tuple[str | None, str | None]:
    """
    Extract the sender's phone number and message text from a WhatsApp webhook payload.
    Returns (None, None) for anything that isn't a plain text message
    (e.g. status updates, images, reactions).
    """
    try:
        entry = payload["entry"][0]
        change = entry["changes"][0]["value"]

        if "messages" not in change:
            return None, None

        message = change["messages"][0]

        if message.get("type") != "text":
            return None, None

        phone = message["from"]
        text = message["text"]["body"].strip()
        return phone, text

    except (KeyError, IndexError, TypeError):
        return None, None


# ── Outbound ───────────────────────────────────────────────────────────────────

def send_message(to: str, text: str) -> dict:
    """Send a plain-text WhatsApp message via the Cloud API."""
    url = f"{GRAPH_API_URL}/{PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json",
    }
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": to,
        "type": "text",
        "text": {"body": text},
    }

    response = requests.post(url, headers=headers, json=payload, timeout=10)

    if not response.ok:
        logger.error(
            "WhatsApp API error %s: %s", response.status_code, response.text
        )
        response.raise_for_status()

    return response.json()


def mark_as_read(message_id: str) -> None:
    """
    Send a read receipt for a message.
    Optional — call this right after receiving a message to show the double blue tick.
    """
    url = f"{GRAPH_API_URL}/{PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json",
    }
    payload = {
        "messaging_product": "whatsapp",
        "status": "read",
        "message_id": message_id,
    }
    try:
        requests.post(url, headers=headers, json=payload, timeout=5)
    except Exception as exc:
        logger.warning("Could not send read receipt: %s", exc)
