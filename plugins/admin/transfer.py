import asyncio
import html
import json
from datetime import datetime
from io import BytesIO

from pyrogram import Client, filters
from pyrogram.enums import ParseMode

from config import Config
from database.connection import db


def _json_default(obj):
    if isinstance(obj, datetime):
        return {"$date": obj.isoformat()}
    return str(obj)


OWNER_FILTER = filters.user(list(Config.OWNER_IDS))

COLLECTIONS_MAP = {
    "user_stats": {
        "pg_table": "user_stats",
        "key": "user_id",
        "fields": [
            "user_id", "username", "first_name", "matches", "wins", "losses",
            "runs", "wickets", "balls_faced", "balls_bowled", "runs_conceded",
            "sixes", "fours", "centuries", "fifties", "ducks", "hat_tricks",
            "moms", "highest_score", "best_partnership", "penalties_received",
            "recent_form", "not_outs", "last_played_at",
        ],
    },
    "users": {
        "pg_table": "users",
        "key": "user_id",
        "fields": ["user_id", "name", "coins", "games_played", "notify_enabled", "created_at"],
    },
    "games": {
        "pg_table": "games",
        "key": "game_id",
        "fields": [
            "game_id", "chat_id", "title", "mode", "host_id", "status", "phase",
            "winner", "team_a_runs", "team_b_runs", "team_a_wickets", "team_b_wickets",
            "team_a_balls", "team_b_balls", "team_a_penalty", "team_b_penalty",
            "target", "innings", "motm", "toss_winner", "batting_team", "bowling_team",
            "overs", "created_at",
        ],
    },
    "duel_stats": {
        "pg_table": "duel_stats",
        "key": "user_id",
        "fields": [
            "user_id", "wins", "losses", "matches", "runs", "wickets",
            "highest_score", "ducks",
        ],
    },
    "mods": {
        "pg_table": "mods",
        "key": "user_id",
        "fields": ["user_id", "tier", "added_by", "added_at"],
    },
    "user_bans": {
        "pg_table": "user_bans",
        "key": "user_id",
        "fields": ["user_id", "first_name", "reason", "banned_by", "banned_at"],
    },
    "group_bans": {
        "pg_table": "group_bans",
        "key": "chat_id",
        "fields": ["chat_id", "title", "reason", "banned_by", "banned_at"],
    },
    "groups": {
        "pg_table": "groups",
        "key": "chat_id",
        "fields": ["chat_id", "title", "created_at"],
    },
    "restricted_users": {
        "pg_table": "restricted_users",
        "key": "user_id",
        "fields": ["user_id", "reason", "admin_id", "timestamp"],
    },
}


async def _transfer_table(pg_conn, collection_name: str, config: dict, status_msg) -> tuple:
    table = config["pg_table"]
    key_field = config["key"]
    fields = config["fields"]

    try:
        rows = await pg_conn.fetch(f"SELECT * FROM {table}")
    except Exception as e:
        return 0, 0, f"Table '{table}' fetch failed: {str(e)[:80]}"

    if not rows:
        return 0, 0, None

    col = db.db[collection_name]
    added = skipped = 0

    for row in rows:
        try:
            doc = {}
            for f in fields:
                if f in row.keys():
                    val = row[f]
                    if isinstance(val, datetime):
                        val = val
                    doc[f] = val

            key_val = doc.get(key_field)
            if key_val is None:
                skipped += 1
                continue

            existing = await col.find_one({key_field: key_val})
            if existing:
                skipped += 1
                continue

            await col.insert_one(doc)
            added += 1
        except Exception:
            skipped += 1

    return added, skipped, None


