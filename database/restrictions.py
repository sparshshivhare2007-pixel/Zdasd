from datetime import datetime
from database.connection import db


async def restrict_user(user_id: int, reason: str, admin_id: int):
    await db.db["restricted_users"].update_one(
        {"user_id": user_id},
        {"$set": {"user_id": user_id, "reason": reason, "admin_id": admin_id, "timestamp": datetime.utcnow()}},
        upsert=True
    )


async def unrestrict_user(user_id: int):
    await db.db["restricted_users"].delete_one({"user_id": user_id})


async def get_restriction_reason(user_id: int):
    try:
        row = await db.db["restricted_users"].find_one({"user_id": user_id}, {"reason": 1})
        if row:
            return row.get("reason")
    except Exception:
        pass
    return None


async def get_all_restricted_users():
    try:
        cursor = db.db["restricted_users"].find({}).sort("timestamp", -1)
        rows = await cursor.to_list(length=1000)
        return [
            {
                "user_id": row["user_id"],
                "reason": row.get("reason"),
                "admin_id": row.get("admin_id"),
                "timestamp": row.get("timestamp"),
            }
            for row in rows
        ]
    except Exception:
        return []
