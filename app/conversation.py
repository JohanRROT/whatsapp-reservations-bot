import os
import logging
import json
from openai import OpenAI
from dotenv import load_dotenv
from db import get_connection
from datetime import datetime, time, date, timezone

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

# Initialize the OpenAI client with the API key from .env
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

# System prompt — defines the bot's personality and purpose
def build_system_prompt():
    today = datetime.now().strftime("%A, %Y-%m-%d")
    return f"""
    You are a professional reservations assistant for a coworking space. Your goal is to help users check availability and book a workspace efficiently and accurately.

    CONTEXT
    Today's date is {today}.

    AVAILABLE SPACES
    - Hot desk: 15€/day
    - Private office: 50€/day
    - Meeting room: 30€/hour

    GREETING
    - If this is the first message in the conversation (no prior history), greet the user with a brief, professional welcome: introduce yourself as the reservations assistant for Coworking Future Now, briefly mention that you can check availability and help book a space, and invite them to get started.
    - For any message after the first, respond naturally and concisely — do not repeat the full welcome message again.

    DATE HANDLING RULES
    - Always resolve relative dates (e.g. "tomorrow", "next Friday") based on today's date above.
    - If the user mentions a date without a year, and that date has already passed this year, assume they mean the same date next year. Confirm the resolved date explicitly in your response (e.g. "Sure, that would be August 24th, 2027").
    - Never invent or guess a date that contradicts today's date. If a date is genuinely ambiguous, ask the user to clarify instead of guessing.

    AVAILABILITY AND RESERVATIONS
    - Before confirming any reservation, always check availability first using the available tools. Never confirm a reservation without verifying it against real data.
    - When checking if a requested time fits an available slot, compare the exact start and end times numerically against each available range before answering. A requested range is only unavailable if no single available slot fully contains it — do not assume partial overlap means unavailability unless you have explicitly checked the start and end boundaries.
    - When a user wants to make a reservation, collect these three things before confirming:
        1. Type of space
        2. Date and time
        3. Their name

    BEHAVIOR
    - Always respond in the same language the user writes in.
    - Keep responses concise, professional, and friendly.
    - If a user's message is ambiguous or seems disconnected from the conversation, use the conversation history to infer context before asking a generic question.
    """
# bot's tools definition
tools = [
    {
        "type": "function",
        "function": {
            "name": "get_available_times",
            "description": (
                "Check available time slots for a specific space type on a given date. "
                "Use this function whenever the user asks about availability, free hours, "
                "or open slots for a space (e.g. 'what's available tomorrow?', "
                "'is there a hot desk free on Friday?'). "
                "Always call this BEFORE confirming any reservation, to make sure the "
                "requested time actually has no conflicts."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "space_type": {
                        "type": "string",
                        "enum": ["hot_desk", "private_office", "meeting_room"],
                        "description": "The type of space the user is asking about."
                    },
                    "date": {
                        "type": "string",
                        "format": "date",
                        "description": "The date to check, in YYYY-MM-DD format."
                    }
                },
                "required": ["space_type", "date"]
            }
        }
    }
]

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
                    ORDER BY created_at DESC
                    LIMIT 30;
                    """
                cursor.execute(query, (phone_number,))
                rows = cursor.fetchall()
        return [{"role": row[0], "content": row[1]} for row in rows[::-1]]

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
    SYSTEM_PROMPT = build_system_prompt()
    try:
        logger.info(f"DEBUG - messages sent: {[{'role': 'system', 'content': SYSTEM_PROMPT}, *history]}")
        response = client.chat.completions.create( 
            model="gpt-4o-mini",
            parallel_tool_calls=False,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                *history
            ],
            tools=tools,
            max_tokens=300,
            temperature=0.7
        )
    except Exception as e:
        logger.error(f"OpenAI API call failed: {e}")
        return "En este momento el agente no se encuentra disponible, por favor intente en unos minutos"

    # Extract the assistant's reply
    response_message = response.choices[0].message

    if response_message.tool_calls:
        tool_call = response_message.tool_calls[0]

        function_name = tool_call.function.name
        function_arg = json.loads(tool_call.function.arguments)

        logger.info(f"Model requested function: {function_name} with args: {function_arg}")

        if function_name == "get_available_times":
            result = get_available_times(function_arg["space_type"], datetime.strptime(function_arg["date"],"%Y-%m-%d").date())
            formatted_result = [f"{start_time.strftime('%H:%M')} - {end_time.strftime('%H:%M')}" for start_time, end_time in result]
        else:
            result = None

        second_response = client.chat.completions.create(
             model="gpt-4o-mini",
             messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                *history,
                response_message,  # el mensaje del modelo pidiendo la función
                {
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": str(formatted_result)
                }
            ],
            max_tokens=300,
            temperature=0.7
        )
        ai_message = second_response.choices[0].message.content

    else:
        ai_message = response_message.content
    # Persist the assistant's response to PostgreSQL
    save_success = save_message(sender, "assistant", ai_message)

    if not save_success:
        logger.error("Failed to insert assistant message in conversation table")

    return ai_message

def get_available_times(space_type, date_c):
    with get_connection() as conn:
        with conn.cursor() as cursor:
            query = """
                SELECT space_type, start_time, end_time
                FROM reservations
                WHERE space_type = %s AND start_time::date = %s
                ORDER BY start_time ASC;
                """
            cursor.execute(query, (space_type, date_c,))
            reservations = cursor.fetchall()
            
            gaps = []
            opening_time = datetime.combine(date_c, time(8,0,0), tzinfo=timezone.utc)
            closing_time = datetime.combine(date_c, time(20,0,0), tzinfo=timezone.utc)
            iterador = opening_time
            for reservation in reservations:
                if reservation[1] > iterador:
                    gaps.append((iterador, reservation[1]))
                iterador = max(iterador, reservation[2])
            if iterador < closing_time:
                gaps.append((iterador, closing_time))
    
    return gaps

