"""Refresh the TTC feed, then rebuild and test the PostgreSQL views."""

import os
from pathlib import Path
import subprocess
from datetime import timedelta

import pendulum
from airflow.sdk import Connection, dag, task


PROJECT = Path("/mnt/c/Users/adamj/Toronto TTC Data Pipeline")
PSQL = r"C:\Program Files\PostgreSQL\18\bin\psql.exe"


def run_windows_tool(*args):
    connection = Connection.get("ttc_postgres")
    if not connection.password:
        raise ValueError("Set the password on the ttc_postgres Airflow connection.")
    settings = {
        "PGHOST": connection.host or "localhost",
        "PGPORT": str(connection.port or 5432),
        "PGUSER": connection.login or "postgres",
        "PGDATABASE": connection.schema or "ttc_delays",
        "PGPASSWORD": connection.password,
        "DBT_ENV_SECRET_TTC_PASSWORD": connection.password,
    }
    settings.update({
        "TTC_PG_HOST": settings["PGHOST"],
        "TTC_PG_PORT": settings["PGPORT"],
        "TTC_PG_USER": settings["PGUSER"],
        "TTC_PG_DATABASE": settings["PGDATABASE"],
    })
    env = os.environ | settings
    forwarded = [
        item for item in env.get("WSLENV", "").split(":")
        if item and item.split("/")[0] not in settings
    ]
    env["WSLENV"] = ":".join(forwarded + [f"{name}/w" for name in settings])
    subprocess.run([str(PROJECT / args[0]), *args[1:]], cwd=PROJECT, env=env, check=True)


@dag(
    schedule="0 9 * * 1",
    start_date=pendulum.datetime(2026, 11, 19, tz="America/Toronto"),
    catchup=False,
    max_active_runs=1,
    default_args={"retries": 1, "retry_delay": timedelta(minutes=5)},
)
def ttc_subway_refresh():
    @task
    def refresh_recent_data():
        run_windows_tool(".venv/Scripts/python.exe", "refresh_recent.py", "--psql", PSQL)

    @task
    def build_analytics():
        run_windows_tool(
            ".venv/Scripts/dbt.exe", "build", "--project-dir", "dbt", "--profiles-dir", "dbt"
        )

    refresh_recent_data() >> build_analytics()


ttc_subway_refresh()