"""
Owner-only premium management commands.

/permit <group_id> [plan]   grant premium to a group
/revoke <group_id>          remove premium from a group
/checkpremium [group_id]    show premium status

Plans: basic (₹29)  standard (₹49)  pro (₹70)
"""

from pyrogram import Client, filters
from pyrogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    Message,
    CallbackQuery,
)
from pyrogram.enums import ParseMode

from config import Config
from database.premium import grant_premium, revoke_premium, get_premium, PLANS


def _owner(uid: int) -> bool:
    return uid in Config.OWNER_IDS


# ─── Commands ─────────────────────────────────────────────────────────────────

@Client.on_message(filters.command("permit") & filters.private)
async def permit_cmd(client: Client, message: Message):
    if not _owner(message.from_user.id):
        return await message.reply_text("⛔ Owner only.")

    args = message.command[1:]
    if not args:
        return await message.reply_text(
            "Usage: <code>/permit &lt;group_id&gt; [plan]</code>\n\n"
            "Plans: <code>basic</code> ₹29  •  <code>standard</code> ₹49  •  <code>pro</code> ₹70",
            parse_mode=ParseMode.HTML,
        )

    try:
        chat_id = int(args[0])
    except ValueError:
        return await message.reply_text("❌ Invalid group ID — must be a number.")

    if len(args) >= 2:
        plan = args[1].lower()
        if plan not in PLANS:
            return await message.reply_text(
                "❌ Unknown plan.\nUse: <code>basic</code>, <code>standard</code>, or <code>pro</code>",
                parse_mode=ParseMode.HTML,
            )
        await _do_grant(message, chat_id, plan, message.from_user.id)
    else:
        buttons = [
            [InlineKeyboardButton(
                f"{data['name']}  —  ₹{data['price']}",
                callback_data=f"pmg_{chat_id}_{key}",
            )]
            for key, data in PLANS.items()
        ]
        buttons.append([InlineKeyboardButton("✖ Cancel", callback_data="pmc")])
        await message.reply_text(
            f"💎 <b>Select plan for group</b> <code>{chat_id}</code>:",
            reply_markup=InlineKeyboardMarkup(buttons),
            parse_mode=ParseMode.HTML,
        )


@Client.on_message(filters.command("revoke") & filters.private)
async def revoke_cmd(client: Client, message: Message):
    if not _owner(message.from_user.id):
        return await message.reply_text("⛔ Owner only.")

    args = message.command[1:]
    if not args:
        return await message.reply_text(
            "Usage: <code>/revoke &lt;group_id&gt;</code>",
            parse_mode=ParseMode.HTML,
        )

    try:
        chat_id = int(args[0])
    except ValueError:
        return await message.reply_text("❌ Invalid group ID.")

    ok = await revoke_premium(chat_id)
    if ok:
        await message.reply_text(
            f"✅ Premium revoked from group <code>{chat_id}</code>.",
            parse_mode=ParseMode.HTML,
        )
    else:
        await message.reply_text(
            f"⚠️ Group <code>{chat_id}</code> had no active premium.",
            parse_mode=ParseMode.HTML,
        )


@Client.on_message(filters.command("checkpremium"))
async def checkpremium_cmd(client: Client, message: Message):
    if not _owner(message.from_user.id):
        return await message.reply_text("⛔ Owner only.")

    args = message.command[1:]
    if args:
        try:
            chat_id = int(args[0])
        except ValueError:
            return await message.reply_text("❌ Invalid group ID.")
    else:
        chat_id = message.chat.id

    p = await get_premium(chat_id)
    if p:
        pd  = PLANS[p["plan"]]
        feats = " • ".join(pd["features"])
        await message.reply_text(
            f"✨ <b>Premium Active</b>\n"
            f"Group: <code>{chat_id}</code>\n"
            f"Plan: <b>{pd['name']}</b>  (₹{pd['price']})\n"
            f"Features: {feats}",
            parse_mode=ParseMode.HTML,
        )
    else:
        await message.reply_text(
            f"❌ No active premium for <code>{chat_id}</code>.",
            parse_mode=ParseMode.HTML,
        )


# ─── Callbacks ────────────────────────────────────────────────────────────────

@Client.on_callback_query(filters.regex(r"^pmg_-?\d+_\w+$"))
async def pmg_cb(client: Client, query: CallbackQuery):
    if not _owner(query.from_user.id):
        return await query.answer("Owner only!", show_alert=True)
    parts   = query.data.split("_")
    chat_id = int(parts[1])
    plan    = parts[2]
    await _do_grant(query.message, chat_id, plan, query.from_user.id, edit=True)
    await query.answer("✅ Premium granted!")


@Client.on_callback_query(filters.regex("^pmc$"))
async def pmc_cb(client: Client, query: CallbackQuery):
    try:
        await query.message.delete()
    except Exception:
        pass
    await query.answer("Cancelled.")


async def _do_grant(msg, chat_id: int, plan: str, granted_by: int, edit: bool = False):
    await grant_premium(chat_id, plan, granted_by)
    pd    = PLANS[plan]
    feats = " • ".join(pd["features"])
    text  = (
        f"✅ <b>Premium Granted!</b>\n"
        f"Group: <code>{chat_id}</code>\n"
        f"Plan: <b>{pd['name']}</b>  (₹{pd['price']})\n"
        f"Unlocks: <b>{feats}</b>"
    )
    if edit:
        try:
            await msg.edit_text(text, parse_mode=ParseMode.HTML)
        except Exception:
            pass
    else:
        await msg.reply_text(text, parse_mode=ParseMode.HTML)
