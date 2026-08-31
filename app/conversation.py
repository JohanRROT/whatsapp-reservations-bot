import os
import logging
from openai import OpenAI
from dotenv import load_dotenv
from db import get_connection

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

# Initialize the OpenAI client with the API key from .env
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

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

def get_conversation_history(phone_number: str) -> list | None:
    """
    Retrieves the conversation history for a given phone number.
    Args:
        phone_number: Clean phone number without 'whatsapp:' prefix
    Returns:
        List of message dicts with 'role' and 'content' keys,
        ordered chronologically (oldest first), limited to 30 messages
    """
    try:
        with get_connection() as conn:
            with conn.cursor() as cursor:
                query = """
                    SELECT role, content
                    FROM conversations
                    WHERE phone_number = %s
                    ORDER BY created_at ASC
                    LIMIT 30;
                    """
                cursor.execute(query, (phone_number,))
                rows = cursor.fetchall()
        return [{"role": row[0], "content": row[1]} for row in rows]

    except Exception as e:
        logger.error(f"Failed to get historical chat from the conversation table: {e}")
        return None


def save_message(phone_number: str, role: str, content: str) -> bool:
    """
    Persists a single message to the conversations table.
    Args:
        phone_number: Clean phone number without 'whatsapp:' prefix
        role: Either 'user' or 'assistant'
        content: The message text
    """
    try:
        with get_connection() as conn:
            with conn.cursor() as cursor:
                query = """
                    INSERT INTO conversations (phone_number, role, content)
                    VALUES (%s, %s, %s);
                """
                cursor.execute(query, (phone_number, role, content))
            conn.commit()
        return True

    except Exception as e:
        logger.error(f"Failed to insert register in conversation table: {e}")
        return False


def get_ai_response(sender: str, user_message: str) -> str:
    """
    Receives a message from a user and returns an AI-generated response.
    Persists both the user message and the assistant response to PostgreSQL.
    Args:
        sender: Clean phone number without 'whatsapp:' prefix
        user_message: The text message sent by the user
    Returns:
        AI-generated response as a string
    """
    # Persist the incoming user message to PostgreSQL
    validator = save_message(sender, "user", user_message)

    if not validator:
        logger.error("Failed to insert user message in conversation table")

        return "En este momento hay un fallo con el almacenamiento de la información, estamos trabajando en ello, vuelva a intentarlo en unos minutos"

    # Retrieve full conversation history for this user (includes message just saved)
    history = get_conversation_history(sender)
    if history is None:
        logger.error("Failed to get historical chat from the conversation table")

        return "En este momento hay un fallo con la recuperación del historial de conversaciones, estamos trabajando en ello, vuelva a intentarlo en unos minutos"

    # Call the OpenAI API with system prompt + full conversation history
    try:
        response = client.chat.completions.create( 
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                *history
            ],
            max_tokens=300,
            temperature=0.7
        )
    except Exception as e:
        logger.error(f"OpenAI API call failed: {e}")
        return "En este momento el agente no se encuentra disponible, por favor intente en unos minutos"

    # Extract the assistant's reply
    ai_message = response.choices[0].message.content

    # Persist the assistant's response to PostgreSQL
    save_success = save_message(sender, "assistant", ai_message)

    if not save_success:
        logger.error("Failed to insert assistant message in conversation table")

    return ai_message
