import re
import json
import random
import httpx
import time
from datetime import datetime
from bson import ObjectId
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.enums import ParseMode
from database.connection import db
from Assets.files import ACHIEVE_IMG
from config import Config

NVIDIA_API_KEY = "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"
PAGE_SIZE = 6


async def random_achievement_hint(user_id: int):
    earned_ids = await db.db["user_achievements"].distinct("achievement_id", {"user_id": user_id})
    obj_ids = []
    for eid in earned_ids:
        try:
            obj_ids.append(ObjectId(eid))
        except Exception:
            pass
    row = await db.db["achievements"].find_one(
        {"_id": {"$nin": obj_ids}},
        sort=[("_id", 1)]
    )
    if not row:
        return "🏆 You've unlocked everything. Absolute legend."
    return f"🎯 <b>Hint Unlocked</b>\n\n🏆 <b>{row['title']}</b>\n📖 {row['description']}\n\nKeep playing to unlock it!"


async def ai_generate_condition(title: str, description: str):
    prompt = f"You are a cricket game logic engine.\nAnalyze this achievement and decide how progress should be tracked.\nAchievement:\nTitle: {title}\nDescription: {description}\nReturn STRICT JSON ONLY in this exact format:\n{{\n  \"scope\": \"career|match|innings\",\n  \"stat\": \"runs|wickets|maidens|matches|partnership|catches|sixes|fours\",\n  \"target\": number\n}}\nRules:\n- Scope must match description meaning\n- Target must be realistic\n- No explanation\n- JSON only"
    raw = await _ai(prompt, temp=0.2, tokens=120)
    return json.loads(raw)


def normalize_condition(cond):
    if cond is None: return {}
    if isinstance(cond, dict): return cond
    if isinstance(cond, str):
        try: return json.loads(cond)
        except Exception: return {}
    return {}


async def safe_callback_answer(cb, text: str):
    MAX = 180
    if len(text) <= MAX:
        await cb.answer(text, show_alert=True)
    else:
        await cb.answer("🎁 Surprise incoming…", show_alert=False)
        await cb.message.reply_text(text)


async def _ai(prompt, temp=0.9, tokens=180):
    payload = {
        "model": "meta/llama3-70b-instruct",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": temp,
        "max_tokens": tokens
    }
    async with httpx.AsyncClient(timeout=40) as ai:
        r = await ai.post("https://integrate.api.nvidia.com/v1/chat/completions", json=payload, headers={"Authorization": f"Bearer {NVIDIA_API_KEY}", "Content-Type": "application/json"})

    if r.status_code != 200: raise RuntimeError(f"NVIDIA API Error {r.status_code}:\n{r.text[:800]}")
    data = r.json()
    if "choices" not in data: raise RuntimeError(f"Malformed AI response:\n{json.dumps(data, indent=2)[:800]}")
    return data["choices"][0]["message"]["content"]


async def ai_roast_user(name, brutal=False):
    tone = "EXTREMELY savage, humiliating, esports-toxic" if brutal else "playful savage"
    prompt = f"Roast a cricket player.\nTone: {tone}\nName: {name}\n2–3 lines max."
    return (await _ai(prompt, temp=1.0, tokens=120))[:500]


async def ai_congrats(name, ach):
    moods = ["funny", "savage", "wholesome", "toxic esports"]
    prompt = f"Congratulate a cricket player.\nTone: {random.choice(moods)}.\n2–3 lines.\nPlayer: {name}\nAchievement: {ach['title']}"
    return await _ai(prompt)


async def generate_dynamic_achievement(user_id: int):
    prompt = "Create a UNIQUE cricket achievement.\nReturn STRICT JSON only:\n{\n  \"title\": \"...\",\n  \"description\": \"...\",\n  \"condition\": {\n    \"type\": \"batting|bowling|team\",\n    \"runs_gte\": number,\n    \"wickets_gte\": number\n  }\n}"
    raw = await _ai(prompt, temp=0.95)
    data = json.loads(raw)

    await db.db["achievements"].update_one(
        {"code": f"DYN_{user_id}_{random.randint(1000,9999)}"},
        {"$setOnInsert": {
            "title": data["title"],
            "description": data["description"],
            "condition": data["condition"],
            "rarity": "legendary",
            "is_dynamic": True,
            "difficulty": 80,
            "created_at": datetime.utcnow()
        }},
        upsert=True
    )


