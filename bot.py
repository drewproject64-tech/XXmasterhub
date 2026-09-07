import asyncio
import logging
import os
import sqlite3
from datetime import datetime, timezone

from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import KeyboardButton, Message, ReplyKeyboardMarkup

TOKEN = os.getenv("BOT_TOKEN", "").strip()
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
            [KeyboardButton(text="📊 Gold Tools")],
            [KeyboardButton(text="🧮 Trading Calculators")],
            [KeyboardButton(text="📚 Forex Academy")],
        ],
        resize_keyboard=True,
        is_persistent=True,
        input_field_placeholder="Choose an option",
    )


WELCOME_TEXT = (
    "<b>👋 Welcome to Gold Master Hub</b>\n\n"
    "Your central hub for gold trading resources and forex education.\n\n"
    "Use the three buttons below to access Gold Tools, Trading Calculators, and Forex Academy.\n\n"
    "⚠️ <i>For educational and informational purposes only. This bot does not provide financial advice or guarantee trading results.</i>"
)


class CalculatorStates(StatesGroup):
    risk_balance = State()
    risk_percent = State()
    risk_stop_distance = State()

    profit_entry = State()
    profit_exit = State()
    profit_size = State()


def parse_positive_number(value: str | None) -> float | None:
    if not value:
        return None
    try:
        number = float(value.replace(",", "").strip())
    except (TypeError, ValueError):
        return None
    return number if number > 0 else None


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
    await message.answer(
        "<b>🆘 Gold Master Hub Help</b>\n\n"
        "Use the three main buttons below:\n\n"
        "<b>📊 Gold Tools</b> — XAUUSD tools and trading references.\n"
        "<b>🧮 Trading Calculators</b> — position sizing and P/L estimates.\n"
        "<b>📚 Forex Academy</b> — forex concepts and education.\n\n"
        "Commands:\n"
        "/menu — restore the main menu\n"
        "/help — show this help\n"
        "/position — position-size calculator\n"
        "/pnl — P/L calculator",
        reply_markup=main_keyboard(),
    )


@dp.message(F.text == "📊 Gold Tools")
async def gold_tools_handler(message: Message):
    remember_user(message)
    await message.answer(
        "<b>📊 Gold Tools</b>\n\n"
        "• XAUUSD symbol reference\n"
        "• Pip/point basics\n"
        "• Gold market terminology\n"
        "• Simple trading checklists\n\n"
        "<b>XAUUSD</b> represents gold priced in US dollars.\n\n"
        "⚠️ Always confirm instrument specifications with your broker before trading.",
        reply_markup=main_keyboard(),
    )


@dp.message(F.text == "🧮 Trading Calculators")
async def calculator_menu_handler(message: Message):
    remember_user(message)
    await message.answer(
        "<b>🧮 Trading Calculators</b>\n\n"
        "<b>Position Size</b>\n"
        "Estimate position size from balance, risk %, and stop distance.\n\n"
        "<b>Profit/Loss</b>\n"
        "Estimate gross P/L from entry, exit, and position size.\n\n"
        "Use /position or /pnl to start a calculator.",
        reply_markup=main_keyboard(),
    )


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
        "Example: <code>2500</code>",
        reply_markup=main_keyboard(),
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


@dp.message(F.text == "📚 Forex Academy")
async def academy_handler(message: Message):
    remember_user(message)
    await message.answer(
        "<b>📚 Forex Academy</b>\n\n"
        "<b>Risk Management</b>\n"
        "Learn how position size, stop distance, and account risk interact.\n\n"
        "<b>Spread</b>\n"
        "The difference between the bid and ask price.\n\n"
        "<b>Leverage</b>\n"
        "A mechanism that can increase market exposure relative to account equity and also increase risk.\n\n"
        "<b>Volatility</b>\n"
        "The degree to which price moves over time. Gold can move rapidly around major economic events.\n\n"
        "Educational content only — not financial advice.",
        reply_markup=main_keyboard(),
    )


async def main():
    await db_connect().close() if False else None
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