@Client.on_message(filters.command("transfer") & OWNER_FILTER)
async def transfer_cmd(client, message):
    args = message.command

    if len(args) < 2:
        return await message.reply_text(
            "📦 <b>PostgreSQL → MongoDB Transfer</b>\n\n"
            "<b>Usage:</b>\n"
            "<code>/transfer postgresql://user:pass@host:port/dbname</code>\n\n"
            "This will migrate all tables (user_stats, users, games, duel_stats, "
            "mods, bans, groups, restricted_users) from PostgreSQL into MongoDB.\n\n"
            "⚠️ Existing documents in MongoDB are <b>skipped</b> (no overwrite).\n"
            "📂 For JSON import use <b>/dbtrans</b> by replying to a JSON file.",
            parse_mode=ParseMode.HTML,
        )

    pg_url = args[1].strip()
    if not pg_url.startswith(("postgresql://", "postgres://")):
        return await message.reply_text(
            "❌ Invalid connection string.\n"
            "Must start with <code>postgresql://</code> or <code>postgres://</code>",
            parse_mode=ParseMode.HTML,
        )

    status = await message.reply_text(
        "🔌 <b>Connecting to PostgreSQL…</b>",
        parse_mode=ParseMode.HTML,
    )

    try:
        import asyncpg
        pg_conn = await asyncpg.connect(pg_url, timeout=15)
    except Exception as e:
        return await status.edit_text(
            f"❌ <b>PostgreSQL connection failed:</b>\n<code>{html.escape(str(e))}</code>",
            parse_mode=ParseMode.HTML,
        )

    try:
        await status.edit_text(
            "✅ <b>PostgreSQL connected!</b>\n🔄 Starting migration…\n\n"
            "This may take a while depending on data size.",
            parse_mode=ParseMode.HTML,
        )

        total_added = 0
        total_skipped = 0
        results_text = "📊 <b>Migration Results:</b>\n\n"

        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")

        for col_name, config in COLLECTIONS_MAP.items():
            try:
                await status.edit_text(
                    f"🔄 <b>Migrating:</b> <code>{col_name}</code>…",
                    parse_mode=ParseMode.HTML,
                )
            except Exception:
                pass

            added, skipped, err = await _transfer_table(pg_conn, col_name, config, status)
            total_added += added
            total_skipped += skipped

            if err:
                results_text += f"⚠️ <code>{col_name}</code>: {html.escape(err)}\n"
            else:
                results_text += f"✅ <code>{col_name}</code>: +{added} added, {skipped} skipped\n"

            try:
                docs = await db.db[col_name].find({}, {"_id": 0}).to_list(length=None)
                payload = json.dumps(docs, default=_json_default, ensure_ascii=False, indent=2)
                bio = BytesIO(payload.encode("utf-8"))
                bio.name = f"{col_name}_{timestamp}.json"
                await message.reply_document(
                    document=bio,
                    caption=(
                        f"📂 <b>{html.escape(col_name)}</b> snapshot\n"
                        f"📊 Docs: <code>{len(docs)}</code>"
                    ),
                    parse_mode=ParseMode.HTML,
                )
            except Exception as e:
                results_text += f"   📁 dump failed: {html.escape(str(e)[:60])}\n"

            await asyncio.sleep(0.2)

        results_text += (
            f"\n────┈┄┄╌╌╌╌┄┄┈────\n"
            f"📦 <b>Total Added:</b> {total_added}\n"
            f"⏭️ <b>Total Skipped:</b> {total_skipped}\n"
            f"✅ <b>Migration Complete!</b>"
        )

        await status.edit_text(results_text, parse_mode=ParseMode.HTML)

    except Exception as e:
        await status.edit_text(
            f"❌ <b>Migration error:</b>\n<code>{html.escape(str(e))}</code>",
            parse_mode=ParseMode.HTML,
        )
    finally:
        try:
            await pg_conn.close()
        except Exception:
            pass


import json
import asyncio
import html
from datetime import datetime

from pyrogram import Client, filters
from pyrogram.enums import ParseMode

from config import Config
from database.connection import db

OWNER_FILTER = filters.user(list(Config.OWNER_IDS))


