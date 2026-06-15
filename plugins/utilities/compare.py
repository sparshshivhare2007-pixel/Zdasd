import asyncio
import io
import math
import html
import random
import os
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from pyrogram import Client, filters
from pyrogram.enums import ParseMode
from database.connection import db

ASSETS = os.path.join(os.path.dirname(__file__), "..", "..", "Assets")
FONT_PATH = os.path.join(ASSETS, "namefont.ttf")
FONT_PATH2 = os.path.join(ASSETS, "fonts.ttf")

CW, CH = 1000, 620


def _font(size: int, bold: bool = False):
    path = FONT_PATH if not bold else FONT_PATH2
    try:
        return ImageFont.truetype(path, size)
    except Exception:
        try:
            return ImageFont.truetype(FONT_PATH if bold else FONT_PATH2, size)
        except Exception:
            return ImageFont.load_default()


def _circle_mask(size: int) -> Image.Image:
    m = Image.new("L", (size, size), 0)
    ImageDraw.Draw(m).ellipse((0, 0, size - 1, size - 1), fill=255)
    return m


def _glow_ring(img: Image.Image, cx, cy, r, rgb, thickness=8):
    ov = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    for i in range(thickness, 0, -1):
        a = int(200 * (i / thickness) ** 1.5)
        d.ellipse((cx - r - i, cy - r - i, cx + r + i, cy + r + i),
                  outline=rgb + (a,), width=2)
    img.paste(ov, mask=ov.split()[3])


def _paste_avatar(card, photo_data, cx, cy, size=130, ring_rgb=(255, 200, 0)):
    r = size // 2
    mask = _circle_mask(size)

    av = None
    if photo_data is not None:
        try:
            raw = photo_data.read() if hasattr(photo_data, "read") else bytes(photo_data)
            av = Image.open(io.BytesIO(raw)).convert("RGBA").resize((size, size), Image.LANCZOS)
        except Exception:
            av = None

    if av is None:
        av = Image.new("RGBA", (size, size), (45, 45, 60, 255))
        dd = ImageDraw.Draw(av)
        dd.ellipse((0, 0, size - 1, size - 1), fill=(60, 60, 80))

    av.putalpha(mask)
    _glow_ring(card, cx, cy, r, ring_rgb, thickness=7)
    card.paste(av, (cx - r, cy - r), av)


