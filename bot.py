import asyncio
import logging
from aiogram import Bot, Dispatcher, F
from aiogram.types import (
    Message, CallbackQuery,
    InlineKeyboardMarkup, InlineKeyboardButton,
    ChatMemberStatus
)
from aiogram.filters import CommandStart
from aiogram.enums import ParseMode

# ─────────────────────────────────────────
#  НАСТРОЙКИ — замени на свои
# ─────────────────────────────────────────
BOT_TOKEN    = "8661674036:AAG8mDPeUoMM5T_mph-jK7bSDc-KvvXONwU"
CHANNEL_ID   = "@localframe"
VIDEO_FILE_ID = "AAMCAgADGQEDBLK1aeEn9AABENzBHV-CptErqGzKsd9cAAKxlQACtvZZSa4VEAw0AWqNAQAHbQADOwQv"

# Текст кнопок и сообщений
CHANNEL_TITLE  = "Мой канал"
WELCOME_TEXT   = (
    "👋 Привет! Я выдаю <b>бесплатный материал</b>.\n\n"
    "Для получения нужно подписаться на канал 👇"
)
NOT_SUBSCRIBED = (
    "❌ Ты ещё не подписан.\n\n"
    "Подпишись на канал и нажми <b>«Проверить подписку»</b> снова."
)
ALREADY_SENT   = "✅ Ты уже получил материал. Спасибо что остаёшься с нами!"
VIDEO_CAPTION  = "🎁 Держи! Вот твой материал. Добро пожаловать в канал 🔥"
# ─────────────────────────────────────────

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN, parse_mode=ParseMode.HTML)
dp  = Dispatcher()

# Простое хранилище выданных лидмагнитов (в памяти)
# Для продакшена замени на базу данных (SQLite / PostgreSQL)
sent_to: set[int] = set()


def subscribe_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"📢 Подписаться на {CHANNEL_TITLE}",
                              url=f"https://t.me/{CHANNEL_ID.lstrip('@')}")],
        [InlineKeyboardButton(text="✅ Проверить подписку",
                              callback_data="check_sub")],
    ])


async def is_subscribed(user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(CHANNEL_ID, user_id)
        return member.status in (
            ChatMemberStatus.MEMBER,
            ChatMemberStatus.ADMINISTRATOR,
            ChatMemberStatus.CREATOR,
        )
    except Exception:
        return False


@dp.message(CommandStart())
async def cmd_start(message: Message):
    if await is_subscribed(message.from_user.id):
        await send_leadmagnet(message.from_user.id, message)
    else:
        await message.answer(WELCOME_TEXT, reply_markup=subscribe_keyboard())


@dp.callback_query(F.data == "check_sub")
async def check_subscription(callback: CallbackQuery):
    user_id = callback.from_user.id

    if await is_subscribed(user_id):
        await callback.message.delete()
        await send_leadmagnet(user_id, callback.message)
    else:
        await callback.answer(
            "Ты ещё не подписан! Подпишись и попробуй снова.",
            show_alert=True
        )


async def send_leadmagnet(user_id: int, source: Message):
    if user_id in sent_to:
        await source.answer(ALREADY_SENT)
        return

    await bot.send_video(
        chat_id=user_id,
        video=VIDEO_FILE_ID,
        caption=VIDEO_CAPTION,
    )
    sent_to.add(user_id)


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