def parse_mongo_date(value):
    """Convert Mongo-style date to datetime"""
    try:
        if isinstance(value, dict) and "$date" in value:
            return datetime.fromisoformat(value["$date"].replace("Z", "+00:00"))
        return value
    except Exception:
        return value


def clean_document(doc: dict):
    """Recursively clean document (handle dates, remove _id if needed)"""
    new_doc = {}

    for k, v in doc.items():
        if k == "_id":
            continue  # skip old Mongo _id

        if isinstance(v, dict):
            new_doc[k] = clean_document(v)
        elif isinstance(v, list):
            new_doc[k] = [
                clean_document(i) if isinstance(i, dict) else parse_mongo_date(i)
                for i in v
            ]
        else:
            new_doc[k] = parse_mongo_date(v)

    return new_doc


@Client.on_message(filters.command("dbtrans") & OWNER_FILTER)
async def dbtrans_cmd(client, message):
    if not message.reply_to_message or not message.reply_to_message.document:
        return await message.reply_text(
            "📂 <b>JSON → MongoDB Import</b>\n\n"
            "<b>Usage:</b>\n"
            "Reply to a JSON file with <code>/dbtrans collection_name</code>\n\n"
            "Example:\n"
            "<code>/dbtrans user_stats</code>",
            parse_mode=ParseMode.HTML
        )

    args = message.command
    if len(args) < 2:
        return await message.reply_text(
            "❌ Please specify collection name.\n"
            "Example: <code>/dbtrans user_stats</code>",
            parse_mode=ParseMode.HTML
        )

    collection_name = args[1]
    col = db.db[collection_name]

    status = await message.reply_text(
        "📥 <b>Downloading JSON file…</b>",
        parse_mode=ParseMode.HTML
    )

    try:
        file_path = await message.reply_to_message.download()
    except Exception as e:
        return await status.edit_text(
            f"❌ Download failed:\n<code>{html.escape(str(e))}</code>",
            parse_mode=ParseMode.HTML
        )

    try:
        await status.edit_text("📖 <b>Reading JSON data…</b>", parse_mode=ParseMode.HTML)

        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read().strip()

        # Detect format
        if content.startswith("["):
            data = json.loads(content)
        else:
            # line-by-line JSON
            data = [json.loads(line) for line in content.splitlines() if line.strip()]

    except Exception as e:
        return await status.edit_text(
            f"❌ JSON parse error:\n<code>{html.escape(str(e))}</code>",
            parse_mode=ParseMode.HTML
        )

    total = len(data)
    added = skipped = 0

    await status.edit_text(
        f"🚀 <b>Importing into:</b> <code>{collection_name}</code>\n"
        f"📊 Total records: {total}",
        parse_mode=ParseMode.HTML
    )

    for i, doc in enumerate(data):
        try:
            clean_doc = clean_document(doc)

            # unique key logic (user_id fallback)
            key = clean_doc.get("user_id") or clean_doc.get("game_id")

            if key:
                existing = await col.find_one({"user_id": key}) or await col.find_one({"game_id": key})
                if existing:
                    skipped += 1
                    continue

            await col.insert_one(clean_doc)
            added += 1

        except Exception:
            skipped += 1

        # update every 50 records
        if i % 50 == 0:
            try:
                await status.edit_text(
                    f"🔄 Processing...\n\n"
                    f"✅ Added: {added}\n"
                    f"⏭️ Skipped: {skipped}\n"
                    f"📊 Done: {i}/{total}",
                    parse_mode=ParseMode.HTML
                )
            except:
                pass

        await asyncio.sleep(0.01)

    await status.edit_text(
        "📦 <b>Import Complete!</b>\n\n"
        f"✅ <b>Added:</b> {added}\n"
        f"⏭️ <b>Skipped:</b> {skipped}\n"
        f"📊 <b>Total:</b> {total}",
        parse_mode=ParseMode.HTML
    )
