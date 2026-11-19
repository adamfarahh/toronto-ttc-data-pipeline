"""Download the City's 2025+ TTC subway data and refresh its PostgreSQL tables."""

import argparse
import csv
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from urllib.request import urlopen


RESOURCE_URL = (
    "https://ckan0.cf.opendata.inter.prod-toronto.ca/dataset/"
    "996cfe8d-fb35-40ce-b569-698d51fc683b/resource"
)
DELAYS_RESOURCE = "0b6e5c52-e993-46d6-8d74-8602ee224457"
CODES_RESOURCE = "b2d8f5e0-0997-46b5-8abd-caa685a0290b"
DELAY_HEADERS = [
    "_id", "Date", "Time", "Day", "Station", "Code", "Min Delay", "Min Gap", "Bound",
    "Line", "Vehicle",
]
CODE_HEADERS = ["_id", "CODE", "DESCRIPTION"]
SQL_SCRIPT = Path(__file__).resolve().parent / "sql" / "refresh_recent.sql"


def download_csv(resource_id, path, expected_headers):
    print(f"Downloading {path.name} ...", flush=True)
    url = f"{RESOURCE_URL}/{resource_id}/download/{path.name}"
    with urlopen(url, timeout=60) as response, path.open("wb") as output:
        shutil.copyfileobj(response, output)

    with path.open(encoding="utf-8-sig", newline="") as downloaded:
        if next(csv.reader(downloaded), None) != expected_headers:
            raise ValueError(f"Unexpected CSV headers in {path.name}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--psql", default="psql", help="Path to the psql executable")
    args = parser.parse_args()
    psql = shutil.which(args.psql)
    if psql is None:
        parser.error(f"Could not find psql at {args.psql!r}")
    psql = str(Path(psql).resolve())

    env = os.environ.copy()
    env.setdefault("PGHOST", "localhost")
    env.setdefault("PGPORT", "5432")
    env.setdefault("PGUSER", "postgres")
    env.setdefault("PGDATABASE", "ttc_delays")

    try:
        with tempfile.TemporaryDirectory(prefix="ttc-recent-") as directory:
            snapshot = Path(directory)
            download_csv(
                DELAYS_RESOURCE, snapshot / "ttc-subway-delay-data-since-2025.csv", DELAY_HEADERS
            )
            download_csv(CODES_RESOURCE, snapshot / "code-descriptions.csv", CODE_HEADERS)
            result = subprocess.run(
                [psql, "-X", "-f", str(SQL_SCRIPT)], cwd=snapshot, env=env, check=False
            )
    except (OSError, ValueError, csv.Error) as error:
        parser.exit(1, f"Refresh failed: {error}\n")
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
