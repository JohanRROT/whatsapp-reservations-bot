"""
Centralized configuration module.
Reads all environment variables once and exposes them as module-level constants.
"""

import os
from dotenv import load_dotenv

# Load .env into os.environ. Must happen before any os.getenv() call below.
load_dotenv()

# --- Database ---
DB_HOST = os.getenv("DB_HOST")
DB_PORT = int(os.getenv("DB_PORT"))
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# --- Twilio ---
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_WHATSAPP_NUMBER = os.getenv("TWILIO_WHATSAPP_NUMBER")

# --- OpenAI ---
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# --- Validation: fail fast at import time if anything is missing ---
_required = {
    "DATABASE_URL": DATABASE_URL,
    "TWILIO_ACCOUNT_SID": TWILIO_ACCOUNT_SID,
    "TWILIO_AUTH_TOKEN": TWILIO_AUTH_TOKEN,
    "TWILIO_WHATSAPP_NUMBER": TWILIO_WHATSAPP_NUMBER,
    "OPENAI_API_KEY": OPENAI_API_KEY,
    "DB_HOST": DB_HOST,
    "DB_PORT": DB_PORT,
    "DB_NAME": DB_NAME,
    "DB_USER": DB_USER,
    "DB_PASSWORD": DB_PASSWORD
}
_missing = [name for name, value in _required.items() if not value]
if _missing:
    raise RuntimeError(
        f"Missing required environment variables: {', '.join(_missing)}. "
        f"Check your .env file."
    )
