#!/usr/bin/env python3
"""Неделя 19–25 окт: 21 TikTok-ролик + описания.txt в «неделя_19-25».

Основа — make_videos.py / make_5.py (фон из «фоны», музыка из «музыка», затемнение,
ffmpeg), оформление как у v3 из «5_единичек», но:
  * текст ≥ 90 px, белый с чёрной обводкой, ≤ 2 строк на экране;
  * ник @markovvv2 ~60 px вверху по центру весь ролик;
  * последние 3 с — белая плашка «Пиши ХОЧУ → @markovvv2», чёрный текст;
  * весь текст выше 80 % высоты и левее 85 % ширины (кнопки TikTok).

  python3 make_week.py            # все 21
  python3 make_week.py --only 3,7 # только эти
"""
import argparse
import json
import math
import random
import re
import subprocess
import tempfile
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parent
BG_DIR = ROOT / "фоны"
MUS_DIR = ROOT / "музыка"
GEN_DIR = BG_DIR / "_сгенерированные"
OUT_DIR = ROOT / "неделя_19-25"

W, H = 1080, 1920
FPS = 30
# Безопасная зона: ничего правее 85 % ширины и ниже 80 % высоты.
SAFE_RIGHT = int(W * 0.85)          # 918
SAFE_BOTTOM = int(H * 0.80)         # 1536
SAFE_LEFT = 50                      # слева кнопок нет — поле уже
TEXT_CX = (SAFE_LEFT + SAFE_RIGHT) // 2
MAX_TEXT_W = SAFE_RIGHT - SAFE_LEFT
TEXT_CY = 900                       # центр блока текста

FONT_SIZE, FONT_MIN = 96, 90
OUTLINE = 7
LINE_SPACING = 1.12
NICK = "@markovvv2"
NICK_SIZE, NICK_Y = 60, 300
PLATE_SEC = 3.0
DIM = 0.5

FONT_CANDIDATES = [
    ("/usr/share/fonts/opentype/inter/InterDisplay-ExtraBold.otf", 0),
    ("/System/Library/Fonts/HelveticaNeue.ttc", 1),               # macOS, Bold
    ("/System/Library/Fonts/Supplemental/Arial Bold.ttf", 0),
    ("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf", 0),
]
FONT_PATH, FONT_INDEX = next((p, i) for p, i in FONT_CANDIDATES if Path(p).exists())
NBSP = " "


def font(size):
    return ImageFont.truetype(FONT_PATH, size, index=FONT_INDEX)


# ---------- контент ----------

