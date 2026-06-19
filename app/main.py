# app/main.py

import os
from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
from dotenv import load_dotenv
from conversation import get_ai_response

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)


@app.route("/webhook", methods=["POST"])
def webhook():
    """
    Receives incoming WhatsApp messages from Twilio.
    Passes the message to the AI and returns the response.
    """
    # Extract the message text and sender's phone number
    incoming_message = request.form.get("Body", "").strip()
    sender = request.form.get("From", "")
    sender = sender.replace("whatsapp:","")

    print(f"[INFO] Message from {sender}: {incoming_message}")

    # Get AI-generated response passing sender and message
    ai_response = get_ai_response(sender, incoming_message)

    print(f"[INFO] AI response: {ai_response}")

    # Build the Twilio response with the AI message
    response = MessagingResponse()
    response.message(ai_response)

    return str(response), 200, {"Content-Type": "text/xml"}


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)

