import os
import logging
from flask import Flask, request, jsonify
from whatsapp import parse_message, send_message
from agent import get_response

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

app = Flask(__name__)

VERIFY_TOKEN = os.environ.get("VERIFY_TOKEN")


@app.route("/", methods=["GET"])
def health_check():
    return jsonify({"status": "running"}), 200


@app.route("/webhook", methods=["GET"])
def verify_webhook():
    """Meta webhook verification handshake."""
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")

    if mode == "subscribe" and token == VERIFY_TOKEN:
        logger.info("Webhook verified successfully.")
        return challenge, 200

    logger.warning("Webhook verification failed — token mismatch.")
    return "Forbidden", 403


@app.route("/webhook", methods=["POST"])
def receive_message():
    """Receive incoming WhatsApp messages and reply with AI response."""
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"status": "no data"}), 400

    phone, text = parse_message(data)

    if not phone or not text:
        # Ignore status updates, media messages, etc.
        return jsonify({"status": "ignored"}), 200

    logger.info("Incoming message from %s: %s", phone, text[:80])

    try:
        reply = get_response(phone, text)
        send_message(phone, reply)
        logger.info("Replied to %s", phone)
    except Exception as exc:
        logger.exception("Error handling message from %s: %s", phone, exc)
        return jsonify({"status": "error"}), 500

    return jsonify({"status": "ok"}), 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
