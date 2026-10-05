import asyncio
import logging
import os
import sqlite3
import time

from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramForbiddenError
from aiogram.filters import Command, CommandStart
from aiogram.types import (
    CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup,
    KeyboardButton, Message, ReplyKeyboardMarkup, ReplyKeyboardRemove,
)

import texts as T

# ─────────────────────────────────────────
#  НАСТРОЙКИ (берутся из переменных окружения)
# ─────────────────────────────────────────
BOT_TOKEN     = os.environ["BOT_TOKEN"]
ADMIN_IDS     = {int(x) for x in os.getenv("ADMIN_IDS", "").replace(" ", "").split(",") if x}
COURSE_URL    = os.getenv("COURSE_URL", "https://t.me/Ozarenieebot")
VIDEO_FILE_ID = os.getenv("VIDEO_FILE_ID", "")
VIDEO_URL     = os.getenv("VIDEO_URL", "")
DB_PATH       = os.getenv("DB_PATH", "bot.db")

HOUR, DAY = 3600, 86400
# Через сколько секунд после остановки на этапе слать очередное напоминание.
PINGS = {
    "start":   ([HOUR, DAY], T.PING_START),
    "q1":      ([HOUR], T.PING_QUIZ),
    "q2":      ([HOUR], T.PING_QUIZ),
    "q3":      ([HOUR], T.PING_QUIZ),
    "video":   ([3 * HOUR, DAY, 2 * DAY], T.PING_VIDEO),
    "contact": ([HOUR], T.PING_CONTACT),
}
# ─────────────────────────────────────────

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

db = sqlite3.connect(DB_PATH)
db.row_factory = sqlite3.Row
db.executescript("""
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    name TEXT, username TEXT,
    stage TEXT DEFAULT 'start',
    niche TEXT, income TEXT, pain TEXT, contact TEXT, call_time TEXT,
    ping_step INTEGER DEFAULT 0,
    next_ping_at INTEGER,
    blocked INTEGER DEFAULT 0,
    created_at INTEGER
);
CREATE TABLE IF NOT EXISTS admin_msgs (
    admin_id INTEGER, message_id INTEGER, user_id INTEGER,
    PRIMARY KEY (admin_id, message_id)
);
""")


# ── База ─────────────────────────────────────────────────
def get_user(uid: int) -> sqlite3.Row | None:
    return db.execute("SELECT * FROM users WHERE id = ?", (uid,)).fetchone()


def touch_user(msg_from) -> sqlite3.Row:
    username = f"@{msg_from.username}" if msg_from.username else "нет"
    db.execute(
        "INSERT INTO users (id, name, username, created_at) VALUES (?, ?, ?, ?) "
        "ON CONFLICT(id) DO UPDATE SET name = excluded.name, username = excluded.username, blocked = 0",
        (msg_from.id, msg_from.full_name, username, int(time.time())),
    )
    db.commit()
    return get_user(msg_from.id)


def set_stage(uid: int, stage: str, **fields):
    """Переводит человека на этап и заново заводит напоминания для этого этапа."""
    delays = PINGS.get(stage, ([], []))[0]
    next_at = int(time.time()) + delays[0] if delays else None
    cols = ", ".join(f"{k} = ?" for k in fields)
    sql = "UPDATE users SET stage = ?, ping_step = 0, next_ping_at = ?" + (f", {cols}" if cols else "") + " WHERE id = ?"
    db.execute(sql, (stage, next_at, *fields.values(), uid))
    db.commit()


# ── Клавиатуры ───────────────────────────────────────────
def kb(*rows: list[InlineKeyboardButton]) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=list(rows))


def options_kb(prefix: str, options: dict[str, str]) -> InlineKeyboardMarkup:
    return kb(*[[InlineKeyboardButton(text=v, callback_data=f"{prefix}:{k}")] for k, v in options.items()])


