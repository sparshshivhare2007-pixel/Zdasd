from database.connection import db


async def get_user_stats(user_id: int):
    try:
        await db.ensure_pool()
        return await db.db["user_stats"].find_one({"user_id": user_id})
    except Exception:
        return None


async def get_duel_stats(user_id: int):
    try:
        await db.ensure_pool()
        return await db.db["duel_stats"].find_one({"user_id": user_id})
    except Exception:
        return None


async def safe_fetchrow(query: str, *args):
    if not args:
        return None
    user_id = args[0]
    return await get_user_stats(user_id)
