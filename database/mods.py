from datetime import datetime
from database.connection import db


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