def start_kb() -> InlineKeyboardMarkup:
    return kb(
        [InlineKeyboardButton(text=T.BTN_COURSE, url=COURSE_URL)],
        [InlineKeyboardButton(text=T.BTN_GOT_COURSE, callback_data="got_course")],
    )


def book_kb() -> InlineKeyboardMarkup:
    return kb([InlineKeyboardButton(text=T.BTN_BOOK, callback_data="book")])


def continue_kb() -> InlineKeyboardMarkup:
    return kb([InlineKeyboardButton(text=T.BTN_CONTINUE, callback_data="continue")])


def phone_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=T.BTN_SEND_PHONE, request_contact=True)]],
        resize_keyboard=True, one_time_keyboard=True,
    )


QUESTIONS = {
    "q1": (T.Q1, "q1", T.Q1_OPTIONS),
    "q2": (T.Q2, "q2", T.Q2_OPTIONS),
    "q3": (T.Q3, "q3", T.Q3_OPTIONS),
}


async def ask(uid: int, stage: str):
    text, prefix, options = QUESTIONS[stage]
    await bot.send_message(uid, text, reply_markup=options_kb(prefix, options))


async def send_video_block(uid: int, pain: str):
    await bot.send_message(uid, T.PAIN.get(pain, T.PAIN["clients"]))
    await asyncio.sleep(2)
    await bot.send_message(uid, T.BRIDGE)
    if VIDEO_FILE_ID:
        await bot.send_video(uid, VIDEO_FILE_ID, caption=T.VIDEO_CAPTION)
    elif VIDEO_URL:
        await bot.send_message(uid, T.VIDEO_CAPTION + "\n\n" + T.VIDEO_LINK.format(url=VIDEO_URL))
    else:
        await bot.send_message(uid, T.VIDEO_CAPTION)
    await asyncio.sleep(3)
    await bot.send_message(uid, T.OFFER, reply_markup=book_kb())


async def resume(uid: int):
    """Показывает человеку шаг, на котором он остановился."""
    user = get_user(uid)
    stage = user["stage"] if user else "start"
    if stage == "start":
        await bot.send_message(uid, T.START, reply_markup=start_kb())
    elif stage in QUESTIONS:
        await ask(uid, stage)
    elif stage == "video":
        await bot.send_message(uid, T.OFFER, reply_markup=book_kb())
    elif stage == "contact":
        await bot.send_message(uid, T.ASK_CONTACT, reply_markup=phone_kb())
    elif stage == "time":
        await bot.send_message(uid, T.ASK_TIME, reply_markup=options_kb("time", T.TIME_OPTIONS))
    else:
        await bot.send_message(uid, T.ALREADY_BOOKED)


# ── Воронка ──────────────────────────────────────────────
@dp.message(CommandStart())
async def cmd_start(message: Message):
    user = touch_user(message.from_user)
    if user["stage"] == "booked":
        await message.answer(T.ALREADY_BOOKED)
        return
    if user["stage"] in ("start", "q1", "q2", "q3"):
        set_stage(user["id"], "start")
        await message.answer(T.START, reply_markup=start_kb())
    else:
        await resume(user["id"])


@dp.callback_query(F.data == "got_course")
async def on_got_course(cb: CallbackQuery):
    touch_user(cb.from_user)
    await cb.answer()
    await cb.message.edit_reply_markup(reply_markup=None)
    set_stage(cb.from_user.id, "q1")
    await cb.message.answer(T.QUIZ_INTRO)
    await ask(cb.from_user.id, "q1")


@dp.callback_query(F.data == "continue")
async def on_continue(cb: CallbackQuery):
    touch_user(cb.from_user)
    await cb.answer()
    await resume(cb.from_user.id)


