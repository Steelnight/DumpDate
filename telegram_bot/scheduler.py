"""
This module handles the scheduling and sending of notifications.
"""
import asyncio
import sqlite3
from datetime import date, timedelta, datetime
from telegram import Bot
from .subscription_manager import get_all_subscriptions, update_last_notified
from .address_matcher import get_address_by_id
from schedule_parser.config import WASTE_SCHEDULE_DB_PATH

async def send_notification(bot: Bot, chat_id: int, message: str) -> None:
    """Sends a notification to a user."""
    await bot.send_message(chat_id=chat_id, text=message)

def get_upcoming_collections(address_id: int, db_path: str = WASTE_SCHEDULE_DB_PATH) -> list:
    """Retrieve upcoming waste collections for a given address."""
    address = get_address_by_id(address_id)
    if not address:
        return []

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    cur.execute(
        "SELECT date, waste_type FROM waste_events WHERE original_address = ?",
        (address,),
    )
    events = cur.fetchall()
    conn.close()
    return events

async def check_and_send_notifications(bot: Bot) -> None:
    """Gathers all due notifications and passes them to the bulk sender."""
    subscriptions = get_all_subscriptions()
    now = datetime.now()
    today = now.date()
    tomorrow = today + timedelta(days=1)

    notification_tasks = []

    for sub_id, chat_id, address_id, notification_time, last_notified_str in subscriptions:
        collections = get_upcoming_collections(address_id)
        last_notified = date.fromisoformat(last_notified_str) if last_notified_str else None

        for collection_date_str, waste_type in collections:
            collection_date = date.fromisoformat(collection_date_str)

            if last_notified == collection_date:
                continue

            message = None
            # Evening before notification (7 PM)
            if notification_time == "evening" and collection_date == tomorrow and now.hour == 19:
                emoji = get_waste_type_emoji(waste_type)
                message = f"{emoji} {waste_type} ist für morgen geplant!"

            # Morning of notification (6 AM)
            elif notification_time == "morning" and collection_date == today and now.hour == 6:
                emoji = get_waste_type_emoji(waste_type)
                message = f"{emoji} {waste_type} wird heute abgeholt!"

            if message:
                notification_tasks.append({
                    "sub_id": sub_id,
                    "chat_id": chat_id,
                    "message": message,
                    "collection_date": collection_date,
                })

    if notification_tasks:
        # This function will be implemented in the next step
        await send_bulk_notifications(bot, notification_tasks)

def log_pending_notification(sub_id: int, db_path: str = WASTE_SCHEDULE_DB_PATH) -> int:
    """Logs a pending notification and returns the log ID."""
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO notification_logs (subscription_id, status) VALUES (?, 'pending')",
        (sub_id,),
    )
    log_id = cur.lastrowid
    conn.commit()
    conn.close()
    return log_id


def update_notification_log(
    log_id: int,
    status: str,
    error_message: str = None,
    db_path: str = WASTE_SCHEDULE_DB_PATH,
) -> None:
    """Updates the status of a notification log."""
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute(
        "UPDATE notification_logs SET status = ?, error_message = ?, timestamp_sent = CURRENT_TIMESTAMP WHERE id = ?",
        (status, error_message, log_id),
    )
    conn.commit()
    conn.close()


async def send_bulk_notifications(bot: Bot, tasks: list) -> None:
    """Sends notifications in bulk with rate limiting and logs the outcomes."""
    chunk_size = 30
    for i in range(0, len(tasks), chunk_size):
        chunk = tasks[i:i + chunk_size]

        # Log pending notifications and prepare coroutines
        log_ids = [log_pending_notification(task["sub_id"]) for task in chunk]
        coroutines = [
            send_notification(bot, task["chat_id"], task["message"]) for task in chunk
        ]

        # Run send operations concurrently
        results = await asyncio.gather(*coroutines, return_exceptions=True)

        # Process results and update logs/database
        for task, log_id, result in zip(chunk, log_ids, results):
            if not isinstance(result, Exception):
                update_last_notified(
                    task["sub_id"], task["collection_date"].isoformat()
                )
                update_notification_log(log_id, "success")
            else:
                error_message = str(result)
                update_notification_log(log_id, "failure", error_message)
                print(
                    f"Failed to send notification to {task['chat_id']}: {error_message}"
                )

        # Wait for 1 second before processing the next chunk
        if i + chunk_size < len(tasks):
            await asyncio.sleep(1)

def get_waste_type_emoji(waste_type: str) -> str:
    """Returns an emoji for a given waste type."""
    if "bio" in waste_type.lower():
        return "🟢"
    if "papier" in waste_type.lower():
        return "🔵"
    if "verpackung" in waste_type.lower():
        return "🟡"
    if "rest" in waste_type.lower():
        return "⚫"
    return "🗑️"

async def scheduler(bot: Bot) -> None:
    """Runs the notification checker periodically."""
    while True:
        await check_and_send_notifications(bot)
        await asyncio.sleep(3600)  # Check every hour
