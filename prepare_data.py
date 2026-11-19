"""Download the official TTC workbooks and write UTF-8 CSV files for PostgreSQL."""

import csv
from pathlib import Path
from urllib.request import urlopen

from openpyxl import load_workbook


DATA_DIR = Path(__file__).resolve().parent / "data"
RESOURCE_URL = (
    "https://ckan0.cf.opendata.inter.prod-toronto.ca/dataset/"
    "996cfe8d-fb35-40ce-b569-698d51fc683b/resource"
)
DELAY_WORKBOOK = ("2ee1a65c-da06-4ad1-bdfb-b1a57701e46a", "ttc-subway-delay-2024.xlsx")
CODE_WORKBOOK = ("3900e649-f31e-4b79-9f20-4731bbfd94f7", "ttc-subway-delay-codes.xlsx")


def download_workbook(resource_id, filename):
    path = DATA_DIR / filename
    if not path.exists():
        url = f"{RESOURCE_URL}/{resource_id}/download/{filename}"
        print(f"Downloading {filename} ...")
        with urlopen(url, timeout=60) as response:
            contents = response.read()
        path.write_bytes(contents)
    return path


def read_delays(path):
    workbook = load_workbook(path, read_only=True, data_only=True)
    try:
        rows = workbook["Subway"].values
        expected = (
            "Date", "Time", "Day", "Station", "Code", "Min Delay", "Min Gap",
            "Bound", "Line", "Vehicle",
        )
        if next(rows) != expected:
            raise ValueError(f"Unexpected column headers in {path.name}")

        delays = []
        for source_row, values in enumerate(rows, start=2):
            if all(value is None for value in values):
                continue
            service_date, *details = values
            delays.append((source_row, service_date.date().isoformat(), *details))
        return delays
    finally:
        workbook.close()


def read_codes(path):
    workbook = load_workbook(path, read_only=True, data_only=True)
    try:
        rows = workbook["Sheet 1"].iter_rows(min_row=2, values_only=True)
        headings = next(rows)
        if headings[2:4] != ("SUB RMENU CODE", "CODE DESCRIPTION") or headings[6:8] != (
            "SRT RMENU CODE", "CODE DESCRIPTION",
        ):
            raise ValueError(f"Unexpected code headers in {path.name}")

        codes = {}
        for row in rows:
            for code, description in (row[2:4], row[6:8]):
                if code is None and description is None:
                    continue
                code, description = code.strip(), description.strip()
                if codes.setdefault(code, description) != description:
                    raise ValueError(f"Conflicting descriptions for delay code {code}")
        return sorted(codes.items())
    finally:
        workbook.close()


def write_csv(filename, headers, rows):
    path = DATA_DIR / filename
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(headers)
        writer.writerows(rows)
    print(f"Wrote {len(rows):,} rows to data/{filename}")


def main():
    DATA_DIR.mkdir(exist_ok=True)
    delays = read_delays(download_workbook(*DELAY_WORKBOOK))
    codes = read_codes(download_workbook(*CODE_WORKBOOK))

    write_csv(
        "subway_delays_2024.csv",
        (
            "source_row", "service_date", "service_time", "weekday", "station",
            "delay_code", "delay_minutes", "gap_minutes", "bound", "line", "vehicle_number",
        ),
        delays,
    )
    write_csv("delay_codes.csv", ("delay_code", "description"), codes)


if __name__ == "__main__":
    main()
