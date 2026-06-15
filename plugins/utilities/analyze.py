import os
import io
import asyncio
import random
import httpx

from pyrogram import Client, filters
from pyrogram.enums import ParseMode, ChatType
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from PIL import Image, ImageDraw, ImageFont

from database.connection import db
from utils.dbpass import safe_fetchrow

FONT_PATH = "Assets/fonts.ttf"

BG = (14, 10, 20)
PURPLE = (155, 89, 255)
WHITE = (240, 240, 240)
MUTED = (160, 160, 160)
GRID = (40, 35, 55)

NVIDIA_ENDPOINT = "https://integrate.api.nvidia.com/v1/chat/completions"
NVIDIA_API_KEY = "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"

LOADING_FRAMES = [
    "🧠 Reading match memories…",
    "📊 Breaking down numbers…",
    "🔥 Consulting cricket gods…",
]

ANALYSIS_MOODS = [
    {"tag": "🔥 On Fire", "style": "Aggressive playmaker", "emoji": "🔥⚡"},
    {"tag": "🧊 Ice Cold", "style": "Calm & clutch", "emoji": "🧊🎯"},
    {"tag": "🎭 Wildcard", "style": "Unpredictable chaos", "emoji": "🎭💥"},
    {"tag": "🧠 Tactical", "style": "Smart & calculated", "emoji": "🧠📊"},
    {"tag": "⚔️ Fighter", "style": "Grit & heart", "emoji": "⚔️💪"},
]

def analyze_buttons(chat_type):
    rows = []
    if chat_type in (ChatType.GROUP, ChatType.SUPERGROUP):
        rows.append([InlineKeyboardButton("🏟 Group Analysis", callback_data="analyze:group")])
    rows.append([InlineKeyboardButton("❌ Close", callback_data="analyze:close")])
    return InlineKeyboardMarkup(rows)

def back_button():
    return InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="analyze:back")]])

def format_hour_12h(hour: int) -> str:
    suffix = "AM" if hour < 12 else "PM"
    h = hour % 12
    h = 12 if h == 0 else h
    return f"{h} {suffix}"

