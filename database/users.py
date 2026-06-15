from datetime import datetime
from database.connection import db


async def get_top_players_runs(limit: int = 10):
    col = db.db["user_stats"]
    cursor = col.find({}, {"user_id": 1, "first_name": 1, "runs": 1, "matches": 1}).sort("runs", -1).limit(limit)
    rows = await cursor.to_list(length=limit)
    users_col = db.db["users"]
    result = []
    for row in rows:
        user = await users_col.find_one({"user_id": row["user_id"]}, {"name": 1})
        name = (user or {}).get("name") or row.get("first_name") or "Player"
        result.append({
            "user_id": row["user_id"],
            "name": name,
            "runs": row.get("runs", 0),
            "matches": row.get("matches", 0),
        })
    return result


async def add_user(user_id: int, name: str) -> bool:
    col = db.db["users"]
    existing = await col.find_one({"user_id": user_id})
    if existing:
        return False
    await col.insert_one({
        "user_id": user_id,
        "name": name,
        "coins": 1000,
        "games_played": 0,
        "notify_enabled": True,
        "created_at": datetime.utcnow(),
    })
    return True


async def total_users() -> int:
    return await db.db["users"].count_documents({})


async def get_mod(user_id: int):
    return await db.db["mods"].find_one({"user_id": user_id})


async def is_mod(user_id: int, min_tier: int = 1) -> bool:
    row = await db.db["mods"].find_one({"user_id": user_id}, {"tier": 1})
    if not row:
        return False
    return row.get("tier", 0) >= min_tier


async def add_or_update_mod(user_id: int, tier: int, owner_id: int):
    await db.db["mods"].update_one(
        {"user_id": user_id},
        {"$set": {"user_id": user_id, "tier": tier, "added_by": owner_id, "added_at": datetime.utcnow()}},
        upsert=True
    )


async def remove_mod(user_id: int):
    await db.db["mods"].delete_one({"user_id": user_id})


async def list_mods():
    cursor = db.db["mods"].find({}, {"user_id": 1, "tier": 1, "added_at": 1}).sort("tier", -1)
    return await cursor.to_list(length=200)


async def ban_user(user_id, first_name, reason, by):
    await db.db["user_bans"].update_one(
        {"user_id": user_id},
        {"$set": {"user_id": user_id, "first_name": first_name, "reason": reason, "banned_by": by, "banned_at": datetime.utcnow()}},
        upsert=True
    )


async def unban_user(user_id):
    await db.db["user_bans"].delete_one({"user_id": user_id})


async def get_user_ban(user_id):
    return await db.db["user_bans"].find_one({"user_id": user_id})


async def list_user_bans():
    cursor = db.db["user_bans"].find({})
    return await cursor.to_list(length=1000)


async def ban_group(chat_id, title, reason, by):
    await db.db["group_bans"].update_one(
        {"chat_id": chat_id},
        {"$set": {"chat_id": chat_id, "title": title, "reason": reason, "banned_by": by, "banned_at": datetime.utcnow()}},
        upsert=True
    )


async def unban_group(chat_id):
    await db.db["group_bans"].delete_one({"chat_id": chat_id})


async def get_group_ban(chat_id):
    return await db.db["group_bans"].find_one({"chat_id": chat_id})


async def list_group_bans():
    cursor = db.db["group_bans"].find({})
    return await cursor.to_list(length=1000)
