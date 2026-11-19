{% set recent_delays = source('ttc_raw', 'subway_delays_recent') %}
{% set recent_codes = source('ttc_raw', 'delay_codes_recent') %}

WITH source_reports AS (
    SELECT
        'archive_2024' AS data_source,
        delays.source_row AS source_id,
        delays.source_row,
        delays.service_date,
        delays.service_time,
        delays.weekday,
        delays.station,
        delays.delay_code,
        codes.description AS cause_description,
        delays.delay_minutes,
        delays.gap_minutes,
        delays.bound,
        delays.line,
        delays.vehicle_number
    FROM {{ source('ttc_raw', 'subway_delays') }} AS delays
    LEFT JOIN {{ source('ttc_raw', 'delay_codes') }} AS codes
        ON codes.delay_code = delays.delay_code

    {% if recent_feed_available(recent_delays, recent_codes) %}
    UNION ALL

    SELECT
        'recent' AS data_source,
        delays.source_id,
        NULL::integer AS source_row,
        delays.service_date,
        delays.service_time,
        delays.weekday,
        delays.station,
        delays.delay_code,
        codes.description AS cause_description,
        delays.delay_minutes,
        delays.gap_minutes,
        delays.bound,
        delays.line,
        delays.vehicle_number
    FROM {{ recent_delays }} AS delays
    LEFT JOIN {{ recent_codes }} AS codes
        ON codes.delay_code = delays.delay_code
    {% endif %}
)

SELECT
    source_row,
    service_date,
    service_time,
    weekday,
    station,
    delay_code,
    COALESCE(cause_description, 'Unmapped TTC code') AS cause,
    delay_minutes,
    gap_minutes,
    bound,
    line,
    vehicle_number,
    delay_minutes > 0 AS is_reported_delay,
    data_source,
    data_source || ':' || source_id::text AS report_id
FROM source_reports