@Client.on_message(filters.command("achievements"))
async def achievements_cmd(client, message):
    user = message.from_user
    await evaluate_and_unlock_achievements(user.id)
    await db.ensure_pool()

    earned_ids = await db.db["user_achievements"].distinct("achievement_id", {"user_id": user.id})
    obj_ids = []
    for eid in earned_ids:
        try:
            obj_ids.append(ObjectId(eid))
        except Exception:
            pass
    earned = await db.db["achievements"].find({"_id": {"$in": obj_ids}}, {"title": 1}).to_list(length=200)

    if not earned:
        caption = await ai_roast_user(user.first_name, brutal=True)
    else:
        caption = f"🏆 <b>{user.first_name}'s Achievements</b>\n\n" + "\n".join(f"✅ {a['title']}" for a in earned[:10]) + f"\n\n📦 Total Unlocked: <b>{len(earned)}</b>"

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("📜 All Achievements", callback_data="ach_page_0")],
        [InlineKeyboardButton("✨ Surprise Me", callback_data="ach_surprise"), InlineKeyboardButton("❌ Close", callback_data="ach_close")]
    ])

    await client.send_photo(message.chat.id, ACHIEVE_IMG, caption=caption, parse_mode=ParseMode.HTML, reply_markup=kb)


async def build_page(user_id: int, page: int, match=None):
    await db.ensure_pool()
    offset = page * PAGE_SIZE

    earned_ids = await db.db["user_achievements"].distinct("achievement_id", {"user_id": user_id})
    earned_set = set(earned_ids)

    all_achs = await db.db["achievements"].find({}).skip(offset).limit(PAGE_SIZE).to_list(length=PAGE_SIZE)
    stats = await db.db["user_stats"].find_one({"user_id": user_id}) or {}
    total = await db.db["achievements"].count_documents({})

    text = f"🏆 <b>All Achievements</b>\n📦 Total: <b>{total}</b>\n\n"

    for a in all_achs:
        ach_id = str(a["_id"])
        achieved = ach_id in earned_set
        cond = normalize_condition(a.get("condition", {}))
        scope = cond.get("scope", "unknown")
        icon = "🧧" if achieved else "⬜"
        cur, tgt = get_progress(a, stats, match or {})
        text += f"{icon} <b>{a['title']}</b>\n📖 {a['description']}\n📊 Progress: <b>{cur} / {tgt}</b>\n🏷️ {a.get('rarity', 'common')} | {scope}\n\n"

    return text


@Client.on_callback_query(filters.regex("^ach_"))
async def achievements_callback(client, cb):
    await cb.answer()
    data = cb.data

    if data == "ach_close": return await cb.message.delete()

    if data == "ach_surprise":
        await cb.answer("🎁 Surprise!", show_alert=False)
        text = await random_achievement_hint(cb.from_user.id)
        return await cb.message.reply_text(text, parse_mode=ParseMode.HTML)

    if data.startswith("ach_page_"):
        page = int(data.split("_")[-1])
        text = await build_page(cb.from_user.id, page)

        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("⬅️ Back", callback_data=f"ach_page_{max(page-1,0)}"), InlineKeyboardButton("➡️ Next", callback_data=f"ach_page_{page+1}")],
            [InlineKeyboardButton("❌ Close", callback_data="ach_close")]
        ])
        await cb.message.edit_caption(caption=text, parse_mode=ParseMode.HTML, reply_markup=kb)


OWNER_ID = next(iter(Config.OWNER_IDS))


def extract_json_array(text: str) -> str:
    start = text.find("[")
    if start == -1: raise ValueError("No JSON array start found")
    bracket_count = 0
    for i in range(start, len(text)):
        if text[i] == "[": bracket_count += 1
        elif text[i] == "]":
            bracket_count -= 1
            if bracket_count == 0: return text[start:i + 1]
    raise ValueError("JSON array not closed")


def get_progress(ach, user_stats, match):
    cond = normalize_condition(ach.get("condition", {}))
    scope = cond.get("scope")
    stat = cond.get("stat")
    target = cond.get("target", 0)
    current = 0

    if scope == "career": current = user_stats.get(stat, 0)
    elif scope == "match": current = match.get(stat, 0)
    elif scope == "innings": current = match.get("innings_stats", {}).get(stat, 0)

    return min(current, target), target


def build_condition():
    presets = [
        {"scope": "career", "stat": "runs", "target": 1000},
        {"scope": "career", "stat": "wickets", "target": 100},
        {"scope": "career", "stat": "matches", "target": 50},
        {"scope": "innings", "stat": "runs", "target": 100},
        {"scope": "innings", "stat": "wickets", "target": 5},
        {"scope": "match", "stat": "runs", "target": 50},
        {"scope": "match", "stat": "wickets", "target": 3},
    ]
    chosen = random.choice(presets)
    return {"scope": chosen["scope"], "stat": chosen["stat"], "target": chosen["target"]}


async def evaluate_and_unlock_achievements(user_id: int, match=None):
    await db.ensure_pool()
    earned_ids = await db.db["user_achievements"].distinct("achievement_id", {"user_id": user_id})
    earned_obj_ids = []
    for eid in earned_ids:
        try:
            earned_obj_ids.append(ObjectId(eid))
        except Exception:
            pass

    achievements = await db.db["achievements"].find({"_id": {"$nin": earned_obj_ids}}).to_list(length=500)
    stats = await db.db["user_stats"].find_one({"user_id": user_id}) or {}
    unlocked = []

    for ach in achievements:
        cond = normalize_condition(ach.get("condition", {}))
        scope, stat, target = cond.get("scope"), cond.get("stat"), cond.get("target", 0)
        current = 0

        if scope == "career": current = stats.get(stat, 0)
        elif scope == "match": current = (match or {}).get(stat, 0)
        elif scope == "innings": current = (match or {}).get("innings_stats", {}).get(stat, 0)

        if target > 0 and current >= target:
            ach_id = str(ach["_id"])
            try:
                await db.db["user_achievements"].update_one(
                    {"user_id": user_id, "achievement_id": ach_id},
                    {"$setOnInsert": {"user_id": user_id, "achievement_id": ach_id, "unlocked_at": datetime.utcnow()}},
                    upsert=True
                )
            except Exception:
                pass
            unlocked.append(ach)

    return unlocked


