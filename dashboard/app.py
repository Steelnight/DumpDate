"""
This module contains the backend Flask application for the dashboard.
"""

import logging
import os
import sqlite3
from datetime import datetime

from flask import Flask, render_template
from schedule_parser.db_manager import init_db

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Initialize the main database
init_db()

DB_PATH = "waste_schedule.db"
ADDRESS_DB_PATH = "address_lookup.db"


def get_db_connection(db_path):
    """Creates a database connection."""
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        return conn
    except sqlite3.Error as e:
        logger.error(f"Database error: {e}")
        return None


def get_file_size_mb(path):
    """Returns the file size in MB, or 0 if it doesn't exist."""
    if os.path.exists(path):
        return round(os.path.getsize(path) / (1024 * 1024), 2)
    return 0


@app.route("/")
def index():
    """Renders the main dashboard page with KPIs and logs."""
    kpis = {
        "active_subscriptions": 0,
        "unique_addresses_subscribed": 0,
        "total_cached_addresses": 0,
        "db_size_mb": get_file_size_mb(DB_PATH),
        "address_db_size_mb": get_file_size_mb(ADDRESS_DB_PATH),
        "bot_uptime_hours": "N/A",
        "ical_download_errors": 0,
        "opt_out_rate_percent": 0,
        "delivery_rate_percent": 0,
        "failure_rate_percent": 0,
        "avg_delivery_latency_seconds": 0,
    }
    logs = []

    # Connect to the main database
    conn = get_db_connection(DB_PATH)
    if conn:
        try:
            cur = conn.cursor()

            # --- Calculate KPIs ---
            kpis["active_subscriptions"] = cur.execute(
                "SELECT COUNT(*) FROM subscriptions WHERE is_active = 1"
            ).fetchone()[0]
            kpis["unique_addresses_subscribed"] = cur.execute(
                "SELECT COUNT(DISTINCT address_id) FROM subscriptions WHERE is_active = 1"
            ).fetchone()[0]

            # Get bot start time and calculate uptime
            start_time_str = cur.execute(
                "SELECT value FROM system_info WHERE key = 'bot_start_time'"
            ).fetchone()
            if start_time_str:
                start_time = datetime.fromisoformat(start_time_str[0])
                uptime = datetime.now() - start_time
                kpis["bot_uptime_hours"] = round(uptime.total_seconds() / 3600, 2)

            # Get iCal download errors from logs
            kpis["ical_download_errors"] = cur.execute(
                "SELECT COUNT(*) FROM logs WHERE level = 'ERROR' AND message LIKE '%iCal download failed%'"
            ).fetchone()[0]

            # Calculate opt-out rate
            total_subscriptions = cur.execute(
                "SELECT COUNT(*) FROM subscriptions"
            ).fetchone()[0]
            inactive_subscriptions = cur.execute(
                "SELECT COUNT(*) FROM subscriptions WHERE is_active = 0"
            ).fetchone()[0]
            if total_subscriptions > 0:
                kpis["opt_out_rate_percent"] = round(
                    (inactive_subscriptions / total_subscriptions) * 100, 2
                )

            # --- Notification KPIs ---
            try:
                total_notifications = cur.execute(
                    "SELECT COUNT(*) FROM notification_logs WHERE status IN ('success', 'failure')"
                ).fetchone()[0]
                if total_notifications > 0:
                    successful_notifications = cur.execute(
                        "SELECT COUNT(*) FROM notification_logs WHERE status = 'success'"
                    ).fetchone()[0]
                    failed_notifications = cur.execute(
                        "SELECT COUNT(*) FROM notification_logs WHERE status = 'failure'"
                    ).fetchone()[0]

                    kpis["delivery_rate_percent"] = round(
                        (successful_notifications / total_notifications) * 100, 2
                    )
                    kpis["failure_rate_percent"] = round(
                        (failed_notifications / total_notifications) * 100, 2
                    )

                    # Calculate average latency for successful notifications
                    avg_latency = cur.execute(
                        "SELECT AVG(JULIANDAY(timestamp_sent) - JULIANDAY(timestamp_scheduled)) FROM notification_logs WHERE status = 'success'"
                    ).fetchone()[0]
                    if avg_latency:
                        kpis["avg_delivery_latency_seconds"] = round(
                            avg_latency * 86400, 2
                        )  # Convert days to seconds
            except (sqlite3.Error, TypeError, ZeroDivisionError) as e:
                logger.warning(f"Could not calculate notification KPIs: {e}")

            # --- Fetch Logs ---
            logs_query = cur.execute(
                "SELECT timestamp, level, message, logger_name FROM logs ORDER BY timestamp DESC LIMIT 100"
            )
            logs = [dict(row) for row in logs_query.fetchall()]

        except sqlite3.Error as e:
            logger.error(f"Query failed: {e}")
        finally:
            conn.close()

    # Connect to the address cache database
    addr_conn = get_db_connection(ADDRESS_DB_PATH)
    if addr_conn:
        try:
            kpis["total_cached_addresses"] = addr_conn.cursor().execute(
                "SELECT COUNT(*) FROM addresses"
            ).fetchone()[0]
        except sqlite3.Error as e:
            logger.error(f"Address DB query failed: {e}")
        finally:
            addr_conn.close()

    return render_template("index.html", kpis=kpis, logs=logs)


if __name__ == "__main__":
    app.run(debug=True)
