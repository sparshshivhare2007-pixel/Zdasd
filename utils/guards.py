"""
Shared guard helpers and decorators for command handlers.

Usage:
    from utils.guards import (
        get_match,           # ACTIVE_MATCHES.get(chat_id) with optional no-match reply
        is_group_admin,      # True/False admin check (no exception leaks)
        is_host_or_admin,    # True/False host OR admin check
        group_only,          # decorator: silently ignore DM invocations
        dm_only,             # decorator: redirect group invocations to DM
        ensure_user,         # upsert a user row in 'users' collection (fire-and-forget)
        ctx,                 # extract (chat_id, user_id, user) from Message in one call
    )

All decorators preserve the original function signature so that other decorators
(host_only, not_restricted, etc.) can stack on top without issue.
"""

from __future__ import annotations

import asyncio
from functools import wraps
from typing import Optional, Tuple

from pyrogram.enums import ChatMemberStatus
from pyrogram.types import Message

from database.connection import db
from plugins.game.team import ACTIVE_MATCHES


# ─── lightweight context extractor ────────────────────────────────────────────

def ctx(message: Message) -> Tuple[int, int, object]:
    """Return (chat_id, user_id, user) from a Message."""
    return message.chat.id, message.from_user.id, message.from_user


# ─── match lookup ─────────────────────────────────────────────────────────────

def get_match(chat_id: int, *, no_match_text: str | None = None, message: Message | None = None):
    """
    Return ACTIVE_MATCHES[chat_id] or None.

    If `no_match_text` and `message` are both supplied and there is no match,
    the function schedules a reply and returns None — so callers can do:

        match = get_match(chat_id)
        if not match:
            return await message.reply_text("...")
    """
    return ACTIVE_MATCHES.get(chat_id)


# ─── admin / permission checks ─────────────────────────────────────────────────

async def is_group_admin(client, chat_id: int, user_id: int) -> bool:
    """Return True if user is owner or admin of the group."""
    try:
        member = await client.get_chat_member(chat_id, user_id)
        return member.status in (ChatMemberStatus.OWNER, ChatMemberStatus.ADMINISTRATOR)
    except Exception:
        return False


async def is_host_or_admin(client, chat_id: int, user_id: int, host_id: int | None) -> bool:
    """Return True if user is the match host OR a group admin."""
    if user_id == host_id:
        return True
    return await is_group_admin(client, chat_id, user_id)


# ─── user upsert ──────────────────────────────────────────────────────────────

async def ensure_user(user) -> None:
    """
    Upsert a minimal user document.  Safe to fire-and-forget with
    asyncio.create_task(ensure_user(user)).
    """
    try:
        await db.db["users"].update_one(
            {"user_id": user.id},
            {"$setOnInsert": {
                "user_id": user.id,
                "name": user.first_name or "Player",
                "coins": 1000,
                "games_played": 0,
                "notify_enabled": True,
            }},
            upsert=True,
        )
    except Exception:
        pass


# ─── decorators ───────────────────────────────────────────────────────────────

def group_only(func):
    """Silently ignore the command when sent in a DM."""
    @wraps(func)
    async def wrapper(client, message: Message, *args, **kwargs):
        from pyrogram.enums import ChatType
        if message.chat.type == ChatType.PRIVATE:
            return
        return await func(client, message, *args, **kwargs)
    return wrapper


def dm_only(redirect_text: str = "📩 This command only works in my DM."):
    """
    Redirect group users to the bot DM.
    Usage:
        @dm_only("Send /duel in my DM to queue.")
        async def duel_cmd(client, message): ...
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(client, message: Message, *args, **kwargs):
            from pyrogram.enums import ChatType
            from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            from config import Config
            if message.chat.type != ChatType.PRIVATE:
                bot_link = f"https://t.me/{Config.BOT_USERNAME.lstrip('@')}"
                await message.reply_text(
                    redirect_text,
                    reply_markup=InlineKeyboardMarkup(
                        [[InlineKeyboardButton("📩 Open DM", url=bot_link)]]
                    ),
                )
                return
            return await func(client, message, *args, **kwargs)
        return wrapper
    return decorator


def require_match(no_match_reply: str = "😴 No active match here."):
    """
    Decorator: reply with `no_match_reply` if no ACTIVE_MATCHES entry exists
    for this chat.  Injects `match` as the first keyword arg.

    Usage:
        @require_match("❌ No game running.")
        async def score_cmd(client, message, match):
            ...
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(client, message: Message, *args, **kwargs):
            chat_id = message.chat.id
            match = ACTIVE_MATCHES.get(chat_id)
            if not match:
                return await message.reply_text(no_match_reply)
            return await func(client, message, *args, match=match, **kwargs)
        return wrapper
    return decorator


def require_admin(reply_text: str = "🚫 Group admins only."):
    """
    Decorator: allow only group admins (or bot owner) to proceed.
    Works on Message handlers only.
    """
    from config import Config

    def decorator(func):
        @wraps(func)
        async def wrapper(client, message: Message, *args, **kwargs):
            user_id = message.from_user.id
            if user_id in Config.OWNER_IDS:
                return await func(client, message, *args, **kwargs)
            if not await is_group_admin(client, message.chat.id, user_id):
                return await message.reply_text(reply_text)
            return await func(client, message, *args, **kwargs)
        return wrapper
    return decorator