@dp.callback_query(F.data.startswith("q"))
async def on_answer(cb: CallbackQuery):
    q, key = cb.data.split(":", 1)
    _, _, options = QUESTIONS[q]
    await cb.answer()
    user = get_user(cb.from_user.id)
    if not user or user["stage"] != q:
        return  # нажали старую кнопку
    await cb.message.edit_text(f"{cb.message.html_text}\n\n✅ {options[key]}", reply_markup=None)
    uid = cb.from_user.id
    touch_user(cb.from_user)
    if q == "q1":
        set_stage(uid, "q2", niche=options[key])
        await ask(uid, "q2")
    elif q == "q2":
        set_stage(uid, "q3", income=options[key])
        await ask(uid, "q3")
    else:
        set_stage(uid, "video", pain=options[key])
        await send_video_block(uid, key)


@dp.callback_query(F.data == "book")
async def on_book(cb: CallbackQuery):
    user = touch_user(cb.from_user)
    await cb.answer()
    if user["stage"] == "booked":
        await cb.message.answer(T.ALREADY_BOOKED)
        return
    set_stage(cb.from_user.id, "contact")
    await cb.message.answer(T.ASK_CONTACT, reply_markup=phone_kb())


async def save_contact(message: Message, contact: str):
    set_stage(message.from_user.id, "time", contact=contact)
    await message.answer(T.CONTACT_SAVED, reply_markup=ReplyKeyboardRemove())
    await message.answer(T.ASK_TIME, reply_markup=options_kb("time", T.TIME_OPTIONS))


@dp.message(F.contact)
async def on_contact(message: Message):
    user = touch_user(message.from_user)
    if user["stage"] == "contact":
        await save_contact(message, message.contact.phone_number)


@dp.callback_query(F.data.startswith("time:"))
async def on_time(cb: CallbackQuery):
    key = cb.data.split(":", 1)[1]
    await cb.answer()
    await cb.message.edit_text(f"{cb.message.html_text}\n\n✅ {T.TIME_OPTIONS[key]}", reply_markup=None)
    set_stage(cb.from_user.id, "booked", call_time=T.TIME_OPTIONS[key])
    await cb.message.answer(T.BOOKED)
    user = get_user(cb.from_user.id)
    await notify_admins(T.ADMIN_LEAD.format(
        name=user["name"], username=user["username"], contact=user["contact"],
        niche=user["niche"], income=user["income"], pain=user["pain"], time=user["call_time"],
    ), user["id"])


# ── Связь с админом ──────────────────────────────────────
async def notify_admins(text: str, user_id: int):
    for admin_id in ADMIN_IDS:
        try:
            sent = await bot.send_message(admin_id, text)
            db.execute("INSERT OR REPLACE INTO admin_msgs VALUES (?, ?, ?)", (admin_id, sent.message_id, user_id))
            db.commit()
        except Exception as e:
            logging.warning("Не смог написать админу %s: %s", admin_id, e)


@dp.message(Command("stats"), F.from_user.id.in_(ADMIN_IDS))
async def cmd_stats(message: Message):
    rows = db.execute("SELECT stage, COUNT(*) c FROM users GROUP BY stage").fetchall()
    counts = {r["stage"]: r["c"] for r in rows}
    total = sum(counts.values())
    blocked = db.execute("SELECT COUNT(*) FROM users WHERE blocked = 1").fetchone()[0]
    order = [("start", "На старте"), ("q1", "Вопрос 1"), ("q2", "Вопрос 2"), ("q3", "Вопрос 3"),
             ("video", "Видео, без записи"), ("contact", "Не оставили контакт"),
             ("time", "Не выбрали время"), ("booked", "Записались")]
    lines = [f"{label}: {counts.get(stage, 0)}" for stage, label in order]
    await message.answer(f"<b>Всего:</b> {total}\n<b>Заблокировали бота:</b> {blocked}\n\n" + "\n".join(lines))


@dp.message(Command("leads"), F.from_user.id.in_(ADMIN_IDS))
async def cmd_leads(message: Message):
    rows = db.execute("SELECT * FROM users WHERE stage = 'booked' ORDER BY rowid DESC LIMIT 15").fetchall()
    if not rows:
        await message.answer("Заявок пока нет.")
        return
    await message.answer("\n\n".join(
        f"{r['name']} {r['username']}\n📱 {r['contact']} · {r['call_time']}\n{r['niche']} · {r['income']} · {r['pain']}"
        for r in rows
    ))


