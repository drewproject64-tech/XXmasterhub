import asyncio
import logging
import os
import sqlite3
from datetime import datetime, timezone
from html import escape

from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    KeyboardButton,
    Message,
    ReplyKeyboardMarkup,
)

TOKEN = os.getenv("BOT_TOKEN", "").strip()
ADMIN_IDS = {
    int(value.strip())
    for value in os.getenv("ADMIN_IDS", "").split(",")
    if value.strip().isdigit()
}

DB_PATH = os.getenv("DB_PATH", "gold_master_hub.db")

if not TOKEN:
    raise RuntimeError("BOT_TOKEN environment variable is required")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("gold_master_hub")

bot = Bot(
    token=TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML),
)
dp = Dispatcher()


def db_connect():
    connection = sqlite3.connect(DB_PATH)
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            joined_at TEXT NOT NULL,
            last_seen TEXT NOT NULL
        )
        """
    )
    connection.commit()
    return connection


def remember_user(message: Message) -> None:
    if not message.from_user:
        return

    now = datetime.now(timezone.utc).isoformat()
    connection = db_connect()
    connection.execute(
        """
        INSERT INTO users (user_id, username, first_name, joined_at, last_seen)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET
            username = excluded.username,
            first_name = excluded.first_name,
            last_seen = excluded.last_seen
        """,
        (
            message.from_user.id,
            message.from_user.username,
            message.from_user.first_name,
            now,
            now,
        ),
    )
    connection.commit()
    connection.close()


def main_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="📊 Gold Tools"),
                KeyboardButton(text="🧮 Trading Calculators"),
            ],
            [
                KeyboardButton(text="🕒 Market Sessions"),
                KeyboardButton(text="📚 Forex Academy"),
            ],
            [
                KeyboardButton(text="📈 Market Information"),
                KeyboardButton(text="📰 Gold Market Updates"),
            ],
            [
                KeyboardButton(text="⚙️ Settings"),
                KeyboardButton(text="👤 Contact Admin"),
            ],
        ],
        resize_keyboard=True,
        is_persistent=True,
        input_field_placeholder="Choose an option",
    )


WELCOME_TEXT = (
    "<b>👋 Welcome to Gold Master Hub</b>\n\n"
    "Your central hub for gold trading resources and forex education.\n\n"
    "Use the menu below to explore XAUUSD tools, trading calculators, market-session guides, "
    "educational materials, and useful market references.\n\n"
    "⚠️ <i>For educational and informational purposes only. This bot does not provide financial advice "
    "or guarantee trading results.</i>"
)


class CalculatorStates(StatesGroup):
    risk_balance = State()
    risk_percent = State()
    risk_stop_distance = State()

    profit_entry = State()
    profit_exit = State()
    profit_size = State()


async def send_home(message: Message) -> None:
    remember_user(message)
    await message.answer(WELCOME_TEXT, reply_markup=main_keyboard())


@dp.message(CommandStart())
async def start_handler(message: Message, state: FSMContext):
    await state.clear()
    await send_home(message)


@dp.message(Command("menu"))
async def menu_handler(message: Message, state: FSMContext):
    await state.clear()
    await send_home(message)


@dp.message(Command("help"))
async def help_handler(message: Message):
    remember_user(message)
    text = (
        "<b>🆘 Gold Master Hub Help</b>\n\n"
        "Choose a section from the keyboard below.\n\n"
        "<b>Gold Tools</b> — basic XAUUSD reference tools.\n"
        "<b>Trading Calculators</b> — position sizing and P/L estimates.\n"
        "<b>Market Sessions</b> — UTC session windows.\n"
        "<b>Forex Academy</b> — trading concepts and terminology.\n"
        "<b>Market Information</b> — general XAUUSD reference data.\n\n"
        "Use /menu at any time to restore the main menu."
    )
    await message.answer(text, reply_markup=main_keyboard())


@dp.message(F.text == "📊 Gold Tools")
async def gold_tools_handler(message: Message):
    remember_user(message)
    text = (
        "<b>📊 Gold Tools</b>\n\n"
        "• XAUUSD symbol reference\n"
        "• Pip/point basics\n"
        "• Gold market terminology\n"
        "• Simple trading checklists\n\n"
        "<b>XAUUSD</b> represents gold priced in US dollars.\n\n"
        "⚠️ Always confirm instrument specifications with your broker before trading."
    )
    await message.answer(text, reply_markup=main_keyboard())


@dp.message(F.text == "🧮 Trading Calculators")
async def calculator_menu_handler(message: Message):
    remember_user(message)
    text = (
        "<b>🧮 Trading Calculators</b>\n\n"
        "1. <b>Position Size</b>\n"
        "Estimate position size from balance, risk %, and stop distance.\n\n"
        "2. <b>Profit/Loss Estimate</b>\n"
        "Estimate gross P/L from entry, exit, and position size.\n\n"
        "Send /position for the position-size calculator or /pnl for the P/L calculator."
    )
    await message.answer(text, reply_markup=main_keyboard())


@dp.message(Command("position"))
async def position_start(message: Message, state: FSMContext):
    remember_user(message)
    await state.set_state(CalculatorStates.risk_balance)
    await message.answer(
        "<b>🧮 Position Size Calculator</b>\n\n"
        "Step 1/3: Enter your account balance in USD.\n\n"
        "Example: <code>1000</code>",
        reply_markup=main_keyboard(),
    )


@dp.message(CalculatorStates.risk_balance)
async def position_balance(message: Message, state: FSMContext):
    value = parse_positive_number(message.text)
    if value is None:
        await message.answer("Please enter a valid positive number, e.g. <code>1000</code>.")
        return

    await state.update_data(balance=value)
    await state.set_state(CalculatorStates.risk_percent)
    await message.answer(
        "Step 2/3: Enter the percentage of your balance you are willing to risk.\n\n"
        "Example: <code>1</code> for 1% risk."
    )


@dp.message(CalculatorStates.risk_percent)
async def position_risk(message: Message, state: FSMContext):
    value = parse_positive_number(message.text)
    if value is None or value > 100:
        await message.answer("Enter a risk percentage between 0 and 100, e.g. <code>1</code>.")
        return

    await state.update_data(risk_percent=value)
    await state.set_state(CalculatorStates.risk_stop_distance)
    await message.answer(
        "Step 3/3: Enter your stop-loss distance in USD per ounce.\n\n"
        "Example: <code>10</code>"
    )


@dp.message(CalculatorStates.risk_stop_distance)
async def position_stop(message: Message, state: FSMContext):
    value = parse_positive_number(message.text)
    if value is None:
        await message.answer("Please enter a valid positive number, e.g. <code>10</code>.")
        return

    data = await state.get_data()
    risk_amount = data["balance"] * data["risk_percent"] / 100
    estimated_ounces = risk_amount / value

    await state.clear()
    await message.answer(
        "<b>✅ Position Size Estimate</b>\n\n"
        f"Balance: <code>${data['balance']:,.2f}</code>\n"
        f"Risk: <code>{data['risk_percent']:.2f}%</code>\n"
        f"Risk amount: <code>${risk_amount:,.2f}</code>\n"
        f"Stop distance: <code>${value:,.2f}</code>\n\n"
        f"Estimated exposure: <code>{estimated_ounces:.4f} oz</code>\n\n"
        "This is a simplified educational estimate. Broker contract sizes, spread, swaps, leverage, and instrument specifications can change the actual result.",
        reply_markup=main_keyboard(),
    )


@dp.message(Command("pnl"))
async def pnl_start(message: Message, state: FSMContext):
    remember_user(message)
    await state.set_state(CalculatorStates.profit_entry)
    await message.answer(
        "<b>🧮 Profit/Loss Calculator</b>\n\n"
        "Step 1/3: Enter your entry price.\n\n"
        "Example: <code>2500</code>"
    )


@dp.message(CalculatorStates.profit_entry)
async def pnl_entry(message: Message, state: FSMContext):
    value = parse_positive_number(message.text)
    if value is None:
        await message.answer("Please enter a valid price.")
        return

    await state.update_data(entry=value)
    await state.set_state(CalculatorStates.profit_exit)
    await message.answer("Step 2/3: Enter your exit price.")


@dp.message(CalculatorStates.profit_exit)
async def pnl_exit(message: Message, state: FSMContext):
    value = parse_positive_number(message.text)
    if value is None:
        await message.answer("Please enter a valid price.")
        return

    await state.update_data(exit=value)
    await state.set_state(CalculatorStates.profit_size)
    await message.answer(
        "Step 3/3: Enter the position size in ounces.\n\n"
        "Example: <code>1</code>"
    )


@dp.message(CalculatorStates.profit_size)
async def pnl_size(message: Message, state: FSMContext):
    value = parse_positive_number(message.text)
    if value is None:
        await message.answer("Please enter a valid positive number.")
        return

    data = await state.get_data()
    raw_pnl = (data["exit"] - data["entry"]) * value
    direction = "Profit" if raw_pnl >= 0 else "Loss"

    await state.clear()
    await message.answer(
        "<b>✅ P/L Estimate</b>\n\n"
        f"Entry: <code>${data['entry']:,.2f}</code>\n"
        f"Exit: <code>${data['exit']:,.2f}</code>\n"
        f"Size: <code>{value:,.4f} oz</code>\n\n"
        f"{direction}: <code>${abs(raw_pnl):,.2f}</code>\n\n"
        "This simplified estimate excludes spread, commissions, swaps, slippage, and broker-specific contract rules.",
        reply_markup=main_keyboard(),
    )


@dp.message(F.text == "🕒 Market Sessions")
async def sessions_handler(message: Message):
    remember_user(message)
    text = (
        "<b>🕒 Major Forex Sessions (UTC)</b>\n\n"
        "🇦🇺 Sydney: approximately 22:00–07:00\n"
        "🇯🇵 Tokyo: approximately 00:00–09:00\n"
        "🇬🇧 London: approximately 08:00–17:00\n"
        "🇺🇸 New York: approximately 13:00–22:00\n\n"
        "Session times can shift because of daylight-saving changes. Treat these as general references and verify current market hours."
    )
    await message.answer(text, reply_markup=main_keyboard())


@dp.message(F.text == "📚 Forex Academy")
async def academy_handler(message: Message):
    remember_user(message)
    text = (
        "<b>📚 Forex Academy</b>\n\n"
        "<b>Risk Management</b>\n"
        "Learn how position size, stop distance, and account risk interact.\n\n"
        "<b>Spread</b>\n"
        "The difference between the bid and ask price.\n\n"
        "<b>Leverage</b>\n"
        "A mechanism that can increase market exposure relative to account equity and also increase risk.\n\n"
        "<b>Volatility</b>\n"
        "The degree to which price moves over time. Gold can move rapidly around major economic events.\n\n"
        "Educational content only — not financial advice."
    )
    await message.answer(text, reply_markup=main_keyboard())


@dp.message(F.text == "📈 Market Information")
async def market_info_handler(message: Message):
    remember_user(message)
    text = (
        "<b>📈 XAUUSD Market Information</b>\n\n"
        "XAUUSD is commonly quoted as gold priced in US dollars per troy ounce.\n\n"
        "Gold can be influenced by factors such as:\n"
        "• US dollar strength\n"
        "• Interest-rate expectations\n"
        "• Inflation expectations\n"
        "• Central-bank policy\n"
        "• Geopolitical risk\n"
        "• Economic data and market sentiment\n\n"
        "This section provides general educational information rather than live market data."
    )
    await message.answer(text, reply_markup=main_keyboard())


@dp.message(F.text == "📰 Gold Market Updates")
async def updates_handler(message: Message):
    remember_user(message)
    text = (
        "<b>📰 Gold Market Updates</b>\n\n"
        "This bot does not currently provide a live news feed.\n\n"
        "For responsible market research, follow reputable financial-data sources and check economic calendars before making trading decisions.\n\n"
        "You can add a live news/API integration later without changing the main menu."
    )
    await message.answer(text, reply_markup=main_keyboard())


@dp.message(F.text == "⚙️ Settings")
async def settings_handler(message: Message):
    remember_user(message)
    text = (
        "<b>⚙️ Settings</b>\n\n"
        "The main keyboard is kept visible for easier navigation.\n\n"
        "Commands available:\n"
        "/menu — show the main menu\n"
        "/help — show help\n"
        "/position — position-size calculator\n"
        "/pnl — P/L calculator"
    )
    await message.answer(text, reply_markup=main_keyboard())


@dp.message(F.text == "👤 Contact Admin")
async def contact_admin_handler(message: Message):
    remember_user(message)
    admin_username = os.getenv("ADMIN_USERNAME", "")
    if admin_username:
        contact_line = f"Contact admin: @{escape(admin_username.lstrip('@'))}"
    else:
        contact_line = "Please configure ADMIN_USERNAME in the bot environment to display the admin contact."

    await message.answer(
        "<b>👤 Contact Admin</b>\n\n" + contact_line,
        reply_markup=main_keyboard(),
    )


@dp.message(Command("stats"))
async def stats_handler(message: Message):
    remember_user(message)

    if not message.from_user or message.from_user.id not in ADMIN_IDS:
        await message.answer("This command is available to admins only.")
        return

    connection = db_connect()
    total_users = connection.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    active_7d = connection.execute(
        "SELECT COUNT(*) FROM users WHERE last_seen >= ?",
        ((datetime.now(timezone.utc)).timestamp() - 7 * 86400,),
    ).fetchone()[0]
    connection.close()

    # The last_seen field is stored as ISO text, so perform the active calculation robustly.
    connection = db_connect()
    rows = connection.execute("SELECT last_seen FROM users").fetchall()
    connection.close()

    now = datetime.now(timezone.utc)
    active_count = 0
    for (last_seen,) in rows:
        try:
            dt = datetime.fromisoformat(last_seen)
            if (now - dt).total_seconds() <= 7 * 86400:
                active_count += 1
        except ValueError:
            continue

    await message.answer(
        "<b>📊 Gold Master Hub Stats</b>\n\n"
        f"Total users: <code>{total_users}</code>\n"
        f"Active in last 7 days: <code>{active_count}</code>\n\n"
        f"Server time: <code>{now.strftime('%Y-%m-%d %H:%M UTC')}</code>"
    )


def parse_positive_number(text: str | None) -> float | None:
    if not text:
        return None
    try:
        value = float(text.replace(",", "").strip())
    except ValueError:
        return None
    if value <= 0:
        return None
    return value


@dp.message()
async def fallback_handler(message: Message):
    remember_user(message)
    await message.answer(
        "I didn't recognize that input. Use the buttons below or /help for the available options.",
        reply_markup=main_keyboard(),
    )


async def main() -> None:
    await bot.delete_webhook(drop_pending_updates=True)
    logger.info("Gold Master Hub bot starting")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
