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
DB_PATH = os.getenv("DB_PATH", "sb24.db")
ADMIN_IDS = {
    int(value.strip())
    for value in os.getenv("ADMIN_IDS", "").split(",")
    if value.strip().isdigit()
}

if not TOKEN:
    raise RuntimeError("BOT_TOKEN environment variable is required")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("sb24")

bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()


WELCOME_TEXT = (
    "<b>SB24 Text Tools</b>\n\n"
    "Quick, simple tools for working with text.\n\n"
    "Choose a tool below to get started. You can also try the examples."
)


HELP_TEXT = (
    "<b>SB24 Help</b>\n\n"
    "<b>Sort Words</b> — arrange words alphabetically.\n"
    "Example: <code>banana apple orange</code>\n\n"
    "<b>Count Text</b> — count characters, words and lines.\n"
    "Example: <code>Hello world</code>\n\n"
    "<b>Rearrange Letters</b> — reverse or alphabetically arrange letters.\n"
    "Example: <code>telegram</code>\n\n"
    "Commands:\n"
    "/start — open the main menu\n"
    "/menu — return to the main menu\n"
    "/help — show instructions\n"
    "/example — try sample inputs"
)


class ToolStates(StatesGroup):
    sort_words = State()
    count_text = State()
    rearrange_letters = State()


def connect_db():
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
    user = message.from_user
    if not user:
        return

    now = datetime.now(timezone.utc).isoformat()
    connection = connect_db()
    try:
        connection.execute(
            """
            INSERT INTO users (user_id, username, first_name, joined_at, last_seen)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                username = excluded.username,
                first_name = excluded.first_name,
                last_seen = excluded.last_seen
            """,
            (user.id, user.username, user.first_name, now, now),
        )
        connection.commit()
    finally:
        connection.close()


def main_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🔤 Sort Words"), KeyboardButton(text="🔢 Count Text")],
            [KeyboardButton(text="🔀 Rearrange Letters"), KeyboardButton(text="🧪 Example")],
            [KeyboardButton(text="❓ Help"), KeyboardButton(text="🏠 Menu")],
        ],
        resize_keyboard=True,
        is_persistent=True,
        input_field_placeholder="Choose a text tool",
    )


def normalize_spaces(text: str) -> str:
    return " ".join(text.split())


def sort_words(text: str) -> str:
    words = normalize_spaces(text).split(" ") if normalize_spaces(text) else []
    return " ".join(sorted(words, key=str.casefold))


def count_text(text: str) -> tuple[int, int, int]:
    characters = len(text)
    words = len(text.split())
    lines = len(text.splitlines()) if text else 0
    return characters, words, lines


def rearrange_letters(text: str) -> str:
    compact = "".join(text.split())
    return "".join(sorted(compact, key=str.casefold))


async def show_home(message: Message, state: FSMContext | None = None) -> None:
    if state:
        await state.clear()
    remember_user(message)
    await message.answer(WELCOME_TEXT, reply_markup=main_keyboard())


@dp.message(CommandStart())
async def start_handler(message: Message, state: FSMContext):
    await show_home(message, state)


@dp.message(Command("menu"))
async def menu_handler(message: Message, state: FSMContext):
    await show_home(message, state)


@dp.message(Command("help"))
async def help_handler(message: Message, state: FSMContext):
    await state.clear()
    remember_user(message)
    await message.answer(HELP_TEXT, reply_markup=main_keyboard())


@dp.message(Command("example"))
async def example_handler(message: Message, state: FSMContext):
    await state.clear()
    remember_user(message)
    await message.answer(
        "<b>🧪 SB24 Examples</b>\n\n"
        "<b>Sort Words</b>\nInput: <code>banana apple orange</code>\nResult: <code>apple banana orange</code>\n\n"
        "<b>Count Text</b>\nInput: <code>Hello world</code>\nResult: <code>11 characters, 2 words, 1 line</code>\n\n"
        "<b>Rearrange Letters</b>\nInput: <code>telegram</code>\nResult: <code>aee gl mrt</code>"
        .replace("aee gl mrt", "aaeeglmrt"),
        reply_markup=main_keyboard(),
    )