def build_peak_time_graph(hour_counts: dict, peak_hour: int, group_name: str):
    W, H = 1280, 720
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)

    try:
        title_f = ImageFont.truetype(FONT_PATH, 52)
        label_f = ImageFont.truetype(FONT_PATH, 26)
        group_f = ImageFont.truetype(FONT_PATH, 28)
    except:
        title_f = label_f = group_f = ImageFont.load_default()

    draw.text((W // 2, 40), "PEAK PLAY TIME", fill=PURPLE, font=title_f, anchor="mm")

    safe_group = (group_name[:28] + "…") if len(group_name) > 30 else group_name
    draw.text((W - 40, 46), safe_group, fill=MUTED, font=group_f, anchor="rm")

    gx1, gy1 = 100, 120
    gx2, gy2 = W - 100, H - 140
    graph_h = gy2 - gy1
    graph_w = gx2 - gx1

    step_y = graph_h // 5
    for i in range(6):
        y = gy1 + i * step_y
        draw.line((gx1, y, gx2, y), fill=GRID)

    max_val = max(hour_counts.values(), default=1)
    step_x = graph_w / 23

    points = []

    for h in range(24):
        val = hour_counts.get(h, 0)
        x = gx1 + h * step_x
        y = gy2 - (val / max_val) * graph_h
        points.append((x, y))

        draw.ellipse((x - 4, y - 4, x + 4, y + 4), fill=PURPLE if h == peak_hour else WHITE)

        if h % 3 == 0:
            draw.text((x, gy2 + 12), format_hour_12h(h), fill=MUTED, font=label_f, anchor="mt")

    if len(points) > 1:
        draw.line(points, fill=PURPLE, width=3)

    buf = io.BytesIO()
    img.save(buf, "PNG", optimize=True)
    buf.seek(0)
    return buf

async def get_ai_analysis(prompt: str) -> str:
    headers = {
        "Authorization": f"Bearer {NVIDIA_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": "meta/llama-3.1-70b-instruct",
        "messages": [
            {"role": "system", "content": "You are a chill, savage but professional cricket analyst."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.8,
        "max_tokens": 400
    }

    async with httpx.AsyncClient(timeout=20) as client:
        r = await client.post(NVIDIA_ENDPOINT, json=payload, headers=headers)
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]

@Client.on_message(filters.command("analyze"))
async def analyze_cmd(client, message):
    target = message.from_user

    if message.reply_to_message and message.reply_to_message.from_user:
        target = message.reply_to_message.from_user
    elif len(message.command) > 1:
        try:
            arg = message.command[1]
            target = await client.get_users(int(arg) if arg.isdigit() else arg)
        except:
            return await message.reply_text("❌ User not found.")

    loading = await message.reply_text(LOADING_FRAMES[0])
    for frame in LOADING_FRAMES[1:]:
        await asyncio.sleep(0.6)
        await loading.edit_text(frame)

    stats = await safe_fetchrow("SELECT * FROM user_stats WHERE user_id=$1", target.id)

    if not stats:
        return await loading.edit_text("😶 No data found.")

    mood = random.choice(ANALYSIS_MOODS)

    prompt = f"""
STYLE:
• Analyze {target.first_name} stylishly

STATS:
Runs {stats['runs']} | Wickets {stats['wickets']}
Avg {(stats['runs'] / max(1, stats['matches'] - stats.get('not_outs', 0))):.2f}
SR {(stats['runs'] / max(1, stats['balls_faced']) * 100):.1f}
Econ {(stats['runs_conceded'] / max(1, stats['balls_bowled'] / 6)):.2f}

Mood: {mood['tag']}
"""

    try:
        analysis = await get_ai_analysis(prompt)
    except:
        return await loading.edit_text("⚠️ AI busy.")

    text = (
        "🧠 <b>𝗔𝗜 𝗣𝗟𝗔𝗬𝗘𝗥 𝗔𝗡𝗔𝗟𝗬𝗦𝗜𝗦</b>\n"
        f"👤 <b>{target.first_name}</b>\n"
        f"🎭 <b>Mood:</b> {mood['tag']} {mood['emoji']}\n"
        "────┈┄┄╌╌╌╌┄┄┈────\n\n"
        f"{analysis}\n\n"
        "────┈┄┄╌╌╌╌┄┄┈────\n"
        "✨ Nexora AI"
    )

    await loading.edit_text(
        text,
        parse_mode=ParseMode.HTML,
        reply_markup=analyze_buttons(message.chat.type)
    )

@Client.on_callback_query(filters.regex("^analyze:"))
async def analyze_callback(client, query):
    action = query.data.split(":")[1]

    if action == "close":
        return await query.message.delete()

    if action == "back":
        fake = query.message
        fake.from_user = query.from_user
        return await analyze_cmd(client, fake)

    if action == "group":
        if query.message.chat.type not in (ChatType.GROUP, ChatType.SUPERGROUP):
            return await query.answer("Groups only")

        member = await client.get_chat_member(query.message.chat.id, query.from_user.id)
        if not member.privileges:
            return await query.answer("Admins only")

        await send_group_analysis(client, query.message)

async def send_group_analysis(client, message):
    loading = await message.reply_text("📊 Scanning group activity…")

    chat_id = message.chat.id
    title = message.chat.title or "This Group"

    pipeline_hours = [
        {"$match": {"chat_id": chat_id}},
        {"$project": {"hour": {"$hour": "$created_at"}}},
        {"$group": {"_id": "$hour", "count": {"$sum": 1}}},
    ]
    hour_raw = await db.db["games"].aggregate(pipeline_hours).to_list(None)

    total_matches = await db.db["games"].count_documents({"chat_id": chat_id})

    pipeline_rank = [
        {"$group": {"_id": "$chat_id", "game_count": {"$sum": 1}}},
        {"$sort": {"game_count": -1}},
    ]
    ranks = await db.db["games"].aggregate(pipeline_rank).to_list(None)

    if total_matches < 3:
        return await loading.edit_text("😶 Not enough data yet.\nPlay a few matches to unlock analytics.", reply_markup=back_button())

    hour_counts = {int(r["_id"]): r["count"] for r in hour_raw if r["_id"] is not None}
    peak_hour = max(hour_counts, key=hour_counts.get) if hour_counts else 0

    rank = next((i + 1 for i, r in enumerate(ranks) if r["_id"] == chat_id), None)
    total_groups = len(ranks)

    graph = build_peak_time_graph(hour_counts=hour_counts, peak_hour=peak_hour, group_name=title)

    caption = (
        f"🏟️ <b>𝗚𝗥𝗢𝗨𝗣 𝗔𝗡𝗔𝗟𝗬𝗦𝗜𝗦</b>\n"
        f"📍 <b>{title}</b>\n"
        "────┈┄┄╌╌╌╌┄┄┈────\n\n"
        f"🔥 <b>Peak Hour:</b> {format_hour_12h(peak_hour)}\n"
        f"🎮 <b>Total Matches:</b> {total_matches}\n\n"
        "🏆 <b>ACTIVITY RANK</b>\n"
        f"#{rank} out of {total_groups} groups\n\n"
        "✨ Nexora • Group Intelligence"
    )

    await loading.delete()
    await client.send_photo(
        chat_id,
        photo=graph,
        caption=caption,
        parse_mode=ParseMode.HTML,
        reply_markup=back_button()
    )
    
