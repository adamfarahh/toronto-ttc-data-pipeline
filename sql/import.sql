\set ON_ERROR_STOP on

BEGIN;

CREATE TABLE IF NOT EXISTS subway_delays (
    source_row integer PRIMARY KEY CHECK (source_row >= 2),
    service_date date NOT NULL CHECK (
        service_date >= DATE '2024-01-01' AND service_date < DATE '2025-01-01'
    ),
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

CREATE TABLE IF NOT EXISTS delay_codes (
    delay_code text PRIMARY KEY,
    description text NOT NULL
);

-- Load the CSV files into temporary tables before touching the stored records.
CREATE TEMP TABLE staged_delays (LIKE subway_delays) ON COMMIT DROP;
CREATE TEMP TABLE staged_codes (LIKE delay_codes) ON COMMIT DROP;

\copy staged_delays (source_row, service_date, service_time, weekday, station, delay_code, delay_minutes, gap_minutes, bound, line, vehicle_number) FROM 'data/subway_delays_2024.csv' WITH (FORMAT csv, HEADER true, ENCODING 'UTF8')
\copy staged_codes (delay_code, description) FROM 'data/delay_codes.csv' WITH (FORMAT csv, HEADER true, ENCODING 'UTF8')

INSERT INTO subway_delays (
    source_row, service_date, service_time, weekday, station, delay_code,
    delay_minutes, gap_minutes, bound, line, vehicle_number
)
SELECT source_row, service_date, service_time, weekday, station, delay_code,
       delay_minutes, gap_minutes, bound, line, vehicle_number
FROM staged_delays
ON CONFLICT (source_row) DO NOTHING;

INSERT INTO delay_codes (delay_code, description)
SELECT delay_code, description
FROM staged_codes
ON CONFLICT (delay_code) DO NOTHING;

COMMIT;