@dp.message(F.text == "❓ Help")
async def help_button_handler(message: Message, state: FSMContext):
    await help_handler(message, state)


@dp.message(F.text == "🏠 Menu")
async def menu_button_handler(message: Message, state: FSMContext):
    await show_home(message, state)


@dp.message(F.text == "🧪 Example")
async def example_button_handler(message: Message, state: FSMContext):
    await example_handler(message, state)


async def begin_tool(message: Message, state: FSMContext, target_state: State, title: str, example: str) -> None:
    await state.clear()
    remember_user(message)
    await state.set_state(target_state)
    await message.answer(
        f"<b>{title}</b>\n\n"
        f"Send the text you want to process.\n\n"
        f"Example: <code>{example}</code>\n\n"
        "Use /menu at any time to cancel.",
        reply_markup=main_keyboard(),
    )


@dp.message(F.text == "🔤 Sort Words")
async def sort_start(message: Message, state: FSMContext):
    await begin_tool(message, state, ToolStates.sort_words, "🔤 Sort Words", "banana apple orange")


@dp.message(ToolStates.sort_words)
async def sort_process(message: Message, state: FSMContext):
    text = (message.text or "").strip()
    if not text:
        await message.answer("Please send some words to sort.")
        return
    result = sort_words(text)
    await state.clear()
    await message.answer(
        "<b>✅ Sorted Words</b>\n\n"
        f"Input: <code>{text}</code>\n"
        f"Result: <code>{result}</code>",
        reply_markup=main_keyboard(),
    )


@dp.message(F.text == "🔢 Count Text")
async def count_start(message: Message, state: FSMContext):
    await begin_tool(message, state, ToolStates.count_text, "🔢 Count Text", "Hello world")


@dp.message(ToolStates.count_text)
async def count_process(message: Message, state: FSMContext):
    text = message.text or ""
    if not text.strip():
        await message.answer("Please send some text to count.")
        return
    characters, words, lines = count_text(text)
    await state.clear()
    await message.answer(
        "<b>✅ Text Count</b>\n\n"
        f"Characters: <code>{characters}</code>\n"
        f"Words: <code>{words}</code>\n"
        f"Lines: <code>{lines}</code>",
        reply_markup=main_keyboard(),
    )


@dp.message(F.text == "🔀 Rearrange Letters")
async def rearrange_start(message: Message, state: FSMContext):
    await begin_tool(message, state, ToolStates.rearrange_letters, "🔀 Rearrange Letters", "telegram")


@dp.message(ToolStates.rearrange_letters)
async def rearrange_process(message: Message, state: FSMContext):
    text = (message.text or "").strip()
    if not text:
        await message.answer("Please send letters or a word to rearrange.")
        return
    result = rearrange_letters(text)
    await state.clear()
    await message.answer(
        "<b>✅ Rearranged Letters</b>\n\n"
        f"Input: <code>{text}</code>\n"
        f"Result: <code>{result}</code>",
        reply_markup=main_keyboard(),
    )


@dp.message(Command("stats"))
async def stats_handler(message: Message):
    remember_user(message)
    if message.from_user is None or message.from_user.id not in ADMIN_IDS:
        await message.answer("This command is available to administrators only.", reply_markup=main_keyboard())
        return

    connection = connect_db()
    try:
        total = connection.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    finally:
        connection.close()

    await message.answer(
        f"<b>📊 SB24 Stats</b>\n\nRegistered users: <code>{total}</code>",
        reply_markup=main_keyboard(),
    )


@dp.message()
async def fallback_handler(message: Message, state: FSMContext):
    remember_user(message)
    current_state = await state.get_state()
    if current_state:
        await message.answer(
            "Please use the format requested above, or tap /menu to return to the main menu.",
            reply_markup=main_keyboard(),
        )
        return

    await message.answer(
        "I didn't recognize that option. Please choose a tool from the menu.",
        reply_markup=main_keyboard(),
    )


async def main():
    connection = connect_db()
    connection.close()
    logger.info("SB24 bot starting")
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("SB24 bot stopped")
