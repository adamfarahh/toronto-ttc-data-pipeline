\set ON_ERROR_STOP on

BEGIN;

-- Run one snapshot refresh at a time. The transaction releases this lock.
SELECT pg_advisory_xact_lock(hashtext('ttc_delays.refresh_recent'));

CREATE TABLE IF NOT EXISTS public.subway_delays_recent (
    source_id integer PRIMARY KEY CHECK (source_id > 0),
    service_date date NOT NULL CHECK (service_date >= DATE '2025-01-01'),
    service_time time NOT NULL,
    weekday text NOT NULL,
    station text NOT NULL,
    delay_code text NOT NULL,
    delay_minutes integer NOT NULL CHECK (delay_minutes >= 0),
    gap_minutes integer NOT NULL CHECK (gap_minutes >= 0),
    bound text,
    line text,
    vehicle_number integer NOT NULL
);

CREATE TABLE IF NOT EXISTS public.delay_codes_recent (
    source_id integer NOT NULL CHECK (source_id > 0),
    delay_code text PRIMARY KEY,
    description text NOT NULL
);

CREATE TEMP TABLE staged_recent_delays (
    LIKE public.subway_delays_recent INCLUDING CONSTRAINTS INCLUDING INDEXES
) ON COMMIT DROP;
CREATE TEMP TABLE staged_recent_codes (
    LIKE public.delay_codes_recent INCLUDING CONSTRAINTS INCLUDING INDEXES
) ON COMMIT DROP;

\copy staged_recent_delays (source_id, service_date, service_time, weekday, station, delay_code, delay_minutes, gap_minutes, bound, line, vehicle_number) FROM 'ttc-subway-delay-data-since-2025.csv' WITH (FORMAT csv, HEADER true, ENCODING 'UTF8')
\copy staged_recent_codes (source_id, delay_code, description) FROM 'code-descriptions.csv' WITH (FORMAT csv, HEADER true, ENCODING 'UTF8')

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM staged_recent_delays)
       OR NOT EXISTS (SELECT 1 FROM staged_recent_codes) THEN
        RAISE EXCEPTION 'The TTC snapshot must contain both reports and code descriptions';
    END IF;
END;
$$;

-- Replace the recent snapshot in a single transaction. Readers can use the last
-- committed version while these writes are in progress.
DELETE FROM public.subway_delays_recent;
DELETE FROM public.delay_codes_recent;

INSERT INTO public.subway_delays_recent (
    source_id, service_date, service_time, weekday, station, delay_code,
    delay_minutes, gap_minutes, bound, line, vehicle_number
)
SELECT source_id, service_date, service_time, weekday, station, delay_code,
       delay_minutes, gap_minutes, bound, line, vehicle_number
FROM staged_recent_delays;

INSERT INTO public.delay_codes_recent (source_id, delay_code, description)
SELECT source_id, delay_code, description
FROM staged_recent_codes;

COMMIT;

SELECT COUNT(*) AS recent_reports,
       MIN(service_date) AS first_service_date,
       MAX(service_date) AS last_service_date
FROM public.subway_delays_recent;
