"""Lightweight key/value settings backed by Mongo with in-memory cache."""

from typing import Any, Optional

from database.connection import db


_DEFAULTS: dict = {
    "maintenance_enabled": False,
    "maintenance_message": (
        "🛠 <b>Bot is under maintenance</b>\n"
        "──┈┄┄╌╌╌╌┄┄┈──\n"
        "Game commands are paused for a short while.\n"
        "Hang tight — we'll be back soon! 🏏"
    ),
}

_cache: dict = {}
_loaded: bool = False


def _col():
    return db.db["bot_settings"]


async def load_settings(force: bool = False) -> dict:
    """Load all settings from Mongo into the in-memory cache."""
    global _loaded
    if _loaded and not force:
        return _cache

    await db.ensure_pool()
    _cache.clear()
    _cache.update(_DEFAULTS)

    try:
        async for doc in _col().find({}):
            key = doc.get("_id")
            if key:
                _cache[key] = doc.get("value")
    except Exception as e:
        print(f"[settings] load failed: {e}")

    _loaded = True
    return _cache


async def get_setting(key: str, default: Any = None) -> Any:
    if not _loaded:
        await load_settings()
    return _cache.get(key, _DEFAULTS.get(key, default))


async def set_setting(key: str, value: Any) -> None:
    if not _loaded:
        await load_settings()
    _cache[key] = value
    try:
        await _col().update_one(
            {"_id": key},
            {"$set": {"value": value}},
            upsert=True,
        )
    except Exception as e:
        print(f"[settings] save failed for {key}: {e}")


# convenience helpers ---------------------------------------------------------

async def is_maintenance() -> bool:
    return bool(await get_setting("maintenance_enabled", False))


async def get_maintenance_message() -> str:
    return await get_setting("maintenance_message", _DEFAULTS["maintenance_message"])


async def set_maintenance(enabled: bool, message: Optional[str] = None) -> None:
    await set_setting("maintenance_enabled", bool(enabled))
    if message:
        await set_setting("maintenance_message", message)