# « / » — новый экран. На экране не больше 2 строк.
TEXTS = [
    "Смена в Пятёрочке: 2 500 ₽ / Бизнес-карты в 8 местах: / как неделя таких смен / Без вложений",
    "Как заработать на РКО с нуля: / 1) пишешь мне / 2) ИП онлайн за 1-3 дня / 3) бизнес-карты за вечер"
    " / 4) ждёшь месяц-полтора / 5) забираешь",
    "Тебе 18+, пашешь больше всех, / а денег меньше всех? / Пока ты на смене, / другие забирают деньги за РКО",
    "Курьер: 12 часов на ногах / за 3 000 ₽ / Бизнес-карты с телефона: / в разы больше",
    "«РКО это развод» / Факты: / всё оформлено на тебя / доступ только у тебя / ты ничего не платишь",
    "Ищешь нишу третий год? / Самый простой вход: РКО",
    "Официант за эти деньги / работает 2 недели / Тут пара вечеров с телефона",
    "Что нужно для РКО: / 18+, паспорт РФ, / без долгов, / не госслужащий / Всё",
    "Открыл сам / и получил деньги / Позвал друзей: / за каждого ещё бонус",
    "Кассир: месяц за кассой / РКО: пара вечеров с телефона",
    "Почему деньги не сразу? / Выплата через месяц-полтора / Говорю как есть",
    "Стипендия 3 000 ₽? / Вот как поднять больше / за пару вечеров",
    "Завод: 5/2 с 8 до 17 / РКО: пара вечеров с телефона",
    "ИП звучит страшно? / Онлайн, бесплатно, 1-3 дня / Подскажу каждый шаг",
    "Почему платят за РКО: / б@нкам нужны клиенты с ИП / За каждого они платят / Часть твоя",
    "Просят твои пароли и коды? / Беги / Я не прошу / Доступ только у тебя",
    "Рефералка: 2к за друга / РКО на себя в 8 местах: / в разы больше",
    "Друг сидит без денег? / Скинь ему это / За каждого друга бонус тебе",
    "Нужно вкладываться? / Нет / Ни рубля",
    "3 ошибки новичка в РКО: / 1) передать кому-то доступ / 2) ждать денег в тот же день / 3) идти с долгами",
    "Откуда деньги за РКО? / Это рекламный бюджет б@нков / Они платят за нового клиента",
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

# Фоны по кругу: POV-ходьба, ночной город, тёмный, стол с кофе.
BG_CYCLE = ["pov", "ночной_город", "тёмный", "стол"]
MUSIC = [
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
    """Неразрывные пробелы: «3 000 ₽», «8 местах», «1) пишешь» не рвутся по строкам."""
    text = re.sub(r"(?<=\d) (?=\d{3}\b)", NBSP, text)
    text = re.sub(r" (?=₽)", NBSP, text)
    text = re.sub(r"(?<=\d) (?=\S)", NBSP, text)
    return re.sub(r"(?<=\d\)) ", NBSP, text)


def greedy(text, f, max_w):
    lines, cur = [], ""
    for word in glue(text).split(" "):
        trial = f"{cur} {word}".strip()
        if f.getlength(trial) <= max_w or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def balanced(text, f, max_w):
    """Ровные строки: самая узкая ширина без лишних строк (как wrap в make_videos.py)."""
    n = len(greedy(text, f, max_w))
    lo, hi = 1, max_w
    while lo < hi:
        mid = (lo + hi) // 2
        if len(greedy(text, f, mid)) <= n:
            hi = mid
        else:
            lo = mid + 1
    return greedy(text, f, lo)


def fits(lines, f):
    return len(lines) <= 2 and all(f.getlength(l) + 2 * OUTLINE <= MAX_TEXT_W for l in lines)


def split_segment(seg, f):
    """Кусок текста → экраны по ≤ 2 строки: если не влезает, режем по словам на равные части."""
    words = glue(seg).split(" ")
    for m in range(1, len(words) + 1):
        parts, n = [], len(words)
        bounds = [round(n * k / m) for k in range(m + 1)]
        parts = [" ".join(words[a:b]) for a, b in zip(bounds, bounds[1:])]
        wrapped = [balanced(p, f, MAX_TEXT_W - 2 * OUTLINE) for p in parts]
        if all(fits(w, f) for w in wrapped):
            return wrapped
    raise SystemExit(f"Слово не влезает в ширину: {seg!r}")


def layout_video(text):
    """Один кегль на весь ролик: самый крупный (≤ 100, ≥ 90), при котором каждый « / »-кусок
    укладывается не больше чем в 2 экрана. Возвращает (шрифт, [строки экрана, ...])."""
    segs = [s.strip() for s in text.split(" / ") if s.strip()]
    for size in range(FONT_SIZE, FONT_MIN - 1, -2):
        f = font(size)
        screens = [scr for seg in segs for scr in split_segment(seg, f)]
        if len(screens) <= len(segs) or size == FONT_MIN:
            return f, screens
    raise AssertionError


# ---------- оверлеи (PNG с прозрачностью) ----------

def draw_lines(d, f, lines, cx, cy, fill, stroke, spacing=LINE_SPACING):
    step = f.size * spacing
    top = cy - step * len(lines) / 2
    boxes = []
    for k, line in enumerate(lines):
        y = top + step * (k + 0.5)
        kw = dict(font=f, anchor="mm", fill=fill)
        if stroke:
            kw.update(stroke_width=OUTLINE, stroke_fill=(0, 0, 0, 255))
        d.text((cx, y), line, **kw)
        boxes.append(bbox(d, (cx, y), line, kw))
    return boxes


def bbox(d, xy, text, kw):
    return d.textbbox(xy, text, **{k: v for k, v in kw.items() if k not in ("fill", "stroke_fill")})


def check_safe(boxes, what):
    for x0, y0, x1, y1 in boxes:
        assert x1 <= SAFE_RIGHT and y1 <= SAFE_BOTTOM and x0 >= 0 and y0 >= 0, (what, (x0, y0, x1, y1))


def nick_layer(path):
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    f = font(NICK_SIZE)
    kw = dict(font=f, anchor="mm", fill=(255, 255, 255, 255), stroke_width=5, stroke_fill=(0, 0, 0, 255))
    d.text((W // 2, NICK_Y), NICK, **kw)
    check_safe([bbox(d, (W // 2, NICK_Y), NICK, kw)], "ник")
    img.save(path)


def text_layer(f, lines, path):
    assert f.size >= FONT_MIN and len(lines) <= 2, lines
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    boxes = draw_lines(d, f, lines, TEXT_CX, TEXT_CY, (255, 255, 255, 255), True)
    check_safe(boxes, lines)
    img.save(path)


def plate_layer(path):
    """Белая плашка, чёрный текст: «Пиши» / «ХОЧУ» (самое крупное) / «→ @markovvv2»."""
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    rows = [("Пиши", 96), ("ХОЧУ", 200), ("→ " + NICK, 80)]
    fonts = [font(s) for _, s in rows]
    widths = [f.getlength(t) for (t, _), f in zip(rows, fonts)]
    heights = [s * 1.15 for _, s in rows]
    pad_x, pad_y = 56, 50
    pw = max(widths) + 2 * pad_x
    ph = sum(heights) + 2 * pad_y
    x0, y0 = TEXT_CX - pw / 2, TEXT_CY - ph / 2
    d.rounded_rectangle((x0, y0, x0 + pw, y0 + ph), 48, fill=(255, 255, 255, 255))
    y = y0 + pad_y
    boxes = [(x0, y0, x0 + pw, y0 + ph)]
    for (t, _), f, h in zip(rows, fonts, heights):
        d.text((TEXT_CX, y + h / 2), t, font=f, anchor="mm", fill=(0, 0, 0, 255))
        boxes.append(d.textbbox((TEXT_CX, y + h / 2), t, font=f, anchor="mm"))
        y += h
    check_safe(boxes, "плашка")
    img.save(path)


# ---------- фоны ----------

def still_to_video(still, path, sec=16):
    frames = sec * FPS
    subprocess.run([
        "ffmpeg", "-v", "error", "-y", "-loop", "1", "-i", str(still),
        "-vf", f"scale=2160:3840,zoompan=z='1+0.10*on/{frames}':x='iw/2-iw/zoom/2':y='ih/2-ih/zoom/2'"
               f":d={frames}:s={W}x{H}:fps={FPS},noise=alls=5:allf=t",
        "-frames:v", str(frames), "-c:v", "libx264", "-crf", "20", "-pix_fmt", "yuv420p", str(path),
    ], check=True)


def make_dark(path):
    """Тёмный фон: графит с мягким световым пятном."""
    img = Image.new("RGB", (W, H))
    px = img.load()
    for y in range(H):
        for x in range(0, W):
            r = math.hypot((x - W * 0.5) / W, (y - H * 0.42) / H)
            v = int(8 + 34 * max(0.0, 1 - r * 2.2))
            px[x, y] = (v, v, v + 5)
    img = img.filter(ImageFilter.GaussianBlur(3))
    still = path.with_suffix(".png")
    img.save(still)
    still_to_video(still, path)


def make_coffee_table(path):
    """Стол с кофе сверху: деревянная столешница, чашка на блюдце, телефон, блокнот."""
    rng = random.Random(7)
    img = Image.new("RGB", (W, H), (92, 60, 38))
    d = ImageDraw.Draw(img)
    # доски
    for bx in range(0, W, 270):
        base = rng.randint(-10, 10)
        for x in range(bx, min(bx + 270, W)):
            for y in range(0, H, 3):
                g = math.sin(y / rng.uniform(38, 42) + x / 9.0 + bx) * 9 + rng.uniform(-6, 6)
                c = (int(128 + base + g * 1.6), int(82 + base * 0.7 + g * 1.1), int(48 + base * 0.5 + g * 0.7))
                d.line((x, y, x, y + 2), fill=c)
        d.line((bx, 0, bx, H), fill=(50, 32, 20), width=4)
    img = img.filter(ImageFilter.GaussianBlur(1.5))
    d = ImageDraw.Draw(img)
    # телефон
    d.rounded_rectangle((120, 1180, 480, 1900), 50, fill=(18, 18, 22))
    d.rounded_rectangle((136, 1196, 464, 1884), 40, fill=(32, 38, 56))
    # блокнот
    d.rectangle((620, 1250, 1040, 1800), fill=(236, 232, 222))
    for y in range(1310, 1780, 46):
        d.line((650, y, 1010, y), fill=(190, 200, 215), width=3)
    # тень и чашка на блюдце
    shadow = Image.new("L", (W, H), 0)
    ImageDraw.Draw(shadow).ellipse((300, 470, 860, 1030), fill=150)
    shadow = shadow.filter(ImageFilter.GaussianBlur(40))
    img.paste((20, 12, 8), (0, 0), shadow)
    d = ImageDraw.Draw(img)
    cx, cy = 560, 720
    d.ellipse((cx - 270, cy - 270, cx + 270, cy + 270), fill=(240, 238, 234))
    d.ellipse((cx - 230, cy - 230, cx + 230, cy + 230), fill=(225, 222, 216))
    d.rounded_rectangle((cx + 165, cy - 45, cx + 300, cy + 45), 40, fill=(244, 242, 238))
    d.ellipse((cx - 175, cy - 175, cx + 175, cy + 175), fill=(250, 249, 246))
    d.ellipse((cx - 150, cy - 150, cx + 150, cy + 150), fill=(74, 42, 22))
    d.ellipse((cx - 120, cy - 120, cx + 120, cy + 120), fill=(150, 98, 58))
    d.ellipse((cx - 70, cy - 85, cx + 60, cy + 55), fill=(196, 150, 104))
    img = img.filter(ImageFilter.GaussianBlur(1.0))
    still = path.with_suffix(".png")
    img.save(still)
    still_to_video(still, path)


def make_night_city(path):
    """Ночной город: силуэты домов с огнями окон и размытые огни улицы (боке)."""
    rng = random.Random(3)
    img = Image.new("RGB", (W, H))
    d = ImageDraw.Draw(img)
    for y in range(H):
        t = y / H
        d.line((0, y, W, y), fill=(int(8 + 14 * t), int(10 + 12 * t), int(28 + 22 * t)))
    x = -40
    while x < W:
        bw, bh = rng.randint(110, 230), rng.randint(500, 1300)
        top = H - 420 - bh
        d.rectangle((x, top, x + bw, H), fill=(10, 11, 18))
        for wy in range(top + 30, H - 440, 44):
            for wx in range(x + 16, x + bw - 20, 30):
                if rng.random() < 0.33:
                    c = rng.choice([(255, 210, 130), (255, 236, 190), (180, 210, 255)])
                    d.rectangle((wx, wy, wx + 14, wy + 22), fill=c)
        x += bw + rng.randint(4, 30)
    bokeh = Image.new("RGB", (W, H))
    bd = ImageDraw.Draw(bokeh)
    for _ in range(90):
        r = rng.randint(18, 70)
        cx, cy = rng.randint(0, W), rng.randint(int(H * 0.55), H)
        c = rng.choice([(255, 170, 60), (255, 80, 60), (255, 230, 170), (90, 160, 255)])
        k = rng.uniform(0.35, 0.8)
        bd.ellipse((cx - r, cy - r, cx + r, cy + r), fill=tuple(int(v * k) for v in c))
    bokeh = bokeh.filter(ImageFilter.GaussianBlur(14))
    img = img.filter(ImageFilter.GaussianBlur(2.5))

    img = ImageChops.add(img, bokeh)
    still = path.with_suffix(".png")
    img.save(still)
    still_to_video(still, path)


def ensure_generated():
    GEN_DIR.mkdir(exist_ok=True)
    if not (GEN_DIR / "тёмный.mp4").exists():
        make_dark(GEN_DIR / "тёмный.mp4")
    if not (GEN_DIR / "ночной_город.mp4").exists():
        make_night_city(GEN_DIR / "ночной_город.mp4")
    if not (GEN_DIR / "стол_кофе.mp4").exists():
        make_coffee_table(GEN_DIR / "стол_кофе.mp4")


FILL = f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H}"
THEMES = {
    # POV-ходьба: ночная улица от первого лица + покачивание шага и медленный наезд
    "pov": (BG_DIR / "6044999852_1_tiktok_6a9934d5e66243_74400506.mp4",
            f"scale={int(W * 1.18)}:{int(H * 1.18)}:force_original_aspect_ratio=increase,"
            f"crop={W}:{H}:x='(iw-{W})/2+22*sin(2*PI*t*0.95)':y='(ih-{H})/2-30+34*abs(sin(2*PI*t*0.95))',"
            "eq=brightness=0.04"),
    # ночной город: огни домов и улицы (в «фоны» подходящего ролика нет — сгенерирован)
    "ночной_город": (GEN_DIR / "ночной_город.mp4", FILL),
    "тёмный": (GEN_DIR / "тёмный.mp4", FILL),
    "стол": (GEN_DIR / "стол_кофе.mp4", FILL),
}


# ---------- рендер ----------

def screen_times(screens):
    """Время на экраны: по числу слов, всего 5–9 с текста + 3 с плашки = 8–12 с."""
    weights = [0.9 + 0.3 * len(" ".join(s).replace(NBSP, " ").split()) for s in screens]
    total = min(9.0, max(5.0, sum(weights)))
    k = total / sum(weights)
    t, out = 0.0, []
    for w in weights:
        out.append((round(t, 2), round(t + w * k, 2)))
        t += w * k
    return round(total, 2), out


def render(i, rng, tmp):
    assert not BANNED.search(TEXTS[i - 1]), TEXTS[i - 1]
    f, screens = layout_video(TEXTS[i - 1])
    tsec, times = screen_times(screens)
    dur = round(tsec + PLATE_SEC, 2)

    theme = BG_CYCLE[(i - 1) % len(BG_CYCLE)]
    bg, bg_vf = THEMES[theme]
    music = MUS_DIR / MUSIC[(i - 1) % len(MUSIC)]

    nick = tmp / f"{i}_nick.png"
    nick_layer(nick)
    plate = tmp / f"{i}_plate.png"
    plate_layer(plate)
    layers = []
    for k, lines in enumerate(screens):
        p = tmp / f"{i}_t{k}.png"
        text_layer(f, lines, p)
        layers.append(p)

    bd = probe_duration(bg)
    bg_in = ["-ss", f"{rng.uniform(0, bd - dur):.2f}", "-i", str(bg)] if bd > dur + 0.5 \
        else ["-stream_loop", "-1", "-i", str(bg)]
    md = probe_duration(music)
    mus_in = ["-ss", f"{rng.uniform(0, max(0, md - dur - 1)):.2f}"] if md > dur + 1 else ["-stream_loop", "-1"]

    ins = [*bg_in, *mus_in, "-i", str(music), "-i", str(nick), "-i", str(plate)]
    for p in layers:
        ins += ["-i", str(p)]
    dim = {"тёмный": 0.2, "стол": 0.35, "ночной_город": 0.3}.get(theme, DIM)
    fc = [f"[0:v]{bg_vf},setsar=1,fps={FPS},drawbox=c=black@{dim}:t=fill,trim=0:{dur},setpts=PTS-STARTPTS[v0]"]
    last = "v0"
    for k, (a, b) in enumerate(times):
        fc.append(f"[{last}][{4 + k}:v]overlay=0:0:enable='between(t,{a},{b - 0.001:.3f})'[v{k + 1}]")
        last = f"v{k + 1}"
    fc.append(f"[{last}][3:v]overlay=0:0:enable='gte(t,{tsec})',fade=t=in:st=0:d=0.15[vp]")
    fc.append("[vp][2:v]overlay=0:0[vout]")
    fc.append(f"[1:a]loudnorm=I=-14,afade=t=in:d=0.2,afade=t=out:st={dur - 0.6}:d=0.6[aout]")

    out = OUT_DIR / f"{i:02d}.mp4"
    subprocess.run(["ffmpeg", "-v", "error", "-y", *ins, "-filter_complex", ";".join(fc),
                    "-map", "[vout]", "-map", "[aout]", "-t", str(dur), "-r", str(FPS),
                    "-c:v", "libx264", "-preset", "medium", "-crf", "21", "-pix_fmt", "yuv420p",
                    "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", str(out)], check=True)
    print(f"{out.name}: {dur:.1f} с, {f.size} px, экранов {len(screens)}, фон {theme}, музыка {music.name}",
          flush=True)
    for (a, b), lines in zip(times, screens):
        print(f"   {a:4.1f}–{b:4.1f}  " + " ⏎ ".join(lines).replace(NBSP, " "), flush=True)


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
    ensure_generated()
    nums = range(1, 22) if args.only == "all" else [int(x) for x in args.only.split(",")]
    with tempfile.TemporaryDirectory() as t:
        for i in nums:
            render(i, rng, Path(t))
    write_descriptions()
    print("Готово:", OUT_DIR)


if __name__ == "__main__":
    main()
