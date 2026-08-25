SELECT
    id AS reminder_id,
    reservation_id,
    reminder_type,
    sent_at
FROM {{ source('flask_bot', 'reminders') }}
