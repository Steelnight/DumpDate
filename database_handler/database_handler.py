import sqlite3

def get_db_connection(db_name='schedule.db'):
    """
    Establishes a connection to the SQLite database.

    Args:
        db_name: The name of the database file. Defaults to 'schedule.db'.

    Returns:
        A connection object.
    """
    conn = sqlite3.connect(db_name)
    conn.row_factory = sqlite3.Row
    return conn

def create_tables(conn):
    """
    Creates the necessary tables in the database if they don't exist.

    Args:
        conn: The database connection object.
    """
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS events (
            uid TEXT PRIMARY KEY,
            name TEXT,
            begin TEXT,
            end TEXT,
            description TEXT
        )
    ''')
    conn.commit()

def store_events(conn, events):
    """
    Stores multiple events in the database in a single transaction.

    Args:
        conn: The database connection object.
        events: A list of Event objects from the ics library.
    """
    cursor = conn.cursor()
    event_data = [
        (event.uid, event.name, str(event.begin), str(event.end), event.description)
        for event in events
    ]
    cursor.executemany('''
        INSERT OR REPLACE INTO events (uid, name, begin, end, description)
        VALUES (?, ?, ?, ?, ?)
    ''', event_data)
    conn.commit()
