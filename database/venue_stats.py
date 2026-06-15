from database.connection import db


async def update_venue_stats(
    user_id: int,
    chat_id: int,
    chat_title: str,
    runs: int,
    wickets: int,
) -> None:
    await db.ensure_pool()
    await db.db["venue_stats"].update_one(
        {"user_id": user_id, "chat_id": chat_id},
        {
            "$inc": {"runs": runs, "wickets": wickets, "matches": 1},
            "$set": {"chat_title": chat_title},
            "$setOnInsert": {"user_id": user_id, "chat_id": chat_id},
        },
        upsert=True,
    )


async def get_user_venues(user_id: int) -> list:
    await db.ensure_pool()
    return await (
        db.db["venue_stats"]
        .find({"user_id": user_id})
        .sort("runs", -1)
        .limit(5)
        .to_list(length=5)
    )


async def get_best_venue(user_id: int) -> dict | None:
    venues = await get_user_venues(user_id)
    return venues[0] if venues else None


async def get_venue_leaderboard(chat_id: int, sort_by: str = "runs", limit: int = 10) -> list:
    await db.ensure_pool()
    field = sort_by if sort_by in ("runs", "wickets", "matches") else "runs"
    return await (
        db.db["venue_stats"]
        .find({"chat_id": chat_id})
        .sort(field, -1)
        .limit(limit)
        .to_list(length=limit)
    )


async def get_best_venue_runs_global() -> dict | None:
    await db.ensure_pool()
    docs = await db.db["venue_stats"].find().sort("runs", -1).limit(1).to_list(length=1)
    return docs[0] if docs else None


async def get_best_venue_wickets_global() -> dict | None:
    await db.ensure_pool()
    docs = await db.db["venue_stats"].find().sort("wickets", -1).limit(1).to_list(length=1)
    return docs[0] if docs else None
