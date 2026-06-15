"""Global maintenance mode — pause game commands with a friendly message.

Owner-only commands:
    /maintenance              → show status
    /maintenance on [reason]  → enable
    /maintenance off          → disable
"""

import html

from pyrogram import Client, StopPropagation, filters
from pyrogram.enums import ParseMode

from config import Config
from database.settings import (
    get_maintenance_message,
    is_maintenance,
    load_settings,
    set_maintenance,
)


OWNER_FILTER = filters.user(list(Config.OWNER_IDS))

# Game commands that should be blocked while maintenance is on.
# Owner-only / panel commands are intentionally NOT in this list.
GAME_COMMANDS = [
    # generic / start
    "duel",
    # solo
    "joingame", "leavegame", "extend", "forcestart",
    # team
    "create_teams", "rejointeams", "join_teamA", "join_teamB",
    "members", "teams", "add", "remove", "shiftteam",
    "changehost", "changecap", "choose_cap", "set_overs",
    "batting", "bowling", "score", "graph",
    "restore", "change_side", "changeside", "endgame",
    # events
    "register", "deregister", "list_events", "events",
]


async def _send_maintenance_notice(client: Client, message) -> None:
    text = await get_maintenance_message()
    try:
        await message.reply_text(text, parse_mode=ParseMode.HTML)
    except Exception:
        try:
            await message.reply_text(text)
        except Exception:
            pass


# ─── intercept handler (runs before everything else) ─────────────────────────

@Client.on_message(
    filters.command(GAME_COMMANDS) & filters.group & ~OWNER_FILTER,
    group=-10,
)
async def maintenance_gate(client: Client, message):
    if await is_maintenance():
        await _send_maintenance_notice(client, message)
        raise StopPropagation


# Same gate for `/start` — but only in groups (DM /start always works so new
# users can still register and view the welcome screen).
@Client.on_message(
    filters.command("start") & filters.group & ~OWNER_FILTER,
    group=-10,
)
async def maintenance_gate_start(client: Client, message):
    if await is_maintenance():
        await _send_maintenance_notice(client, message)
        raise StopPropagation


# ─── /maintenance ────────────────────────────────────────────────────────────

@Client.on_message(filters.command("maintenance") & OWNER_FILTER)
async def maintenance_cmd(client: Client, message):
    await load_settings(force=True)

    args = message.command
    if len(args) < 2:
        active = await is_maintenance()
        msg = await get_maintenance_message()
        return await message.reply_text(
            "🛠 <b>MAINTENANCE STATUS</b>\n"
            "──┈┄┄╌╌╌╌┄┄┈──\n"
            f"State: <b>{'🔴 ON' if active else '🟢 OFF'}</b>\n\n"
            f"<b>Message preview:</b>\n{msg}\n\n"
            "<b>Usage:</b>\n"
            "<code>/maintenance on [reason]</code>\n"
            "<code>/maintenance off</code>",
            parse_mode=ParseMode.HTML,
        )

    action = args[1].lower()

    if action in ("on", "enable", "start", "true"):
        custom = None
        if len(args) >= 3:
            reason = " ".join(args[2:]).strip()
            custom = (
                "🛠 <b>Bot is under maintenance</b>\n"
                "──┈┄┄╌╌╌╌┄┄┈──\n"
                f"{html.escape(reason)}\n\n"
                "Game commands are paused. Hang tight! 🏏"
            )
        await set_maintenance(True, message=custom)
        msg = await get_maintenance_message()
        return await message.reply_text(
            "🔴 <b>Maintenance ENABLED.</b>\n\n"
            "Players will see:\n\n" + msg,
            parse_mode=ParseMode.HTML,
        )

    if action in ("off", "disable", "stop", "false"):
        await set_maintenance(False)
        return await message.reply_text(
            "🟢 <b>Maintenance DISABLED.</b>\nGame commands are live again 🏏",
            parse_mode=ParseMode.HTML,
        )

    if action == "status":
        active = await is_maintenance()
        return await message.reply_text(
            f"🛠 Maintenance is currently <b>{'🔴 ON' if active else '🟢 OFF'}</b>.",
            parse_mode=ParseMode.HTML,
        )

    await message.reply_text(
        "❌ Unknown action.\nUse <code>on</code>, <code>off</code>, or <code>status</code>.",
        parse_mode=ParseMode.HTML,
    )
