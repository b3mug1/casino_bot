import asyncio
import logging
import os
import re

from aiogram import Bot, Dispatcher
from aiogram.filters import Command, CommandObject, CommandStart
from aiogram.types import Message
from dotenv import load_dotenv

from database import CasinoDatabase, InsufficientBalance

load_dotenv()

TOKEN = os.getenv("BOT_TOKEN", "").strip()
DATABASE_PATH = os.getenv("DATABASE_PATH", "casino.db")
STARTING_BALANCE = 1_000

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

dispatcher = Dispatcher()
database = CasinoDatabase(DATABASE_PATH, starting_balance=STARTING_BALANCE)

CHOICES = {
    "орел": "орел",
    "орёл": "орел",
    "решка": "решка",
    "heads": "орел",
    "tails": "решка",
}


def parse_bet(args: str | None) -> tuple[int, str] | None:
    if not args:
        return None

    parts = args.split()
    if len(parts) != 2:
        return None

    amount_text, choice_text = parts
    if not re.fullmatch(r"[0-9]{1,19}", amount_text):
        return None

    amount = int(amount_text)
    if amount > 9_223_372_036_854_775_807:
        return None

    choice = CHOICES.get(choice_text.casefold())
    if choice is None:
        return None
    return amount, choice


@dispatcher.message(CommandStart())
async def start(message: Message) -> None:
    if message.from_user is None:
        return
    try:
        balance = await asyncio.to_thread(database.get_balance, message.from_user.id)
    except Exception:
        logger.exception("Failed to load balance for user %s", message.from_user.id)
        await message.answer("Не удалось загрузить баланс. Попробуйте позже.")
        return

    await message.answer(
        "Добро пожаловать в казино-бот! Здесь используются только виртуальные фишки.\n"
        f"Ваш стартовый баланс: {balance} фишек.\n\n"
        "Посмотреть баланс: /balance\n"
        "Сыграть: /flip <ставка> <орел|решка>\n"
        "Например: /flip 100 орел"
    )


@dispatcher.message(Command("help"))
async def help_command(message: Message) -> None:
    await message.answer(
        "Игра на виртуальные фишки:\n"
        "/balance — посмотреть баланс\n"
        "/flip <ставка> <орел|решка> — сделать ставку\n\n"
        "Например: /flip 100 решка\n"
        "При победе вы получаете ставку сверху; при проигрыше ставка списывается."
    )


@dispatcher.message(Command("balance"))
async def balance_command(message: Message) -> None:
    if message.from_user is None:
        return
    try:
        balance = await asyncio.to_thread(database.get_balance, message.from_user.id)
    except Exception:
        logger.exception("Failed to load balance for user %s", message.from_user.id)
        await message.answer("Не удалось загрузить баланс. Попробуйте позже.")
        return

    await message.answer(f"Ваш баланс: {balance} фишек.")


@dispatcher.message(Command("flip"))
async def flip_command(message: Message, command: CommandObject) -> None:
    if message.from_user is None:
        return

    parsed = parse_bet(command.args)
    if parsed is None:
        await message.answer(
            "Укажите целую положительную ставку и сторону монеты.\n"
            "Пример: /flip 100 орел"
        )
        return

    amount, choice = parsed
    try:
        result = await asyncio.to_thread(
            database.play_round, message.from_user.id, amount, choice
        )
    except InsufficientBalance as error:
        await message.answer(
            f"Недостаточно фишек для такой ставки. Ваш баланс: {error.balance}."
        )
        return
    except ValueError as error:
        await message.answer(str(error))
        return
    except Exception:
        logger.exception("Failed to play a round for user %s", message.from_user.id)
        await message.answer("Не удалось завершить игру. Попробуйте позже.")
        return

    if result.won:
        outcome = f"Выпал {result.outcome} — вы выиграли {amount} фишек!"
    else:
        outcome = f"Выпала {result.outcome} — вы проиграли {amount} фишек."
    await message.answer(f"{outcome}\nВаш баланс: {result.balance} фишек.")


async def main() -> None:
    if not TOKEN:
        raise RuntimeError(
            "Не задан BOT_TOKEN. Создайте файл .env на основе .env.example "
            "и добавьте токен Telegram-бота."
        )

    await asyncio.to_thread(database.initialize)
    bot = Bot(token=TOKEN)
    try:
        await dispatcher.start_polling(bot)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped")
