# DumpDate
DumpDate is a smart reminder bot that keeps track of the local garbage collection schedule in Dresden and notifies you before pickup

## Running with Docker

1.  **Clone the repository:**
    ```sh
    git clone https://github.com/your-username/dumpdate.git
    cd dumpdate
    ```

2.  **Create an `.env` file:**
    Copy the example file and add your Telegram Bot Token.
    ```sh
    cp .env.example .env
    ```
    Now edit `.env` and paste your token.

3.  **Build and run the application:**
    ```sh
    docker-compose up --build
    ```

This command will:
*   Build the Docker image for the application.
*   Run the `build_cache.py` script to create the address database.
*   Start the Telegram bot.
*   Start the web dashboard, which will be accessible at `http://localhost:5000`.

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
