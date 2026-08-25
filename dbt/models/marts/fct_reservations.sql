SELECT
    reservation_id,
    phone_number,
    space_type,
    start_time,
    end_time,
    created_at,
    ROUND ((EXTRACT(EPOCH FROM (end_time - start_time))/ 3600)::NUMERIC,2) AS duration_hours
FROM {{ref('stg_reservations')}}
