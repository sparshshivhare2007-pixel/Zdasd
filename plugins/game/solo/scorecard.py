import io
import textwrap
from PIL import Image, ImageDraw, ImageFont

CARD_W = 770
CARD_H = 980
PURPLE_DARK = (28, 0, 60)
PURPLE_MID = (72, 0, 130)
PURPLE_LIGHT = (110, 0, 180)
BANNER_BG = (230, 225, 245)
BANNER_BORDER = (150, 120, 210)
STAT_BLUE = (20, 20, 180)
LABEL_DARK = (50, 30, 110)
WHITE = (255, 255, 255)
GOLD = (255, 210, 40)
GREEN = (40, 200, 80)
RED = (220, 50, 50)


def _load_font(path, size):
    try:
        return ImageFont.truetype(path, size)
    except Exception:
        return ImageFont.load_default()


def _draw_rounded_rect(draw, xy, radius, fill, outline=None, outline_width=2):
    x0, y0, x1, y1 = xy
    draw.rounded_rectangle([x0, y0, x1, y1], radius=radius, fill=fill,
                           outline=outline, width=outline_width)


def _draw_gradient_bg(img):
    draw = ImageDraw.Draw(img)
    for y in range(CARD_H):
        ratio = y / CARD_H
        r = int(PURPLE_DARK[0] + (PURPLE_MID[0] - PURPLE_DARK[0]) * ratio)
        g = int(PURPLE_DARK[1] + (PURPLE_MID[1] - PURPLE_DARK[1]) * ratio)
        b = int(PURPLE_DARK[2] + (PURPLE_MID[2] - PURPLE_DARK[2]) * ratio)
        draw.line([(0, y), (CARD_W, y)], fill=(r, g, b))


def _draw_section(draw, img, y_top, title_icon, name, stat_labels, stat_values,
                  name_font, stat_font, label_font, title_font, accent):
    cx = CARD_W // 2

    # — circle icon bg —
    r = 46
    draw.ellipse([cx - r, y_top - r, cx + r, y_top + r], fill=accent, outline=WHITE, width=3)
    tw = draw.textlength(title_icon, font=title_font)
    draw.text((cx - tw / 2, y_top - 32), title_icon, font=title_font, fill=WHITE)

    # — name banner —
    bw = 560
    bh = 56
    bx = cx - bw // 2
    by = y_top + r + 18
    _draw_rounded_rect(draw, [bx, by, bx + bw, by + bh], 28, BANNER_BG, BANNER_BORDER, 3)
    # truncate name if too long
    short_name = name[:22] if len(name) > 22 else name
    nw = draw.textlength(short_name, font=name_font)
    draw.text((cx - nw / 2, by + 8), short_name, font=name_font, fill=STAT_BLUE)

    # — stats banner —
    sw = 560
    sh = 64
    sx = cx - sw // 2
    sy = by + bh + 14
    _draw_rounded_rect(draw, [sx, sy, sx + sw, sy + sh], 28, BANNER_BG, BANNER_BORDER, 3)

    n_cols = len(stat_values)
    col_w = sw // n_cols
    for i, (lbl, val) in enumerate(zip(stat_labels, stat_values)):
        col_cx = sx + col_w * i + col_w // 2
        vw = draw.textlength(str(val), font=stat_font)
        draw.text((col_cx - vw / 2, sy + 5), str(val), font=stat_font, fill=STAT_BLUE)
        lw = draw.textlength(lbl, font=label_font)
        draw.text((col_cx - lw / 2, sy + 36), lbl, font=label_font, fill=LABEL_DARK)

    return sy + sh + 10