def build_prompt(rarity: str, seed: int):
    return f"Generate EXACTLY 12 cricket achievements.\nSTRICT RULES:\n- ALL achievements rarity = {rarity}\n- Output STRICT JSON array only\n- Stop immediately after ]\n- Seed = {seed}\nIMPORTANT CONSTRAINTS:\n- DO NOT generate achievements related to catches, stumpings, run-outs, fielding-only actions, keeper-specific actions.\n- ONLY use actions supported by the bot: batting runs, wickets taken, maidens, matches played, partnerships, wins / losses, economy / strike-based performance, Captaincy based records.\nEach item MUST be EXACTLY:\n{{\n  \"code\": \"UNIQUE_CODE\",\n  \"title\": \"Short title\",\n  \"description\": \"One sentence requirement\",\n  \"difficulty\": 1-100\n}}"


@Client.on_message(filters.command("gene") & filters.user(OWNER_ID))
async def generate_achievements_by_rarity(client, message):
    if len(message.command) < 2: return await message.reply_text("❌ Usage:\n/gene common\n/gene rare\n/gene epic\n/gene legendary")

    rarity = message.command[1].lower()
    allowed = {"common", "rare", "epic", "legendary"}
    if rarity not in allowed: return await message.reply_text("❌ Invalid rarity.")

    status = await message.reply_text(f"⚙️ Initializing {rarity} generator...")
    await db.ensure_pool()

    total = await db.db["achievements"].count_documents({})
    if total >= 300: return await status.edit_text("🛑 Global achievement limit reached (300 max).")
    if rarity == "legendary":
        leg_count = await db.db["achievements"].count_documents({"rarity": "legendary"})
        if leg_count >= 15:
            return await status.edit_text("🛑 Legendary limit reached (15 max).")

    seed = int(time.time())
    raw = ""
    try:
        raw = await _ai(build_prompt(rarity, seed), temp=0.3, tokens=600)
        json_text = extract_json_array(raw)
        achievements = json.loads(json_text)
        if not isinstance(achievements, list) or len(achievements) != 12: raise ValueError("Invalid achievement count")
    except Exception:
        print("AI RAW OUTPUT:\n", raw)
        return await status.edit_text("❌ AI failed to generate achievements.")

    inserted = 0
    for i, ach in enumerate(achievements, start=1):
        code = f"{rarity.upper()}_{int(time.time())}_{random.randint(100,999)}"
        try:
            condition = await ai_generate_condition(ach["title"], ach["description"])
        except Exception:
            condition = build_condition()
        try:
            await db.db["achievements"].insert_one({
                "code": code,
                "title": ach["title"],
                "description": ach["description"],
                "condition": condition,
                "rarity": rarity,
                "is_dynamic": False,
                "difficulty": ach.get("difficulty", 50),
                "created_at": datetime.utcnow()
            })
            inserted += 1
        except Exception:
            pass
        try:
            await status.edit_text(f"🏆 Generating {rarity.upper()} achievements\n✅ {i}/12 processed\n🎖️ {ach['title']}")
        except Exception:
            pass

    await status.edit_text(f"🔥 {rarity.upper()} generation complete!\n🏆 {inserted} achievements saved\n📦 Total ≤ 300")


@Client.on_message(filters.command("delach") & filters.user(OWNER_ID))
async def delete_achievement(client, message):
    if len(message.command) < 2: return await message.reply_text("❌ Usage:\n/delach <achievement title>\n/delach all")
    arg = " ".join(message.command[1:]).strip()

    await db.ensure_pool()

    if arg.lower() == "all":
        await db.db["user_achievements"].delete_many({})
        await db.db["achievements"].delete_many({})
        return await message.reply_text("🧨 <b>ALL achievements deleted.</b>\nDatabase reset complete.", parse_mode=ParseMode.HTML)

    row = await db.db["achievements"].find_one(
        {"title": {"$regex": f"^{re.escape(arg)}$", "$options": "i"}},
        {"_id": 1, "title": 1}
    )
    if not row: return await message.reply_text("❌ Achievement not found.\nTip: Title must match exactly.")
    await db.db["achievements"].delete_one({"_id": row["_id"]})

    await message.reply_text(f"🗑️ Achievement deleted:\n<b>{row['title']}</b>", parse_mode=ParseMode.HTML)
