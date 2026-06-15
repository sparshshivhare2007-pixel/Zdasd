from functools import wraps
from pyrogram.enums import ChatMemberStatus, ChatType, ParseMode
from pyrogram.types import Message, CallbackQuery
from config import Config
from database.games import get_active_game
from plugins.game.team import ACTIVE_MATCHES
from database.restrictions import get_restriction_reason

def admin_only(func):
    @wraps(func)
    async def wrapper(client, update, *args, **kwargs):
        if isinstance(update, CallbackQuery):
            chat = update.message.chat if update.message else None
            user = update.from_user
            reply = update.message.reply_text if update.message else None
            answer = update.answer
        elif isinstance(update, Message):
            chat = update.chat
            user = update.from_user
            reply = update.reply_text
            answer = None
        else:
            return

        if not chat or chat.type not in (ChatType.GROUP, ChatType.SUPERGROUP):
            return

        if isinstance(update, CallbackQuery) and update.message.sender_chat:
            return await answer("Anonymous admins cannot use this.", show_alert=True)

        if isinstance(update, Message) and update.sender_chat:
            return await reply("**𝗔𝗖𝗖𝗘𝗦𝗦 𝗗𝗘𝗡𝗜𝗘𝗗**\n`Anonymous admins cannot use this command.`")

        if not user:
            return

        if user.id in Config.OWNER_IDS:
            return await func(client, update, *args, **kwargs)

        try:
            member = await client.get_chat_member(chat.id, user.id)
        except Exception:
            if answer: return await answer("Could not verify permissions.", show_alert=True)
            elif reply: return await reply("**𝗘𝗥𝗥𝗢𝗥**\n`Could not verify permissions.`")
            return

        if member.status in (ChatMemberStatus.OWNER, ChatMemberStatus.ADMINISTRATOR):
            return await func(client, update, *args, **kwargs)

        if answer: return await answer("Admins only.", show_alert=True)
        elif reply: return await reply("**𝗔𝗖𝗖𝗘𝗦𝗦 𝗗𝗘𝗡𝗜𝗘𝗗**\n`Admins only.`")

    return wrapper

def host_only(func):
    @wraps(func)
    async def wrapper(client, message, *args, **kwargs):
        chat_id = message.chat.id
        user_id = message.from_user.id

        match = ACTIVE_MATCHES.get(chat_id)
        if match:
            host_id = match.get("host_id")
        else:
            game = await get_active_game(chat_id)
            if not game:
                return await message.reply_text("😴 No match running right now.\nStart one first.")
            host_id = game.get("host_id")

        if user_id != host_id:
            return await message.reply_text("👑 Host privilege only.\nSit tight or convince the host 😌")

        return await func(client, message, *args, **kwargs)

    return wrapper

def not_restricted(func):
    @wraps(func)
    async def wrapper(client, message, *args, **kwargs):
        user = message.from_user
        if not user:
            return await func(client, message, *args, **kwargs)

        reason = await get_restriction_reason(user.id)
        if reason:
            text = (
                f"🚫 **𝗔𝗖𝗖𝗘𝗦𝗦 𝗗𝗘𝗡𝗜𝗘𝗗**\n"
                f"──┈┄┄╌╌╌╌┄┄┈──\n"
                f"You have been restricted from using the Cricket bot.\n\n"
                f"📌 **Reason:** `{reason}`\n\n"
                f"Only the Owner or Mods can remove this restriction."
            )
            
            if hasattr(message, "data"):
                return await message.answer(f"🚫 Restricted: {reason}", show_alert=True)
            else:
                return await message.reply_text(text, parse_mode=ParseMode.MARKDOWN)

        return await func(client, message, *args, **kwargs)
    return wrapper
    
