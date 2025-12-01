"""
This module handles the scheduling and sending of notifications using the WasteManagementFacade.
"""

import asyncio
import logging

from telegram import Bot
from telegram.ext import Application

from schedule_parser.facade import WasteManagementFacade

logger = logging.getLogger(__name__)


async def send_notification(bot: Bot, chat_id: int, message: str) -> None:
    """Sends a single notification message to a user."""
    await bot.send_message(chat_id=chat_id, text=message)


async def check_and_send_notifications(facade: WasteManagementFacade, bot: Bot) -> None:
    """
    Fetches due notifications from the facade and sends them.
    """
    logger.info("Checking for due notifications...")
    notification_tasks = facade.get_due_notifications()

    if not notification_tasks:
        logger.info("No notifications are due.")
        return

    logger.info(f"Found {len(notification_tasks)} notifications to send.")

    # In a real high-volume scenario, you'd use a more robust batching/rate-limiting mechanism.
    # For this example, asyncio.gather with error handling is sufficient.
    chunk_size = 30
    for i in range(0, len(notification_tasks), chunk_size):
        chunk = notification_tasks[i : i + chunk_size]

        # Log pending notifications and prepare coroutines
        coroutines = []
        log_ids = {}  # map coroutine to log_id

        for task in chunk:
            log_id = facade.log_pending_notification(task["subscription_id"])
            if log_id:
                coro = send_notification(bot, task["chat_id"], task["message"])
                coroutines.append(coro)
                log_ids[coro] = (
                    log_id,
                    task,
                )  # Store log_id and task for result processing

        # Run send operations concurrently
        results = await asyncio.gather(*coroutines, return_exceptions=True)

        # Process results and update logs/database
        for coro, result in zip(coroutines, results):
            log_id, task_info = log_ids[coro]
            if not isinstance(result, Exception):
                facade.update_last_notified_date(
                    subscription_id=task_info["subscription_id"],
                    collection_date=task_info["collection_date"],
                )
                facade.update_notification_log(log_id, "success")
                logger.info(
                    f"Successfully sent notification to chat_id {task_info['chat_id']}."
                )
            else:
                error_message = str(result)
                facade.update_notification_log(log_id, "failure", error_message)
                logger.error(
                    f"Failed to send notification to chat_id {task_info['chat_id']}: {error_message}"
                )

        # Wait for 1 second before processing the next chunk to respect rate limits
        if i + chunk_size < len(notification_tasks):
            await asyncio.sleep(1)


async def scheduler(facade: WasteManagementFacade, application: Application) -> None:
    """
    The main scheduler loop that periodically checks for and sends notifications.
    """
    bot = application.bot
    logger.info("Notification scheduler started.")
    while True:
        try:
            await check_and_send_notifications(facade, bot)
        except Exception as e:
            logger.exception(
                f"An error occurred in the notification scheduler loop: {e}"
            )
        # Wait for 1 hour before the next check.
        # In a production environment, this might be a more sophisticated clock-based trigger.
        await asyncio.sleep(3600)
