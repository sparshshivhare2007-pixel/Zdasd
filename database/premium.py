from database.connection import db
from datetime import datetime

PLANS = {
    "basic":    {"name": "⭐ Basic",    "price": 29,  "features": ["spam_free"]},
    "standard": {"name": "🔷 Standard", "price": 49,  "features": ["spam_free", "disabled_numbers"]},
    "pro":      {"name": "💎 Pro",      "price": 70,  "features": ["spam_free", "disabled_numbers", "edge_rule"]},
}

PLAN_ORDER = ["basic", "standard", "pro"]

_cache: dict = {}


async def grant_premium(chat_id: int, plan: str, granted_by: int) -> bool:
    if plan not in PLANS:
        return False
    await db.ensure_pool()
    await db.db["premium_groups"].update_one(
        {"chat_id": chat_id},
        {"$set": {
            "chat_id":    chat_id,
            "plan":       plan,
            "granted_by": granted_by,
            "granted_at": datetime.utcnow(),
            "active":     True,
        }},
        upsert=True,
    )
    _cache[chat_id] = {"plan": plan, "active": True}
    return True


async def revoke_premium(chat_id: int) -> bool:
    await db.ensure_pool()
    res = await db.db["premium_groups"].update_one(
        {"chat_id": chat_id},
        {"$set": {"active": False}},
    )
    _cache.pop(chat_id, None)
    return res.modified_count > 0


async def get_premium(chat_id: int):
    if chat_id in _cache:
        p = _cache[chat_id]
        return p if p.get("active") else None
    await db.ensure_pool()
    doc = await db.db["premium_groups"].find_one({"chat_id": chat_id, "active": True})
    if doc:
        _cache[chat_id] = {"plan": doc["plan"], "active": True}
        return _cache[chat_id]
    _cache[chat_id] = {"active": False}
    return None


async def is_premium(chat_id: int) -> bool:
    return (await get_premium(chat_id)) is not None


async def get_plan_features(chat_id: int) -> list:
    p = await get_premium(chat_id)
    if not p:
        return []
    return PLANS.get(p["plan"], {}).get("features", [])


async def can_use_feature(chat_id: int, feature: str) -> bool:
    return feature in (await get_plan_features(chat_id))


def plan_unlocked(premium: dict, req_plan: str) -> bool:
    if not premium or not premium.get("active"):
        return False
    try:
        return PLAN_ORDER.index(premium["plan"]) >= PLAN_ORDER.index(req_plan)
    except ValueError:
        return False
