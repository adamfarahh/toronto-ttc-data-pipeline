"""Serve the TTC dbt views as a local, read-only dashboard."""

from contextlib import closing
from datetime import date, timedelta
from getpass import getpass
import os

from flask import Flask, render_template
import psycopg2
from psycopg2.extras import RealDictCursor


def build_forecast(days):
    """Repeat the latest week and score earlier seven-day forecasts."""
    if not days:
        return None

    actuals = {date.fromisoformat(row["date"]): row["minutes"] for row in days}
    last_date = max(actuals)
    week = timedelta(days=7)
    forecast_dates = [last_date + timedelta(days=offset) for offset in range(1, 8)]
    if any(day - week not in actuals for day in forecast_dates):
        return None

    # Each seven-day test window uses the preceding week's figures as predictions.
    evaluation_start = last_date - timedelta(days=55)
    errors = [
        abs(minutes - actuals[day - week])
        for day, minutes in actuals.items()
        if day >= evaluation_start and day - week in actuals
    ]
    return {
        "days": [
            {"date": day, "minutes": actuals[day - week]}
            for day in forecast_dates
        ],
        "mae": sum(errors) / len(errors) if errors else None,
        "evaluated_days": len(errors),
    }


def display_description(description):
    # Some published descriptions contain UTF-8 bytes encoded again as Latin-1.
    if any("\u0080" <= char <= "\u009f" for char in description):
        try:
            return description.encode("latin-1").decode("utf-8")
        except UnicodeError:
            pass
    return description


def load_dashboard(connection_options):
    with closing(psycopg2.connect(**connection_options)) as connection, connection:
        connection.set_session(readonly=True, isolation_level="REPEATABLE READ")
        with connection.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("""
                SELECT service_date, logged_reports, reported_delays, total_delay_minutes
                FROM analytics.daily_delay_totals
                ORDER BY service_date
            """)
            daily = cursor.fetchall()
            cursor.execute("""
                SELECT station, reported_delays
                FROM analytics.station_delay_counts
                ORDER BY reported_delays DESC, station
                LIMIT 10
            """)
            stations = cursor.fetchall()
            cursor.execute("""
                SELECT delay_code, cause, total_delay_minutes
                FROM analytics.cause_delay_minutes
                ORDER BY total_delay_minutes DESC, delay_code, cause
                LIMIT 10
            """)
            causes = [
                {**row, "cause": display_description(row["cause"])}
                for row in cursor.fetchall()
            ]

    days = [
        {"date": row["service_date"].isoformat(), "minutes": int(row["total_delay_minutes"])}
        for row in daily
    ]
    return {
        "days": days,
        "forecast": build_forecast(days),
        "records": sum(row["logged_reports"] for row in daily),
        "delays": sum(row["reported_delays"] for row in daily),
        "minutes": sum(int(row["total_delay_minutes"]) for row in daily),
        "stations": stations,
        "causes": causes,
    }


def create_app(connection_options):
    app = Flask(__name__)

    @app.route("/")
    def dashboard():
        try:
            data = load_dashboard(connection_options)
        except psycopg2.Error as error:
            app.logger.error("PostgreSQL query failed: %s", error.diag.message_primary or type(error).__name__)
            return render_template("index.html", data=None, error=True), 503
        return render_template("index.html", data=data, error=False)

    return app


if __name__ == "__main__":
    options = {
        "host": os.getenv("PGHOST", "localhost"),
        "port": os.getenv("PGPORT", "5432"),
        "user": os.getenv("PGUSER", "postgres"),
        "dbname": os.getenv("PGDATABASE", "ttc_delays"),
        "password": os.getenv("PGPASSWORD") or getpass("PostgreSQL password: "),
        "connect_timeout": 5,
    }
    create_app(options).run(host="127.0.0.1", port=8050)