def build_solo_end_card(match) -> io.BytesIO:
    players = match.get("players", [])
    stats = match.get("player_stats", {})
    user_cache = match.get("user_cache", {})
    total_runs = match.get("total_runs", 0)
    total_balls = match.get("total_balls", 0)

    # Find best batter & best bowler
    top_batter_id, top_runs = None, -1
    top_bowler_id, top_wkts = None, -1

    for uid in players:
        p = stats.get(uid, {})
        if p.get("runs", 0) > top_runs:
            top_runs = p["runs"]
            top_batter_id = uid
        if p.get("wickets", 0) > top_wkts:
            top_wkts = p["wickets"]
            top_bowler_id = uid

    bat_name = user_cache.get(top_batter_id, "—") if top_batter_id else "—"
    bowl_name = user_cache.get(top_bowler_id, "—") if top_bowler_id else "—"

    bp = stats.get(top_batter_id, {}) if top_batter_id else {}
    bop = stats.get(top_bowler_id, {}) if top_bowler_id else {}

    bat_runs = bp.get("runs", 0)
    bat_balls = bp.get("balls_faced", 0)
    bat_6s = bp.get("sixes_count", 0)
    bat_4s = bp.get("fours_count", 0)

    bowl_runs = bop.get("runs_conceded", 0)
    bowl_balls = bop.get("balls_bowled", 0)
    overs_bowl = f"{bowl_balls // 6}.{bowl_balls % 6}"
    bowl_wkts = bop.get("wickets", 0)
    bowl_econ = round(bowl_runs / max(bowl_balls / 6, 0.1), 1)

    total_overs = f"{total_balls // 6}.{total_balls % 6}"

    name_font = _load_font("Assets/namefont.ttf", 38)
    stat_font = _load_font("Assets/namefont.ttf", 30)
    label_font = _load_font("Assets/fonts.ttf", 20)
    title_font = _load_font("Assets/fonts.ttf", 32)
    header_font = _load_font("Assets/namefont.ttf", 44)
    small_font = _load_font("Assets/fonts.ttf", 22)

    img = Image.new("RGB", (CARD_W, CARD_H))
    _draw_gradient_bg(img)
    draw = ImageDraw.Draw(img)

    # sparkle dots decoration
    import random
    rng = random.Random(42)
    for _ in range(60):
        x, y = rng.randint(0, CARD_W), rng.randint(0, CARD_H)
        r = rng.randint(1, 3)
        alpha = rng.randint(80, 180)
        draw.ellipse([x - r, y - r, x + r, y + r], fill=(255, 255, 255))

    # — HEADER —
    cx = CARD_W // 2
    hw = draw.textlength("🏆 MATCH OVER 🏆", font=header_font)
    draw.text((cx - hw / 2, 22), "🏆 MATCH OVER 🏆", font=header_font, fill=GOLD)

    # separator
    draw.line([(60, 80), (CARD_W - 60, 80)], fill=PURPLE_LIGHT, width=2)

    # — BATTER SECTION —
    y = _draw_section(
        draw, img, y_top=150,
        title_icon="🏏",
        name=bat_name,
        stat_labels=["R", "B", "6s", "4s"],
        stat_values=[bat_runs, bat_balls, bat_6s, bat_4s],
        name_font=name_font, stat_font=stat_font,
        label_font=label_font, title_font=title_font,
        accent=(100, 0, 200),
    )

    # — divider between sections —
    draw.line([(60, y + 20), (CARD_W - 60, y + 20)], fill=PURPLE_LIGHT, width=2)
    lw = draw.textlength("BEST BOWLER", font=small_font)
    draw.text((cx - lw / 2, y + 30), "BEST BOWLER", font=small_font, fill=GOLD)

    # — BOWLER SECTION —
    _draw_section(
        draw, img, y_top=y + 110,
        title_icon="⚾",
        name=bowl_name,
        stat_labels=["R", "O", "W", "E"],
        stat_values=[bowl_runs, overs_bowl, bowl_wkts, bowl_econ],
        name_font=name_font, stat_font=stat_font,
        label_font=label_font, title_font=title_font,
        accent=(60, 0, 160),
    )

    # — FOOTER —
    draw.line([(60, CARD_H - 90), (CARD_W - 90, CARD_H - 90)], fill=PURPLE_LIGHT, width=2)
    total_text = f"Total: {total_runs} runs | {total_overs} overs"
    tw = draw.textlength(total_text, font=small_font)
    draw.text((cx - tw / 2, CARD_H - 75), total_text, font=small_font, fill=WHITE)

    brand = "Nexora Cricket Bot"
    bw = draw.textlength(brand, font=small_font)
    draw.text((cx - bw / 2, CARD_H - 48), brand, font=small_font, fill=(180, 160, 220))

    buf = io.BytesIO()
    img.save(buf, "PNG")
    buf.seek(0)
    return buf
