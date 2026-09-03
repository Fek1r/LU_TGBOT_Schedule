# LU Schedule Bot

A Telegram bot for **Latvijas Universitāte** students — tracks your class schedule, sends cancellation alerts, and reminds you before each lesson.

Scrapes [lekciju-saraksts.lu.lv](https://lekciju-saraksts.lu.lv) directly — no third-party APIs.

---

## Features

- **Schedule on demand** — today, tomorrow, this week, next week
- **Morning digest** — daily schedule sent at a configurable time
- **Cancellation alerts** — monitors lesson status changes and notifies instantly
- **Lesson reminders** — N minutes before each class
- **Break times** — shows the gap between lessons right in the schedule
- **Any group** — 1669 LU groups, searchable from inside the bot; every subscriber picks their own
- **Multi-subscriber** — anyone can subscribe via `/start`, data stored in SQLite
- **3 interface languages** — Русский / English / Latviešu, picked via inline button
- **Inline navigation** — single message edited on each tap, chat stays clean

---

## Preview

```
📅 Tuesday, 01.09.2026

┌ 08:30 – 10:10 ─ Lecture
│ 📚 Diskrētā matemātika datoriķiem
│ 🏛 ALFA(110) (1. stāvs), Jelgavas iela 3
└ 👤 Juris Smotrovs

⏸ 20 min

┌ 10:30 – 12:10 ─ Lecture
│ 📚 Algoritmi un programmēšan
│ 🏛 ALFA(110) (1. stāvs), Jelgavas iela 3
└ 👤 Uldis Straujums, Jānis Zuters
```

---

## Getting Started

### 1. Clone the repository

```bash
git clone https://github.com/Fek1r/LU_TGBOT_Schedule.git
cd LU_TGBOT_Schedule
```

### 2. Create a Telegram bot

1. Open [@BotFather](https://t.me/BotFather) and send `/newbot`
2. Follow the instructions and copy the token (`123456789:ABC-DEF...`)

### 3. Configure environment

```bash
cp .env.example .env
```

Fill in `.env`:

```env
TELEGRAM_BOT_TOKEN=your_token
GROUP_ID=26R-22302-PLK-1        # default group for new subscribers; each user can change it in the bot
MORNING_NOTIFY_TIME=07:00       # time to send the morning digest
REMINDER_MINUTES_BEFORE=15      # how many minutes before class to remind
CHECK_INTERVAL_MINUTES=20       # how often to check for cancellations
DEFAULT_LANGUAGE=ru             # fallback language: ru / en / lv
TIMEZONE=Europe/Riga            # the university's timezone, not the server's
```

> The group ID can be found in the URL on lekciju-saraksts.lu.lv, e.g. `26R-22302-PLK-1`

### 4. Install dependencies

```bash
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 5. Run

```bash
python main.py
```

Open the bot in Telegram, send `/start`, pick a language — you're subscribed.

---

## Running on a Server

### screen / tmux (quick)

```bash
screen -S lu-bot
source venv/bin/activate
python main.py
# Ctrl+A, D to detach — screen -r lu-bot to return
```

### systemd (recommended)

Create `/etc/systemd/system/lu-bot.service`:

```ini
[Unit]
Description=LU Schedule Telegram Bot
After=network.target

[Service]
Type=simple
User=your_user
WorkingDirectory=/path/to/lu-schedule-bot
ExecStart=/path/to/lu-schedule-bot/venv/bin/python main.py
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable lu-bot
sudo systemctl start lu-bot
journalctl -u lu-bot -f   # view logs
```

---

## Project Structure

```
lu-schedule-bot/
├── main.py          — entry point
├── config.py        — settings from .env
├── scraper.py       — scrapes lekciju-saraksts.lu.lv
├── groups.py        — the group catalogue: search and cache
├── fetcher.py       — cached, de-duplicated access to the scraper
├── storage.py       — SQLite: subscribers + lesson states
├── locales.py       — UI strings (ru / en / lv)
├── formatter.py     — language-aware message formatting
├── scheduler.py     — APScheduler: morning digest, cancellations, reminders
├── bot.py           — aiogram handlers, inline navigation
├── .env.example     — environment variables template
└── requirements.txt
```

## Stack

| | |
|---|---|
| Bot framework | [aiogram 3.x](https://github.com/aiogram/aiogram) |
| Scheduler | [APScheduler 3.x](https://apscheduler.readthedocs.io) |
| Database | SQLite via [aiosqlite](https://github.com/omnilib/aiosqlite) |
| Scraping | [requests](https://requests.readthedocs.io) + [BeautifulSoup4](https://www.crummy.com/software/BeautifulSoup/) |
