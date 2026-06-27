# 📡 Grade Watcher Bot

A Discord bot that monitors your KIET LMS grades and sends you a DM the moment something changes — so you don't have to keep refreshing the portal.

---

## How It Works

The bot logs into the KIET LMS on your behalf, scrapes your Grade History page every **5 minutes**, and hashes the result. If the hash differs from the last check, it diffs the old and new grade lists and DMs you only the changed entries.

```
User registers via Discord DM
        │
        ▼
Bot logs into LMS → fetches grade page → hashes it
        │
        ▼ (every 5 min)
Hash changed? → diff grades → DM user the updates
```

---

## Features

- 🔐 Per-user login with LMS session management and auto re-login on session expiry
- 🔔 Instant Discord DM when any grade is posted or updated
- 📘 On-demand grade summary with `!recheck`
- 🗂️ Persistent grade cache — survives bot restarts
- ☁️ Ready to deploy on [Render](https://render.com) (free tier)

---

## Commands

All commands are sent as **Discord DMs to the bot**.

| Command | Description |
|---|---|
| `!register <student_id> <password>` | Link your LMS account and start the watcher |
| `!recheck` | Fetch and display your current grades right now |

> ⚠️ Send `!register` in a **DM**, not a public server channel — your password is in plaintext.

---

## Setup (Local)

### 1. Prerequisites

- Python 3.10+
- A Discord bot token ([create one here](https://discord.com/developers/applications))
- Your KIET LMS credentials

### 2. Clone & Install

```bash
git clone https://github.com/your-username/grade-watcher-bot.git
cd grade-watcher-bot
pip install -r requirements.txt
```

### 3. Configure Environment

Create a `.env` file in the project root:

```env
DISCORD_BOT_TOKEN=your_discord_bot_token_here
```

### 4. Discord Bot Settings

In the [Discord Developer Portal](https://discord.com/developers/applications), make sure your bot has:

- **Message Content Intent** enabled (under Bot → Privileged Gateway Intents)
- **DM permissions** — the bot communicates exclusively via DMs

### 5. Run

```bash
python main.py
```

You should see `✅ Logged in as <BotName>` in the console.

---

## Deploy on Render (Free)

A `render.yaml` is included for one-click deployment.

1. Push the repo to GitHub
2. Go to [render.com](https://render.com) → New → Web Service → connect your repo
3. Render auto-detects `render.yaml` and configures the service
4. Add the `DISCORD_BOT_TOKEN` environment variable under **Environment** in the Render dashboard
5. Deploy — the bot stays online 24/7 on Render's free tier

> **Note:** Render's free tier spins down after inactivity. Use the `Always On` option or a cron ping service (e.g. UptimeRobot) to keep the bot awake.

---

## Project Structure

```
grade-watcher-bot/
├── main.py                  # Bot logic — login, scraping, Discord events
├── requirements.txt         # Python dependencies
├── render.yaml              # Render deployment config
├── .gitignore               # Excludes .env and runtime data files
└── README.md
```

Runtime files created automatically (not committed):

```
user_credentials.json        # Stored LMS credentials per Discord user
{user_id}_hash.txt           # SHA-256 hash of last known grade table
{user_id}_grades.json        # Cached grade list for diffing
grade_watcher.log            # Application log
```

---

## Dependencies

| Package | Purpose |
|---|---|
| `requests` | HTTP sessions for LMS login and scraping |
| `beautifulsoup4` | HTML parsing of the grade table |
| `discord.py` | Discord bot framework |
| `python-dotenv` | Load `.env` into environment variables |

---

## Security Notes

- **Credentials are stored in plaintext** in `user_credentials.json`. Avoid deploying this bot for anyone other than yourself without encrypting the credentials file first.
- The bot disables SSL verification (`verify=False`) when talking to the KIET LMS due to its self-signed certificate. This is a known limitation.
- Never commit `.env` or the runtime data files — the `.gitignore` already excludes them.

---

## Known Limitations & Planned Improvements

- [ ] Encrypt stored credentials (e.g. with `cryptography` / Fernet)
- [ ] Support multiple concurrent users without blocking the event loop (move watcher to a proper background task)
- [ ] `!unregister` command to remove credentials and stop the watcher
- [ ] `!status` command to confirm the watcher is running for a user
- [ ] Configurable check interval per user
- [ ] Replace file-based storage with a lightweight DB (SQLite)
- [ ] Graceful handling when the LMS is down

---

## License

MIT — use it, break it, fix it.
