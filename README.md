# Gold Master Hub

Telegram bot providing XAUUSD/gold trading tools, calculators, market-session references, and forex education.

## Features

- Persistent Telegram reply keyboard below the chat box
- Gold/XAUUSD reference tools
- Position-size calculator
- Profit/loss calculator
- Major forex session references
- Forex education basics
- General market information
- Admin-only `/stats`
- SQLite user tracking
- Render worker deployment configuration

## Environment variables

Set these environment variables on your hosting platform:

- `BOT_TOKEN` — Telegram BotFather token
- `ADMIN_IDS` — comma-separated Telegram numeric admin IDs
- `ADMIN_USERNAME` — optional admin username shown in Contact Admin
- `DB_PATH` — optional SQLite path

## Run locally

```bash
pip install -r requirements.txt
python bot.py
```

The bot is educational/informational and does not provide financial advice or guarantee trading results.