@dp.message(Command("broadcast"), F.from_user.id.in_(ADMIN_IDS))
async def cmd_broadcast(message: Message):
    text = message.html_text.partition(" ")[2].strip()
    if not text:
        await message.answer("Напиши так: /broadcast текст рассылки")
        return
    ids = [r[0] for r in db.execute("SELECT id FROM users WHERE blocked = 0")]
    ok = 0
    for uid in ids:
        try:
            await bot.send_message(uid, text)
            ok += 1
        except TelegramForbiddenError:
            db.execute("UPDATE users SET blocked = 1 WHERE id = ?", (uid,))
        except Exception as e:
            logging.warning("Рассылка %s: %s", uid, e)
        await asyncio.sleep(0.05)
    db.commit()
    await message.answer(f"Отправлено: {ok} из {len(ids)}")


@dp.message(F.video, F.from_user.id.in_(ADMIN_IDS))
async def admin_video(message: Message):
    await message.answer(f"file_id этого видео:\n<code>{message.video.file_id}</code>\n\nВставь его в VIDEO_FILE_ID.")


@dp.message(F.reply_to_message, F.from_user.id.in_(ADMIN_IDS))
async def admin_reply(message: Message):
    row = db.execute(
        "SELECT user_id FROM admin_msgs WHERE admin_id = ? AND message_id = ?",
        (message.chat.id, message.reply_to_message.message_id),
    ).fetchone()
    if not row:
        await message.answer("Не нашёл, кому отвечать. Отвечай reply на заявку или сообщение от человека.")
        return
    try:
        await message.copy_to(row["user_id"])
        await message.answer("✅ Отправлено")
    except TelegramForbiddenError:
        await message.answer("❌ Человек заблокировал бота")


@dp.message(F.text)
async def on_text(message: Message):
    user = touch_user(message.from_user)
    if user["stage"] == "contact":
        await save_contact(message, message.text.strip())
        return
    if message.from_user.id in ADMIN_IDS:
        return
    await notify_admins(T.ADMIN_USER_MSG.format(
        name=user["name"], username=user["username"], text=message.html_text,
    ), user["id"])
    await message.answer(T.MESSAGE_RECEIVED)
    if user["stage"] != "booked":
        await resume(user["id"])


# ── Напоминания ──────────────────────────────────────────
async def pinger():
    while True:
        try:
            now = int(time.time())
            due = db.execute(
                "SELECT * FROM users WHERE blocked = 0 AND next_ping_at IS NOT NULL AND next_ping_at <= ?", (now,)
            ).fetchall()
            for u in due:
                delays, msgs = PINGS.get(u["stage"], ([], []))
                step = u["ping_step"]
                if step >= len(msgs):
                    db.execute("UPDATE users SET next_ping_at = NULL WHERE id = ?", (u["id"],))
                    continue
                markup = {"start": start_kb(), "video": book_kb()}.get(u["stage"], continue_kb())
                try:
                    await bot.send_message(u["id"], msgs[step], reply_markup=markup)
                except TelegramForbiddenError:
                    db.execute("UPDATE users SET blocked = 1, next_ping_at = NULL WHERE id = ?", (u["id"],))
                    continue
                except Exception as e:
                    logging.warning("Напоминание %s: %s", u["id"], e)
                step += 1
                next_at = now + delays[step] if step < len(delays) else None
                db.execute("UPDATE users SET ping_step = ?, next_ping_at = ? WHERE id = ?", (step, next_at, u["id"]))
                await asyncio.sleep(0.05)
            db.commit()
        except Exception:
            logging.exception("Ошибка в напоминаниях")
        await asyncio.sleep(30)


async def main():
    if not ADMIN_IDS:
        logging.warning("ADMIN_IDS не задан: заявки никуда не придут!")
    asyncio.create_task(pinger())
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
