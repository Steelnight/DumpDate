# DumpDate
DumpDate is a smart reminder bot that keeps track of the local garbage collection schedule in Dresden and notifies you before pickup

# Planned Features

🗑️ 1. Automated Schedule Retrieval
	•	Integrates with the waste calendar of the city of Dresden 
	•	Supports multiple waste types (residual, bio, paper, recycling, special).

💬 2. Telegram Notifications
	•	Sends push reminders via Telegram bot.
	•	Configurable time of day (e.g. evening before, morning of collection).
	•	Optional group chat notifications for shared households.
	•	Uses Markdown for clean, emoji-enhanced messages (e.g. 🟢 Recycling tomorrow!).

🧠 3. Smart Scheduling
	•	Automatically skips past dates or holidays.
	•	Detects next collection day dynamically, even if the schedule changes.

⚙️ 4. Flexible Setup
	•	Simple .yaml or .env configuration file for:
	•	Adress
	•	Waste categories
	•	Telegram Bot Token + Chat ID
	•	Reminder lead time
	•	Runs as a Docker container

📊 5. Status & Logs
	•	Web dashboard or console mode showing:
	•	Upcoming pickups
	•	Last notification sent
	•	System uptime
	•	Optional Prometheus metrics export (for monitoring).

🌍 6. Multi-User / Household Support
	•	One instance can manage multiple addresses or users.
	•	Configurable chat mapping per location.
\n## High-Performance Caching\n\nThis library uses a high-performance SQLite database for address lookups to ensure fast and efficient operation. Before using the library for the first time, you must build the local address cache.\n\nTo do this, run the following command from the root of the project:\n\n```bash\npoetry run python build_cache.py\n```\n\nThis will create an `address_lookup.db` file in the project's root directory. It is recommended to run this command periodically (e.g., once a week or month) to keep the address data up-to-date.
