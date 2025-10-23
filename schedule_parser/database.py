"""
This module provides database utilities for the waste schedule parser.

It includes a context manager for handling SQLite database connections to ensure
they are consistently managed and closed.
"""
import sqlite3
from contextlib import contextmanager

@contextmanager
def get_db_connection(db_path: str):
    """
    A context manager for SQLite database connections.

    This function yields a database connection and ensures that the connection
    is always closed, even if errors occur.

    Args:
        db_path: The path to the SQLite database file.

    Yields:
        A tuple containing the connection and cursor objects.

    Raises:
        sqlite3.Error: If there is an issue with the database connection.
    """
    conn = None
    try:
        conn = sqlite3.connect(db_path)
        yield conn, conn.cursor()
        conn.commit()
    except sqlite3.Error as e:
        if conn:
            conn.rollback()
        # Reraise the exception to be handled by the caller
        raise e
    finally:
        if conn:
            conn.close()
