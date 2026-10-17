#!/usr/bin/env python3
"""Неделя 19–25 окт: 21 Short в «неделя_19-25» + описания.txt. Вид как v1 из make_5.py:

  * фон — ролик из «фоны» на весь экран (горизонтальные обрезаются по бокам), затемнение 55 %;
    по кругу: ночная дорога (POV), ночной город, купюры, тёмный ролик, стол с купюрами;
  * текст Helvetica Neue Medium 50, белый, мягкая тень, по центру, виден с первого кадра;
    «||» — новый абзац (пустая строка), «|» — новая строка, цифры не отрываются от слова;
  * ник @markovvv2 весь ролик сверху (y≈300), 40;
  * последние 2,5 с, тем же шрифтом, без плашки: «Пиши ХОЧУ» 80, «→ @markovvv2» 66,
    «расскажу, как забрать деньги от б@нков» 44 в 2 строки;
  * энергичная музыка из «музыка», громкость выровнена, затухание в конце;
  * 1080×1920, 30 fps, H.264 + AAC, 6–8 с (короче — больше досматривают до «ХОЧУ»).

  python3 make_week.py            # все 21
  python3 make_week.py --only 3,7 # только эти
"""
import argparse
import json
import random
import re
import subprocess
import tempfile
from pathlib import Path

from PIL import ImageFont

ROOT = Path(__file__).resolve().parent
BG_DIR = ROOT / "фоны"
MUS_DIR = ROOT / "музыка"
OUT_DIR = ROOT / "неделя_19-25"

W, H, FPS = 1080, 1920, 30
DIM = 0.55
SAFE_X = 150                      # поля по бокам, как в make_5.py
MAX_TEXT_W = W - 2 * SAFE_X
FONT_SIZE, NICK_SIZE = 50, 40
OUTLINE, GLOW_BLUR = 2, 4         # мягкая полупрозрачная тень вокруг букв (make_videos.py)
NICK = "@markovvv2"
NICK_Y = 300
PLATE_SEC = 2.5
NBSP = " "

# (файл, индекс в .ttc, имя для libass). На Mac — Helvetica Neue Medium, на Linux — её клон FreeSans.
FONT_CANDIDATES = [
    ("/System/Library/Fonts/HelveticaNeue.ttc", 10, "Helvetica Neue Medium"),
    ("/usr/share/fonts/truetype/freefont/FreeSans.ttf", 0, "FreeSans"),
]
FONT_PATH, FONT_INDEX, FONT_NAME = next(c for c in FONT_CANDIDATES if Path(c[0]).exists())

TEXTS = [
    "Смена в Пятёрочке: 2 500 ₽||Бизнес-карты в 8 местах: как неделя таких смен||Без вложений",
    "Как заработать на РКО с нуля:||1) пишешь мне|2) ИП онлайн за 1-3 дня|3) бизнес-карты за вечер"
    "|4) ждёшь месяц-полтора|5) забираешь",
    "Тебе 18+, пашешь больше всех, а денег меньше всех?||Пока ты на смене, другие забирают деньги за РКО",
    "Курьер: 12 часов на ногах за 3 000 ₽||Бизнес-карты с телефона: в разы больше",
    "«РКО это развод»||Факты: всё оформлено на тебя, доступ только у тебя, ты ничего не платишь",
    "Ищешь нишу третий год?||Самый простой вход: РКО",
    "Официант за эти деньги работает 2 недели||Тут пара вечеров с телефона",
    "Что нужно для РКО:||18+, паспорт РФ, без долгов, не госслужащий||Всё",
    "Открыл сам и получил деньги||Позвал друзей: за каждого ещё бонус",
    "Кассир: месяц за кассой||РКО: пара вечеров с телефона",
    "Почему деньги не сразу?||Выплата через месяц-полтора||Говорю как есть",
    "Стипендия 3 000 ₽?||Вот как поднять больше за пару вечеров",
    "Завод: 5/2 с 8 до 17||РКО: пара вечеров с телефона",
    "ИП звучит страшно?||Онлайн, бесплатно, 1-3 дня||Подскажу каждый шаг",
    "Почему платят за РКО:||б@нкам нужны клиенты с ИП||За каждого они платят||Часть твоя",
    "Просят твои пароли и коды?||Беги||Я не прошу. Доступ только у тебя",
    "Рефералка: 2к за друга||РКО на себя в 8 местах: в разы больше",
    "Друг сидит без денег?||Скинь ему это||За каждого друга бонус тебе",
    "Нужно вкладываться?||Нет||Ни рубля",
    "3 ошибки новичка в РКО:||1) передать кому-то доступ|2) ждать денег в тот же день|3) идти с долгами",
    "Откуда деньги за РКО?||Это рекламный бюджет б@нков||Они платят за нового клиента",
]
# Концовка: (текст, кегль, y). На экране нет слова «банк» — пишем «б@нков».
ENDING = [
    ("Пиши ХОЧУ", 80, 834),
    ("→ " + NICK, 66, 945),
    ("расскажу, как забрать", 44, 1041),
    ("деньги от б@нков", 44, 1088),
]

