# app/main.py

import os
from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)


@app.route("/webhook", methods=["POST"])
def webhook():
    """
    Receives incoming WhatsApp messages from Twilio.
    Twilio sends a POST request to this endpoint every time
    a user sends a message to the sandbox number.
    """
    # Extract the message text and sender's phone number
    incoming_message = request.form.get("Body", "").strip()
    sender = request.form.get("From", "")

    print(f"[INFO] Message from {sender}: {incoming_message}")

    # Build the response Twilio expects
    response = MessagingResponse()
    response.message("Hello! I am your reservations assistant. How can I help you?")

    return str(response), 200, {"Content-Type": "text/xml"}


if __name__ == "__main__":
    app.run(debug=True, port=5000)
