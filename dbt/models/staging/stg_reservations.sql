SELECT
    id AS reservation_id,
    phone_number,
    space_type,
    start_time,
    end_time,
    created_at
FROM {{ source('flask_bot', 'reservations') }}
