"""
Reminder DAGs for the coworking reservations bot.
Two DAGs run hourly to send 24h and 1h reminders via WhatsApp.
"""
import logging
from airflow.decorators import dag, task
from datetime import datetime
from twilio.rest import Client
from app.db import get_connection
from app.config import TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_WHATSAPP_NUMBER

logger = logging.getLogger(__name__)

@task
def read_pending_reminders (reminder_type: str, hours_before:int):
    try:
        with get_connection() as conn:
            with conn.cursor() as cursor:
                query = """
                    SELECT
                        rv.id,
                        rv.phone_number,
                        rv.space_type,
                        rv.start_time,
                        rv.end_time
                    FROM reservations AS rv
                    LEFT JOIN reminders AS rm
                      ON rv.id = rm.reservation_id
                      AND rm.reminder_type = %s
                    WHERE rm.reservation_id IS NULL
                      AND rv.start_time BETWEEN NOW() + (%s||' hours')::INTERVAL
                                        AND NOW() + (%s||' hours')::INTERVAL + INTERVAL '1 hour';
                    """
                cursor.execute(query,(reminder_type, hours_before, hours_before,))
                rows = cursor.fetchall()
        return [{"id": row[0], "phone_number": row[1], "space_type": row[2], "start_time": row[3], "end_time": row[4]} for row in rows]
    
    except Exception as e:
        logger.error(f"Failed to retrieve pending reminders from reservations/reminders join: {e}")
        raise

@task
def send_and_log_reminder(reservation: dict, reminder_type: str):
    try:
        message_body = f"Hola, te recordamos tu reserva de {reservation['space_type']} el {reservation['start_time']}."
        twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        twilio_client.messages.create(
            from_ = TWILIO_WHATSAPP_NUMBER,
            to = f'whatsapp:{reservation["phone_number"]}',
            body = message_body
            )
    except Exception as e:
        logger.error(f"Twilio's call API failed: {e}")
        raise
    try:
        with get_connection() as conn:
            with conn.cursor() as cursor:
                query="""
                    INSERT INTO reminders (reservation_id, reminder_type)
                    VALUES(%s,%s);
                    """
                cursor.execute(query,(reservation['id'],reminder_type))
                conn.commit()

    except Exception as e:
        logger.error(f"Failed to insert reminder record: {e}")
        raise


def build_reminder_dag(reminder_type:str, hours_before: int, dag_id: str):
    @dag(
        dag_id=dag_id,
        schedule="@hourly",
        start_date=datetime(2025, 1, 1),
        catchup=False,
        tags=["reminders"],
        )
    def _dag():
        reservations = read_pending_reminders(reminder_type=reminder_type, hours_before=hours_before)
        send_and_log_reminder.partial(reminder_type=reminder_type).expand(reservation=reservations)

    return _dag()

reminder_24h_dag = build_reminder_dag(reminder_type="24h", hours_before=24, dag_id="reminder_24h")
reminder_1h_dag  = build_reminder_dag(reminder_type="1h",  hours_before=1,  dag_id="reminder_1h")