TITLES = [
    "Смена в Пятёрочке 2 500 ₽ против пары вечеров с телефона",
    "Как заработать на РКО с нуля: 5 шагов",
    "Тебе 18+ и денег вечно нет?",
    "Курьер 12 часов за 3 000 ₽. Есть вариант проще",
    "РКО это развод? Три факта",
    "Ищешь нишу третий год? Начни с этого",
    "Официант 2 недели или пара вечеров с телефона",
    "Что нужно для РКО: 4 условия",
    "Позвал друзей и получил бонус за каждого",
    "Кассир месяц за кассой. Есть вариант проще",
    "Почему выплата через месяц-полтора",
    "Стипендия 3 000 ₽? Вот как поднять больше",
    "Завод 5/2 или пара вечеров с телефона",
    "ИП за 1-3 дня онлайн и бесплатно",
    "Почему за РКО платят деньги",
    "Просят пароли и коды? Беги",
    "Рефералка 2к за друга против РКО",
    "Скинь это другу без денег",
    "Нужно вкладываться в РКО? Ни рубля",
    "3 ошибки новичка в РКО",
    "Откуда берутся деньги за РКО",
]
DESC = ("Пиши «ХОЧУ» в ТГ: @markovvv2. Канал с гайдом: markovrko. Доступ только у тебя, вложений ноль. "
        "#рко #заработок #подработка #студент #деньги")
BANNED = re.compile(r"банк|сч[её]т", re.I)

# Фоны по кругу. Тёмный IMG_13338 короче 12 с — он чуть замедляется, а не зацикливается.
THEMES = {
    "ночная_дорога": [BG_DIR / "6044999852_1_tiktok_6a9934d5e66243_74400506.mp4"],
    "ночной_город": [BG_DIR / "792996255_1_tiktok_691210ba3adc99_19024936.mp4",
                     BG_DIR / "885564788_1_tiktok_69154547596943_43315476.mp4"],
    "купюры": [BG_DIR / "IMG_18259.mp4"],
    "тёмный": [BG_DIR / "IMG_13338.mp4"],
    "стол_с_купюрами": [BG_DIR / "1397611078_1_tiktok_6a0dcc135712c0_09814984.mp4"],
}
BG_CYCLE = ["ночная_дорога", "ночной_город", "купюры", "тёмный", "стол_с_купюрами"]
ENERGY = [
    "6866214859_1_tiktok_6a1cab7983bdf6_98223199.mp3",
    "905647610_1_tiktok_69cb0b12b6ff99_48043899.mp3",
    "969250147_1_tiktok_6a7f5f04db8cb4_31788749.mp3",
    "7090366305_1_tiktok_689f5432d9a084_43998919.mp3",
    "7755494120_1_tiktok_6a4b61588f7ae2_71076373.mp3",
    "𝑀𝑜𝑛𝑒𝑦𝑊𝑖𝑛𝑠 - Money Wins.mp3",
]


# ---------- утилиты (как в make_videos.py) ----------

def probe_duration(path):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "json", str(path)],
        capture_output=True, text=True, check=True,
    ).stdout
    return float(json.loads(out)["format"]["duration"])


def glue(text):
    """«3 000 ₽», «8 местах», «1) пишешь» не рвутся по строкам."""
    text = re.sub(r"(?<=\d) (?=\d{3}\b)", NBSP, text)
    text = re.sub(r" (?=₽)", NBSP, text)
    text = re.sub(r"(?<=\d) (?=\S)", NBSP, text)
    return re.sub(r"(?<=\d\)) ", NBSP, text)


def greedy(text, font, max_w):
    lines, cur = [], ""
    for word in glue(text).split(" "):
        trial = f"{cur} {word}".strip()
        if font.getlength(trial) <= max_w or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def wrap(text, font):
    """Ровные строки: самая узкая ширина без лишних строк."""
    n = len(greedy(text, font, MAX_TEXT_W))
    lo, hi = 1, MAX_TEXT_W
    while lo < hi:
        mid = (lo + hi) // 2
        if len(greedy(text, font, mid)) <= n:
            hi = mid
        else:
            lo = mid + 1
    return greedy(text, font, lo)


def layout(text):
    font = ImageFont.truetype(FONT_PATH, FONT_SIZE, index=FONT_INDEX)
    lines = []
    for para in text.split("||"):
        if lines:
            lines.append(NBSP)               # пустая строка между абзацами
        for sub in para.split("|"):
            lines += wrap(sub.strip(), font)
    assert all(font.getlength(l) <= MAX_TEXT_W for l in lines), lines
    return lines


