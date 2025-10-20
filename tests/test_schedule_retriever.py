import unittest
import sqlite3
from unittest.mock import patch, MagicMock
from schedule_retriever.schedule_retriever import retrieve_and_store_schedule

class TestScheduleRetriever(unittest.TestCase):

    @patch('schedule_retriever.schedule_retriever.requests.get')
    def test_retrieve_and_store_schedule(self, mock_get):
        # Create an in-memory database connection for the test
        conn = sqlite3.connect(':memory:')

        # Mock the response from requests.get
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = """
BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Test Cal//EN
BEGIN:VEVENT
UID:12345
SUMMARY:Test Event 1
DTSTART:20251020T100000Z
DTEND:20251020T110000Z
DESCRIPTION:This is a test event.
END:VEVENT
BEGIN:VEVENT
UID:67890
SUMMARY:Test Event 2
DTSTART:20251021T100000Z
DTEND:20251021T110000Z
DESCRIPTION:This is another test event.
END:VEVENT
END:VCALENDAR
"""
        mock_get.return_value = mock_response

        # Call the function with the in-memory database connection
        retrieve_and_store_schedule('http://fake-url.com/cal.ics', db_connection=conn)

        # Verify the data was stored in the database
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM events ORDER BY uid')
        rows = cursor.fetchall()
        self.assertEqual(len(rows), 2)
        # Manually set the row factory for this cursor to access by column name
        rows = [dict(zip([d[0] for d in cursor.description], row)) for row in rows]
        self.assertEqual(rows[0]['uid'], '12345')
        self.assertEqual(rows[1]['uid'], '67890')
        conn.close()

if __name__ == '__main__':
    unittest.main()
