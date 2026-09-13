# SB24 Text Tools

Telegram bot for simple, everyday text utilities.

## Features

- Persistent reply keyboard below the chat box
- Sort words alphabetically
- Count characters, words, and lines
- Rearrange letters alphabetically
- Built-in examples for easy testing
- `/start`, `/menu`, and `/help` commands
- Admin-only `/stats`
- SQLite user tracking
- Render worker deployment configuration

## Environment variables

Set these variables on your hosting platform:

- `BOT_TOKEN` — Telegram BotFather token
- `ADMIN_IDS` — comma-separated Telegram numeric admin IDs
- `DB_PATH` — optional SQLite path

## Run locally

```bash
pip install -r requirements.txt
python bot.py
```

SB24 is designed as a simple text utility bot. It does not provide financial advice, investment signals, or guaranteed results.