def ass_escape(s):
    return s.replace("\\", "\\\\").replace("{", "\\{").replace("}", "\\}")


def ass_time(t):
    cs = int(round(t * 100))
    return f"{cs // 360000}:{cs // 6000 % 60:02d}:{cs // 100 % 60:02d}.{cs % 100:02d}"


def build_ass(text, tsec, dur):
    head = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: T,{FONT_NAME},{FONT_SIZE},&H00FFFFFF,&H00FFFFFF,&H70000000,&H00000000,0,0,0,0,100,100,0,0,1,{OUTLINE},0,5,0,0,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    glow = f"\\blur{GLOW_BLUR}"
    body = "\\N".join(ass_escape(l) for l in layout(text))
    rows = [
        f"Dialogue: 0,{ass_time(0)},{ass_time(dur)},T,,0,0,0,,"
        f"{{\\an5\\pos({W // 2},{NICK_Y})\\fs{NICK_SIZE}{glow}}}{NICK}",
        # текст с первого кадра — крючок сразу
        f"Dialogue: 0,{ass_time(0)},{ass_time(tsec)},T,,0,0,0,,"
        f"{{\\an5\\pos({W // 2},{H // 2})\\fs{FONT_SIZE}{glow}}}{body}",
    ]
    for line, size, y in ENDING:
        rows.append(f"Dialogue: 0,{ass_time(tsec)},{ass_time(dur)},T,,0,0,0,,"
                    f"{{\\an5\\pos({W // 2},{y})\\fs{size}{glow}}}{ass_escape(line)}")
    return head + "\n".join(rows) + "\n"


def text_sec(text):
    words = len(text.replace("||", " ").replace("|", " ").split())
    # коротко, чтобы до «ХОЧУ» досматривали; ~4 слова в секунду + время «зацепиться»
    return round(min(5.5, max(3.5, 1.5 + words * 0.25)), 1)


# ---------- рендер ----------

def render(i, rng, tmp):
    text = TEXTS[i - 1]
    assert not BANNED.search(text), text
    tsec = text_sec(text)
    dur = round(tsec + PLATE_SEC, 1)

    theme = BG_CYCLE[(i - 1) % len(BG_CYCLE)]
    pool = THEMES[theme]
    bg = pool[((i - 1) // len(BG_CYCLE)) % len(pool)]
    music = MUS_DIR / ENERGY[(i - 1) % len(ENERGY)]

    ass = tmp / f"{i}.ass"
    ass.write_text(build_ass(text, tsec, dur), encoding="utf-8")
    ass_arg = str(ass).replace("\\", "/").replace(":", "\\:").replace("'", "\\'")

    bd = probe_duration(bg)
    slow = max(1.0, (dur + 0.2) / bd)
    bg_in = ["-ss", f"{rng.uniform(0, bd - dur - 0.2):.2f}" if slow == 1.0 else "0", "-i", str(bg)]
    md = probe_duration(music)
    mus_in = ["-ss", f"{rng.uniform(0, max(0, md - dur - 1)):.2f}"] if md > dur + 1 else ["-stream_loop", "-1"]

    vf = (f"setpts={slow:.3f}*PTS,"
          f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},setsar=1,fps={FPS},"
          f"drawbox=c=black@{DIM}:t=fill,"
          f"ass='{ass_arg}'")
    out = OUT_DIR / f"{i:02d}.mp4"
    subprocess.run(["ffmpeg", "-v", "error", "-y", *bg_in, *mus_in, "-i", str(music),
                    "-map", "0:v:0", "-map", "1:a:0", "-vf", vf,
                    "-af", f"loudnorm=I=-14,afade=t=out:st={dur - 0.6}:d=0.6", "-t", str(dur),
                    "-r", str(FPS), "-c:v", "libx264", "-preset", "medium", "-crf", "19", "-pix_fmt", "yuv420p",
                    "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(out)], check=True)
    print(f"{out.name}: {dur:.1f} с, фон {theme} ({bg.name}), музыка {music.name}", flush=True)


def write_descriptions():
    rows = []
    for i, title in enumerate(TITLES, 1):
        rows += [f"{i:02d} | {title}", DESC, ""]
    text = "\n".join(rows)
    assert not BANNED.search(text)
    (OUT_DIR / "описания.txt").write_text(text, encoding="utf-8")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="all", help="all | 1,5,7")
    ap.add_argument("--seed", type=int, default=19)
    args = ap.parse_args()
    assert len(TEXTS) == len(TITLES) == 21
    rng = random.Random(args.seed)
    OUT_DIR.mkdir(exist_ok=True)
    nums = range(1, 22) if args.only == "all" else [int(x) for x in args.only.split(",")]
    with tempfile.TemporaryDirectory() as t:
        for i in nums:
            render(i, rng, Path(t))
    write_descriptions()
    print("Готово:", OUT_DIR)


if __name__ == "__main__":
    main()
