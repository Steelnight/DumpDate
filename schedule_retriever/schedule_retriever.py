import requests
from ics import Calendar
from database_handler.database_handler import get_db_connection, create_tables, store_events

def retrieve_and_store_schedule(url, db_connection=None):
    """
    Retrieves, parses, and stores an iCalendar schedule from a URL.

    Args:
        url: The URL of the iCalendar file.
        db_connection: An optional database connection. If not provided, a new one
                       will be created and closed.
    """
    conn = db_connection if db_connection else get_db_connection()

    create_tables(conn)

    try:
        response = requests.get(url)
        response.raise_for_status()  # Raise an exception for bad status codes
        calendar = Calendar(response.text)
        store_events(conn, calendar.events)
    finally:
        # Only close the connection if this function created it.
        if not db_connection:
            conn.close()
