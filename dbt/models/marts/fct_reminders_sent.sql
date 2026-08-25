SELECT
    rem.reminder_id,
    rem.reservation_id,
    rem.reminder_type,
    rem.sent_at,
    res.space_type,
    res.start_time,
    res.duration_hours
FROM {{ref('stg_reminders')}} AS rem 
INNER JOIN {{ref('fct_reservations')}} AS res
    ON  rem.reservation_id = res.reservation_id
