# app/conversation.py

import os
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize the OpenAI client with the API key from .env
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

# In-memory store for conversation histories
# Key: phone number (e.g. "whatsapp:+34612345678")
# Value: list of message dicts with "role" and "content"
conversation_history = {}

# System prompt — defines the bot's personality and purpose
SYSTEM_PROMPT = """
You are a helpful reservations assistant for a coworking space.
Your job is to help users check availability and book a workspace.

Available spaces:
- Hot desk: 15€/day
- Private office: 50€/day
- Meeting room: 30€/hour

When a user wants to make a reservation, collect:
1. Type of space
2. Date and time
3. Their name

Always respond in the same language the user writes in.
Keep responses concise and friendly.
"""


def get_ai_response(sender: str, user_message: str) -> str:
    """
    Receives a message from a user and returns an AI-generated response.
    Maintains conversation history per phone number.

    Args:
        sender: Phone number of the user (e.g. "whatsapp:+34612345678")
        user_message: The text message sent by the user

    Returns:
        AI-generated response as a string
    """

    # Initialize history for new users
    if sender not in conversation_history:
        conversation_history[sender] = []

    # Append the new user message to their history
    conversation_history[sender].append({
        "role": "user",
        "content": user_message
    })

    # Call the OpenAI API with the full conversation history
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            *conversation_history[sender]
        ],
        max_tokens=300,
        temperature=0.7
    )

    # Extract the text from the response
    ai_message = response.choices[0].message.content

    # Save the assistant's response to the history
    conversation_history[sender].append({
        "role": "assistant",
        "content": ai_message
    })

    return ai_message# app/conversation.py