def _draw_stat_bar(draw, x, y, w, h, v1, v2, c1, c2):
    total = v1 + v2
    if total == 0:
        r1 = 0.5
    else:
        r1 = v1 / total
    
    gap = 4
    bar_w = w - gap * 2
    split = int(bar_w * r1)
    
    draw.rounded_rectangle([x + gap, y, x + gap + split, y + h], radius=h // 2, fill=c1 + (200,))
    draw.rounded_rectangle([x + gap + split, y, x + gap + bar_w, y + h], radius=h // 2, fill=c2 + (200,))


def _draw_stat_rows(card, rows, c1, c2):
    d = ImageDraw.Draw(card, "RGBA")
    fy = 318
    rh = 50
    pad_x = 28

    for i, (label, v1, v2, hw) in enumerate(rows):
        y = fy + i * rh
        bg = (18, 20, 32, 220) if i % 2 == 0 else (12, 14, 24, 200)
        d.rectangle([(0, y), (CW, y + rh - 1)], fill=bg)

        fv1 = float(v1) if isinstance(v1, (int, float)) else 0.0
        fv2 = float(v2) if isinstance(v2, (int, float)) else 0.0
        tie = abs(fv1 - fv2) < 0.01
        p1_wins = ((fv1 > fv2) if hw else (fv1 < fv2)) if not tie else False

        GOLD = (255, 210, 0)
        DIM = (130, 130, 150)

        tc1 = GOLD if (p1_wins and not tie) else (DIM if tie else DIM)
        tc2 = GOLD if (not p1_wins and not tie) else (DIM if tie else DIM)

        vs1 = f"{fv1:.1f}" if isinstance(v1, float) else str(int(v1))
        vs2 = f"{fv2:.1f}" if isinstance(v2, float) else str(int(v2))

        mid_y = y + rh // 2

        d.text((pad_x + 90, mid_y), vs1, fill=tc1, font=_font(22), anchor="mm")
        d.text((CW // 2, mid_y), str(label), fill=(170, 170, 200), font=_font(13), anchor="mm")
        d.text((CW - pad_x - 90, mid_y), vs2, fill=tc2, font=_font(22), anchor="mm")

        bar_y = y + rh - 8
        _draw_stat_bar(d, 140, bar_y, CW - 280, 5, fv1, fv2, c1, c2)


def _design_neon_dark(av1, av2, n1, n2, score1, score2, rows):
    C1 = (255, 50, 90)
    C2 = (40, 130, 255)
    BG = (6, 8, 18)

    card = Image.new("RGBA", (CW, CH), BG + (255,))
    ov = Image.new("RGBA", (CW, CH), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)

    cx = CW // 2

    def poly(pts, c, a):
        d.polygon(pts, fill=c + (a,))

    poly([(0, 0), (cx - 20, 0), (cx - 50, CH), (0, CH)], C1, 22)
    poly([(0, 0), (cx - 60, 0), (cx - 120, CH), (0, CH)], C1, 12)
    poly([(0, 0), (80, 0), (50, CH), (0, CH)], C1, 35)

    poly([(CW, 0), (cx + 20, 0), (cx + 50, CH), (CW, CH)], C2, 22)
    poly([(CW, 0), (cx + 60, 0), (cx + 120, CH), (CW, CH)], C2, 12)
    poly([(CW, 0), (CW - 80, 0), (CW - 50, CH), (CW, CH)], C2, 35)

    poly([(cx - 18, 0), (cx + 18, 0), (cx + 14, CH), (cx - 14, CH)], (110, 90, 200), 28)
    poly([(cx - 5, 0), (cx + 5, 0), (cx + 4, CH), (cx - 4, CH)], (180, 160, 255), 75)

    card.paste(ov, mask=ov.split()[3])

    header_ov = Image.new("RGBA", (CW, CH), (0, 0, 0, 0))
    dh = ImageDraw.Draw(header_ov)
    dh.rectangle([(0, 0), (CW, 68)], fill=(12, 12, 28, 230))
    dh.rectangle([(0, CH - 62), (CW, CH)], fill=(12, 12, 28, 230))
    card.paste(header_ov, mask=header_ov.split()[3])

    _paste_avatar(card, av1, 160, 200, size=130, ring_rgb=C1[:3])
    _paste_avatar(card, av2, CW - 160, 200, size=130, ring_rgb=C2[:3])

    d2 = ImageDraw.Draw(card)

    d2.text((CW // 2, 22), "⚔  HEAD TO HEAD  ⚔", fill=(210, 195, 255), font=_font(22), anchor="mm")
    d2.text((CW // 2, 50), "NEXORA CRICKET", fill=(70, 65, 105), font=_font(13), anchor="mm")

    n1_short = n1[:13]
    n2_short = n2[:13]
    d2.text((160, 278), n1_short, fill=C1, font=_font(24), anchor="mm")
    d2.text((CW - 160, 278), n2_short, fill=C2, font=_font(24), anchor="mm")

    sc1_c = (255, 215, 0) if score1 >= score2 else (120, 120, 145)
    sc2_c = (255, 215, 0) if score2 >= score1 else (120, 120, 145)
    d2.text((160, 303), f"[ {score1} pts ]", fill=sc1_c, font=_font(15), anchor="mm")
    d2.text((CW - 160, 303), f"[ {score2} pts ]", fill=sc2_c, font=_font(15), anchor="mm")

    _draw_stat_rows(card, rows, C1[:3], C2[:3])

    if score1 > score2:
        vt, vc = f"🏆  {n1_short} DOMINATES", C1
    elif score2 > score1:
        vt, vc = f"🏆  {n2_short} TAKES THE EDGE", C2
    else:
        vt, vc = "⚖️  DEAD HEAT — TOO CLOSE TO CALL", (200, 200, 255)
    d2.text((CW // 2, CH - 28), vt, fill=vc, font=_font(19), anchor="mm")

    buf = io.BytesIO()
    card.convert("RGB").save(buf, format="JPEG", quality=94)
    buf.seek(0)
    return buf


def _design_stadium(av1, av2, n1, n2, score1, score2, rows):
    C1 = (255, 85, 0)
    C2 = (0, 185, 255)
    BG = (5, 9, 7)

    card = Image.new("RGBA", (CW, CH), BG + (255,))
    ov = Image.new("RGBA", (CW, CH), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)

    def poly(pts, c, a=None):
        if a is None:
            if len(c) == 4:
                d.polygon(pts, fill=c)
            else:
                raise ValueError("Alpha missing for RGB color")
        else:
            d.polygon(pts, fill=c + (a,))


    for i in range(6):
        ox = i * 60
        poly(
            [(ox, 0), (ox + 100, 0), (ox - 90, CH), (ox - 150, CH)],
            C1,
            max(0, 16 - i * 2)
        )

    for i in range(6):
        ox = CW - i * 60
        poly(
            [(ox, 0), (ox - 100, 0), (ox + 90, CH), (ox + 150, CH)],
            C2,
            max(0, 16 - i * 2)
        )

    d.ellipse(
        [(CW // 2 - 280, 55), (CW // 2 + 280, 310)],
        fill=(12, 42, 12, 100),
        outline=(35, 110, 35, 50),
        width=2
    )
    d.ellipse(
        [(CW // 2 - 170, 85), (CW // 2 + 170, 280)],
        fill=(18, 58, 18, 70)
    )

    poly([(0, 0), (CW, 0), (CW, 68), (0, 78)], (8, 13, 8), 235)
    poly([(0, CH - 62), (CW, CH - 50), (CW, CH), (0, CH)], (8, 13, 8), 235)

    card.paste(ov, mask=ov.split()[3])

    _paste_avatar(card, av1, 155, 198, size=130, ring_rgb=C1[:3])
    _paste_avatar(card, av2, CW - 155, 198, size=130, ring_rgb=C2[:3])

    d2 = ImageDraw.Draw(card)

    d2.text((CW // 2, 195), "VS", fill=(255, 215, 0), font=_font(50), anchor="mm")
    d2.text((CW // 2, 22), "🏟  CRICKET CLASH", fill=(200, 240, 200), font=_font(22), anchor="mm")
    d2.text((CW // 2, 50), "NEXORA STADIUM", fill=(55, 100, 55), font=_font(13), anchor="mm")

    n1_short = n1[:13]
    n2_short = n2[:13]
    d2.text((155, 278), n1_short, fill=C1, font=_font(24), anchor="mm")
    d2.text((CW - 155, 278), n2_short, fill=C2, font=_font(24), anchor="mm")

    sc1_c = (255, 215, 0) if score1 >= score2 else (140, 120, 90)
    sc2_c = (255, 215, 0) if score2 >= score1 else (140, 120, 90)
    d2.text((155, 303), f"[ {score1} pts ]", fill=sc1_c, font=_font(15), anchor="mm")
    d2.text((CW - 155, 303), f"[ {score2} pts ]", fill=sc2_c, font=_font(15), anchor="mm")

    _draw_stat_rows(card, rows, C1[:3], C2[:3])

    if score1 > score2:
        vt, vc = f"🔥  {n1_short} WINS THE CLASH", C1
    elif score2 > score1:
        vt, vc = f"💧  {n2_short} WINS THE CLASH", C2
    else:
        vt, vc = "⚖️  PERFECT TIE — INCREDIBLE!", (200, 255, 200)

    d2.text((CW // 2, CH - 28), vt, fill=vc, font=_font(19), anchor="mm")

    buf = io.BytesIO()
    card.convert("RGB").save(buf, format="JPEG", quality=94)
    buf.seek(0)
    return buf

def _design_battle_clash(av1, av2, n1, n2, score1, score2, rows):
    C1 = (190, 30, 255)
    C2 = (255, 195, 0)
    BG = (9, 7, 18)

    card = Image.new("RGBA", (CW, CH), BG + (255,))
    ov = Image.new("RGBA", (CW, CH), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)

    def poly(pts, c, a):
        d.polygon(pts, fill=c + (a,))

    cx, cy = CW // 2, 195
    for angle in range(0, 360, 18):
        rad = math.radians(angle)
        rad2 = math.radians(angle + 9)
        r1, r2 = 270, 195
        x1 = int(cx + r1 * math.cos(rad))
        y1 = int(cy + r1 * math.sin(rad))
        x2 = int(cx + r2 * math.cos(rad2))
        y2 = int(cy + r2 * math.sin(rad2))
        shade = C1 if angle % 36 < 18 else C2
        poly([(cx, cy), (x1, y1), (x2, y2)], shade, 16)

    poly([(0, 0), (CW // 2, 0), (CW // 2 - 35, CH), (0, CH)], C1, 30)
    poly([(0, 0), (CW // 2, 0), (CW // 2 - 70, CH), (0, CH)], C1, 16)
    poly([(CW, 0), (CW // 2, 0), (CW // 2 + 35, CH), (CW, CH)], C2, 30)
    poly([(CW, 0), (CW // 2, 0), (CW // 2 + 70, CH), (CW, CH)], C2, 16)

    poly([(0, 0), (CW, 0), (CW, 70), (0, 82)], (14, 10, 26, 235))
    poly([(0, CH - 62), (CW, CH - 50), (CW, CH), (0, CH)], (14, 10, 26, 235))

    bolt = [(cx - 7, 78), (cx + 20, 178), (cx - 4, 178), (cx + 24, 312), (cx - 24, 178), (cx + 4, 178)]
    d.polygon(bolt, fill=(255, 255, 255, 35))

    card.paste(ov, mask=ov.split()[3])

    _paste_avatar(card, av1, 155, 198, size=130, ring_rgb=C1[:3])
    _paste_avatar(card, av2, CW - 155, 198, size=130, ring_rgb=C2[:3])

    d2 = ImageDraw.Draw(card)
    d2.text((CW // 2, 22), "⚡  BATTLE CLASH  ⚡", fill=(235, 215, 255), font=_font(22), anchor="mm")
    d2.text((CW // 2, 50), "NEXORA RIVALRY", fill=(85, 65, 115), font=_font(13), anchor="mm")

    n1_short = n1[:13]
    n2_short = n2[:13]
    d2.text((155, 278), n1_short, fill=C1, font=_font(24), anchor="mm")
    d2.text((CW - 155, 278), n2_short, fill=C2, font=_font(24), anchor="mm")

    sc1_c = (255, 255, 255) if score1 >= score2 else (130, 110, 150)
    sc2_c = (255, 255, 255) if score2 >= score1 else (130, 110, 150)
    d2.text((155, 303), f"[ {score1} pts ]", fill=sc1_c, font=_font(15), anchor="mm")
    d2.text((CW - 155, 303), f"[ {score2} pts ]", fill=sc2_c, font=_font(15), anchor="mm")

    _draw_stat_rows(card, rows, C1[:3], C2[:3])

    if score1 > score2:
        vt, vc = f"⚡  {n1_short} REIGNS SUPREME", C1
    elif score2 > score1:
        vt, vc = f"⚡  {n2_short} REIGNS SUPREME", C2
    else:
        vt, vc = "⚡  SPARKS FLY — IT'S A TIE!", (235, 215, 255)
    d2.text((CW // 2, CH - 28), vt, fill=vc, font=_font(19), anchor="mm")

    buf = io.BytesIO()
    card.convert("RGB").save(buf, format="JPEG", quality=94)
    buf.seek(0)
    return buf


DESIGNS = [_design_neon_dark, _design_stadium, _design_battle_clash]


def build_compare_card(av1, av2, n1, n2, score1, score2, rows) -> io.BytesIO:
    fn = random.choice(DESIGNS)
    return fn(av1, av2, n1, n2, score1, score2, rows)


@Client.on_message(filters.command("compare"))
async def head2head_cmd(client, message):
    args = message.command[1:]
    users = []

    try:
        if message.reply_to_message and message.reply_to_message.from_user:
            users = [message.from_user, message.reply_to_message.from_user]
        elif len(args) == 1:
            u2 = await client.get_users(args[0])
            users = [message.from_user, u2]
        elif len(args) >= 2:
            u1 = await client.get_users(args[0])
            u2 = await client.get_users(args[1])
            users = [u1, u2]
        else:
            return await message.reply_text(
                "❌ Use <code>/compare @user</code> or reply to someone.",
                parse_mode=ParseMode.HTML,
            )
    except Exception:
        return await message.reply_text("❌ Invalid user(s). Try username or user ID.")

    u1, u2 = users
    uid1, uid2 = u1.id, u2.id

    status = await message.reply_text("⚔️ Building compare card…")

    s1 = await db.db["user_stats"].find_one({"user_id": uid1})
    s2 = await db.db["user_stats"].find_one({"user_id": uid2})

    if not s1 or not s2:
        return await status.edit_text(
            "⚠️ One or both players have no stats yet. Play some matches first 🏏"
        )

    def safe(v):
        return v or 0

    def batting_avg(s):
        outs = max(1, safe(s["matches"]) - safe(s.get("not_outs", 0)))
        return safe(s["runs"]) / outs

    def strike_rate(s):
        bf = safe(s["balls_faced"])
        return (safe(s["runs"]) / bf * 100) if bf > 0 else 0.0

    def economy(s):
        bb = safe(s["balls_bowled"])
        return (safe(s["runs_conceded"]) / (bb / 6)) if bb > 0 else 99.0

    def win_rate(s):
        m = safe(s["matches"])
        return (safe(s["wins"]) / m * 100) if m > 0 else 0.0

    fields_raw = [
        ("Runs",        s1["runs"],        s2["runs"],        True),
        ("Wickets",     s1["wickets"],     s2["wickets"],     True),
        ("Avg",         batting_avg(s1),   batting_avg(s2),   True),
        ("Strike Rate", strike_rate(s1),   strike_rate(s2),   True),
        ("Economy",     economy(s1),       economy(s2),       False),
    ]

    score1 = score2 = 0
    text_lines = []
    for label, v1, v2, hw in fields_raw:
        fv1 = float(v1) if isinstance(v1, (int, float)) else 0.0
        fv2 = float(v2) if isinstance(v2, (int, float)) else 0.0
        tie = abs(fv1 - fv2) < 0.01
        if not tie:
            if (fv1 > fv2 and hw) or (fv1 < fv2 and not hw):
                score1 += 1
                mk = "✅"
            else:
                score2 += 1
                mk = "❌"
        else:
            mk = "➖"
        vs1 = f"{fv1:.1f}" if isinstance(v1, float) else str(int(v1))
        vs2 = f"{fv2:.1f}" if isinstance(v2, float) else str(int(v2))
        sym = ">" if mk == "✅" else "<" if mk == "❌" else "="
        text_lines.append(f"• {label:<14}: {vs1} {sym} {vs2} {mk}")

    extra_fields = [
        ("Hat-Tricks",   safe(s1.get("hat_tricks", 0)), safe(s2.get("hat_tricks", 0)), True),
        ("MOMs",         safe(s1["moms"]),               safe(s2["moms"]),               True),
        ("Ducks",        safe(s1["ducks"]),              safe(s2["ducks"]),              False),
        ("Matches",      safe(s1["matches"]),            safe(s2["matches"]),            True),
        ("Win Rate",     win_rate(s1),                   win_rate(s2),                   True),
        ("Partnership",  safe(s1.get("best_partnership", 0)), safe(s2.get("best_partnership", 0)), True),
    ]
    for label, v1, v2, hw in extra_fields:
        fv1 = float(v1)
        fv2 = float(v2)
        tie = abs(fv1 - fv2) < 0.01
        if not tie:
            if (fv1 > fv2 and hw) or (fv1 < fv2 and not hw):
                score1 += 1
                mk = "✅"
            else:
                score2 += 1
                mk = "❌"
        else:
            mk = "➖"
        vs1 = f"{fv1:.1f}" if isinstance(v1, float) else str(int(fv1))
        vs2 = f"{fv2:.1f}" if isinstance(v2, float) else str(int(fv2))
        sym = ">" if mk == "✅" else "<" if mk == "❌" else "="
        text_lines.append(f"• {label:<14}: {vs1} {sym} {vs2} {mk}")

    if score1 > score2:
        verdict = f"{html.escape(u1.first_name)} dominates 😤"
    elif score2 > score1:
        verdict = f"{html.escape(u2.first_name)} takes the edge 🔥"
    else:
        verdict = "Too close to call 🤝"

    caption = (
        "⚔️ <b>𝗛𝗘𝗔𝗗 𝗧𝗢 𝗛𝗘𝗔𝗗</b>\n\n"
        f"🔴 {html.escape(u1.first_name)}  <b>{score1}</b> 🆚 <b>{score2}</b>  🔵 {html.escape(u2.first_name)}\n"
        "────┈┄┄╌╌╌╌┄┄┈────\n\n"
        "📊 <b>𝗦𝗧𝗔𝗧𝗦</b>\n"
        + "\n".join(text_lines)
        + f"\n\n🔥 <b>𝗩𝗘𝗥𝗗𝗜𝗖𝗧:</b> {verdict}"
    )

    try:
        from plugins.utilities.profile_card import download_user_photo
        av1_data, av2_data = await asyncio.gather(
            download_user_photo(client, uid1),
            download_user_photo(client, uid2),
        )
        display_rows = fields_raw[:5]
        loop = asyncio.get_event_loop()
        buf = await loop.run_in_executor(
            None,
            lambda: build_compare_card(av1_data, av2_data, u1.first_name, u2.first_name, score1, score2, display_rows),
        )
        await status.delete()
        await message.reply_photo(photo=buf, caption=caption, parse_mode=ParseMode.HTML)
    except Exception as e:
        print(f"Compare card error: {e}")
        await status.edit_text(caption, parse_mode=ParseMode.HTML)
