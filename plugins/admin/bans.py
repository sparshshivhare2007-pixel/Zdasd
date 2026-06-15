from pyrogram import Client, filters
from pyrogram.enums import ParseMode
import html
from database.restrictions import restrict_user, unrestrict_user, get_all_restricted_users
from config import Config 
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

USERS_PER_PAGE = 10


@Client.on_message(filters.command("restrict") & filters.user(list(Config.OWNER_IDS)))
async def restrict_cmd(client, message):
    args = message.command
    target_user = None
    reason = ""

    if message.reply_to_message:
        target_user = message.reply_to_message.from_user
        if len(args) > 1:
            reason = message.text.split(maxsplit=1)[1]
        else:
            return await message.reply_text("⚠️ <b>Format:</b> Reply to a user and type <code>/restrict [reason]</code>", parse_mode=ParseMode.HTML)
            
    else:
        if len(args) < 3:
            return await message.reply_text(
                "⚠️ <b>Format:</b> <code>/restrict [User_ID or @Username] [reason]</code>\n"
                "Or simply reply to a user's message with <code>/restrict [reason]</code>",
                parse_mode=ParseMode.HTML
            )
        
        user_identifier = args[1]
        reason = message.text.split(maxsplit=2)[2] 
        
        wait_msg = await message.reply_text("🔍 Fetching user details...")
        try:
            if user_identifier.isdigit() or (user_identifier.startswith("-") and user_identifier[1:].isdigit()):
                user_identifier = int(user_identifier)
                
            target_user = await client.get_users(user_identifier)
            await wait_msg.delete()
        except Exception as e:
            return await wait_msg.edit_text(f"❌ <b>Error:</b> User not found. Make sure they have started the bot.\n<code>{e}</code>", parse_mode=ParseMode.HTML)

    if not target_user:
        return await message.reply_text("❌ Could not determine the user.")

    await restrict_user(target_user.id, reason, message.from_user.id)
    
    safe_name = html.escape(target_user.first_name or "Player")
    safe_reason = html.escape(reason)
    
    await message.reply_text(
        f"⛔ <b>{safe_name}</b> (<code>{target_user.id}</code>) has been restricted from playing.\n"
        f"📌 <b>Reason:</b> {safe_reason}",
        parse_mode=ParseMode.HTML
    )


@Client.on_message(filters.command("unrestrict") & filters.user(list(Config.OWNER_IDS)))
async def unrestrict_cmd(client, message):
    args = message.command
    target_user = None

    if message.reply_to_message:
        target_user = message.reply_to_message.from_user
        
    else:
        if len(args) < 2:
            return await message.reply_text(
                "⚠️ <b>Format:</b> <code>/unrestrict [User_ID or @Username]</code>\n"
                "Or simply reply to a user's message with <code>/unrestrict</code>",
                parse_mode=ParseMode.HTML
            )
        
        user_identifier = args[1]
        
        wait_msg = await message.reply_text("🔍 Fetching user details...")
        try:
            if user_identifier.isdigit() or (user_identifier.startswith("-") and user_identifier[1:].isdigit()):
                user_identifier = int(user_identifier)
                
            target_user = await client.get_users(user_identifier)
            await wait_msg.delete()
        except Exception as e:
            return await wait_msg.edit_text(f"❌ <b>Error:</b> User not found.\n<code>{e}</code>", parse_mode=ParseMode.HTML)

    if not target_user:
        return await message.reply_text("❌ Could not determine the user.")

    await unrestrict_user(target_user.id)
    
    safe_name = html.escape(target_user.first_name or "Player")
    
    await message.reply_text(
        f"✅ <b>{safe_name}</b> (<code>{target_user.id}</code>) is now free to play and host matches again!",
        parse_mode=ParseMode.HTML
    )

@Client.on_message(filters.command("restricted") & filters.user(list(Config.OWNER_IDS)))
async def restricted_users_cmd(client, message):

    users = await get_all_restricted_users()

    if not users:
        return await message.reply_text(
            "✅ <b>No restricted users found.</b>",
            parse_mode=ParseMode.HTML
        )

    await send_restricted_page(client, message, users, 0)


async def send_restricted_page(client, message, users, page):

    start = page * USERS_PER_PAGE
    end = start + USERS_PER_PAGE
    chunk = users[start:end]

    text = "<b>⛔ Restricted Users</b>\n\n"

    for i, user in enumerate(chunk, start=start + 1):

        user_id = user["user_id"]
        reason = html.escape(user["reason"] or "No reason")

        try:
            tg_user = await client.get_users(user_id)
            name = html.escape(tg_user.first_name or "Unknown")
        except Exception:
            name = "Unknown User"

        text += f"<b>{i}.</b> {name} (<code>{user_id}</code>)\n"
        text += f"📌 <b>Reason:</b> {reason}\n\n"

    buttons = []

    if page > 0:
        buttons.append(
            InlineKeyboardButton("⬅️ Prev", callback_data=f"restricted_{page-1}")
        )

    if end < len(users):
        buttons.append(
            InlineKeyboardButton("Next ➡️", callback_data=f"restricted_{page+1}")
        )

    keyboard = InlineKeyboardMarkup([buttons]) if buttons else None

    await message.reply_text(
        text,
        parse_mode=ParseMode.HTML,
        reply_markup=keyboard
    )


@Client.on_callback_query(filters.regex(r"^restricted_(\d+)"))
async def restricted_page_callback(client, query):

    page = int(query.matches[0].group(1))
    users = await get_all_restricted_users()

    start = page * USERS_PER_PAGE
    end = start + USERS_PER_PAGE
    chunk = users[start:end]

    text = "<b>⛔ Restricted Users</b>\n\n"

    for i, user in enumerate(chunk, start=start + 1):

        user_id = user["user_id"]
        reason = html.escape(user["reason"] or "No reason")

        try:
            tg_user = await client.get_users(user_id)
            name = html.escape(tg_user.first_name or "Unknown")
        except Exception:
            name = "Unknown User"

        text += f"<b>{i}.</b> {name} (<code>{user_id}</code>)\n"
        text += f"📌 <b>Reason:</b> {reason}\n\n"

    buttons = []

    if page > 0:
        buttons.append(
            InlineKeyboardButton("⬅️ Prev", callback_data=f"restricted_{page-1}")
        )

    if end < len(users):
        buttons.append(
            InlineKeyboardButton("Next ➡️", callback_data=f"restricted_{page+1}")
        )

    keyboard = InlineKeyboardMarkup([buttons]) if buttons else None

    await query.message.edit_text(
        text,
        parse_mode=ParseMode.HTML,
        reply_markup=keyboard
    )

    await query.answer()
