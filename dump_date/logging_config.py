"""
This module sets up a database logging handler for the application.
"""
import logging
import sqlite3
from logging import Handler, LogRecord
from schedule_parser.config import WASTE_SCHEDULE_DB_PATH


class SQLiteHandler(Handler):
    """
    A logging handler that writes records to an SQLite database.
    """

    def __init__(self, db_path: str = WASTE_SCHEDULE_DB_PATH):
        super().__init__()
        self.db_path = db_path

    def emit(self, record: LogRecord) -> None:
        """
        Writes the log record to the database.
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO logs (level, message, logger_name) VALUES (?, ?, ?)",
                (record.levelname, self.format(record), record.name),
            )
            conn.commit()
            conn.close()
        except Exception as e:
            # If logging to the DB fails, we can't do much
            print(f"CRITICAL: Could not write log to database: {e}")


def setup_database_logging() -> None:
    """
    Configures the root logger to use the SQLiteHandler.
    """
    # Get the root logger
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)  # Set the lowest level to capture

    # Remove any existing handlers to avoid duplicates
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    # Create and add the database handler
    db_handler = SQLiteHandler()
    db_handler.setLevel(logging.INFO)
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    db_handler.setFormatter(formatter)
    logger.addHandler(db_handler)

    # Add a console handler as well for immediate feedback
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    logging.info("Logging configured to use database and console.")
