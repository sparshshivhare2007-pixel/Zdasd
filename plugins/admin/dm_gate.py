"""
DM Gate — restrict which commands work in private chats.

  Owner DM  : only OWNER_DM_COMMANDS pass through; everything else is blocked silently.
  Other DMs : only /start passes through; everything else gets a redirect reply.
"""

from pyrogram import Client, StopPropagation, filters
from pyrogram.enums import ParseMode
from config import Config

OWNER_FILTER = filters.user(list(Config.OWNER_IDS))

OWNER_DM_COMMANDS = {
    # maintenance / admin
    "maintenance",
    # broadcast
    "broad",
    # group management
    "leave", "active",
    # restrictions
    "restrict", "unrestrict", "restricted",
    # db / server tools
    "transfer", "dbtrans", "owner", "uptime",
    "serverinfo", "dbstats", "dbcollections", "dbbackup",
    "logs", "restart",
    # events
    "start_event", "end_event", "event_players",
    # achievement tools
    "gene", "delach",
}

_GROUP_REDIRECT = (
    "🏏 <b>This command only works in a group.</b>\n\n"
    "Add me to a group and use it there!"
)


@Client.on_message(filters.private & filters.command([]) & OWNER_FILTER, group=-9)
async def owner_dm_gate(client, message):
    cmd = (message.command[0] if message.command else "").lower()
    if cmd not in OWNER_DM_COMMANDS:
        raise StopPropagation


@Client.on_message(filters.private & filters.command([]) & ~OWNER_FILTER, group=-9)
async def user_dm_gate(client, message):
    cmd = (message.command[0] if message.command else "").lower()
    if cmd == "start":
        return
    try:
        await message.reply_text(_GROUP_REDIRECT, parse_mode=ParseMode.HTML)
    except Exception:
        pass
    raise StopPropagation
