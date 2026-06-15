import random
from pyrogram import Client, filters
from pyrogram.enums import ParseMode
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import Config
from database.users import add_user, total_users

PLAYZONE_LINK = "https://t.me/CLG_fun_zone"
SUPPORT_LINK = "https://t.me/Legacynewzz"

START_MOODS = [
    "🏏 𝗪𝗲𝗹𝗰𝗼𝗺𝗲, 𝗖𝗮𝗽𝘁𝗮𝗶𝗻!",
    "✨ 𝗥𝗲𝗮𝗱𝘆 𝘁𝗼 𝗯𝘂𝗶𝗹𝗱 𝘆𝗼𝘂𝗿 𝗰𝗿𝗶𝗰𝗸𝗲𝘁 𝗹𝗲𝗴𝗮𝗰𝘆?",
    "🔥 𝗧𝗵𝗲 𝗽𝗶𝘁𝗰𝗵 𝗶𝘀 𝘀𝗲𝘁. 𝗟𝗲𝘁’𝘀 𝗽𝗹𝗮𝘆!",
]

# ========== DM START ==========
@Client.on_message(filters.command("start") & filters.private)
async def start_cmd(client: Client, message):
    user = message.from_user
    first_name = user.first_name or "Captain"

    is_new = await add_user(user.id, first_name)

    args = message.command[1] if len(message.command) > 1 else ""
    if args == "duel":
        from plugins.game.duel import get_duel_matchmaking_card
        text, buttons = get_duel_matchmaking_card()
        await message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=buttons)
        return

    mood = random.choice(START_MOODS)

    caption = (
        f"{mood}\n"
        "────┈┄┄╌╌╌╌┄┄┈────\n\n"
        f"👤 <b>{first_name}</b>, welcome to <b>Cricket Legacy</b> ✨\n\n"
        "🏏 <b>Cricket Legacy v2</b>\n\n"
        "🎮 Play epic team & solo matches\n"
        "⚔️ Challenge rivals in 1v1 Duel\n"
        "📊 Track stats & achievements\n"
        "🎙 Live match vibes & action\n\n"
        "🐞 Found a bug?\n"
        "Report it in <b>PlayZone</b>\n\n"
        "👇 Use the buttons below"
    )

    buttons = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("ʟᴇɢᴀᴄʏ ᴘʟᴀʏᴢᴏɴᴇ 🏏", url=PLAYZONE_LINK),
            InlineKeyboardButton("🆘 ꜱᴜᴘᴘᴏʀᴛ", url=SUPPORT_LINK),
        ],
        [
            InlineKeyboardButton("➕ ᴀᴅᴅ ᴛᴏ ɢʀᴏᴜᴘ", url=f"https://t.me/{Config.BOT_USERNAME.replace('@','')}?startgroup=true")
        ],
    ])

    try:
        await message.reply_photo(
            photo=Config.START_IMAGE,
            caption=caption,
            parse_mode=ParseMode.HTML,
            reply_markup=buttons
        )
    except Exception:
        await message.reply_text(caption, parse_mode=ParseMode.HTML, reply_markup=buttons)

    if is_new:
        try:
            count = await total_users()
            log_text = (
                "✨ <b>NEW PLAYER JOINED</b>\n\n"
                f"👤 {first_name}\n"
                f"🆔 <code>{user.id}</code>\n"
                f"📊 Total Users: {count}"
            )
            await client.send_message(Config.LOG_CHANNEL, log_text, parse_mode=ParseMode.HTML)
        except Exception:
            pass


# ========== GROUP START (VOTING SYSTEM) ==========
from pyrogram.enums import ChatMemberStatus
from pyrogram.errors import MessageNotModified
from pyrogram.types import InputMediaPhoto
from Assets.files import START_IMAGE_GROUP
from database.games import is_game_active

VOTE_IMAGE = "https://graph.org/file/82fa7ec61ef263e7fc5ea-93eb782dc413885a2c.jpg"
VOTES_REQUIRED = 3
VOTE_TIMEOUT = 120
VOTE_STATE: dict = {}

PICKER_CAPTION = (
    "🎮 <b>SELECT MODE</b>\n"
    "──┈┄┄╌╌╌╌┄┄┈──\n"
    "Choose how you want to play 👇\n\n"
    "⚔️ <i>1v1 Duel runs in the bot DM — tap to queue.</i>"
)


def _mode_buttons() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("🏏 Team", callback_data="mode_team"),
                InlineKeyboardButton("👤 Solo", callback_data="mode_solo"),
            ],
            [
                InlineKeyboardButton("⚔️ 1v1 Duel", callback_data="mode_duel"),
            ],
            [InlineKeyboardButton("✖ Cancel", callback_data="mode_cancel")],
        ]
    )


async def _bot_can_send_media(client: Client, chat_id: int) -> bool:
    try:
        me = await client.get_me()
        member = await client.get_chat_member(chat_id, me.id)
        if member.status.name == "ADMINISTRATOR":
            return getattr(member.privileges, "can_send_media_messages", True) is not False
        return True
    except Exception:
        return True


async def _is_group_admin(client: Client, chat_id: int, user_id: int) -> bool:
    try:
        member = await client.get_chat_member(chat_id, user_id)
        return member.status in (ChatMemberStatus.OWNER, ChatMemberStatus.ADMINISTRATOR)
    except Exception:
        return False


def _vote_caption(initiator_name: str, count: int) -> str:
    bars = "🟢" * count + "⬜" * (VOTES_REQUIRED - count)
    return (
        f"🗳️ <b>𝗩𝗢𝗧𝗘 𝗧𝗢 𝗦𝗧𝗔𝗥𝗧</b>\n"
        f"──┈┄┄╌╌╌╌┄┄┈──\n\n"
        f"👤 <b>{initiator_name}</b> wants to start a match!\n\n"
        f"🏏 {bars}\n"
        f"<b>{count} / {VOTES_REQUIRED}</b> votes collected\n\n"
        f"⏳ <i>Voting closes in 2 minutes.</i>\n"
        f"Tap below to vote! 👇"
    )


def _vote_buttons(chat_id: int, count: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(
            f"✅ Vote to Start  ({count}/{VOTES_REQUIRED})",
            callback_data=f"vote_start:{chat_id}",
        )],
        [InlineKeyboardButton("✖ Cancel", callback_data=f"vote_cancel:{chat_id}")],
    ])


async def _send_mode_picker(client: Client, message) -> None:
    chat_id = message.chat.id

    if await is_game_active(chat_id):
        await message.reply_text(
            "⚠️ <b>Game already running</b>\nFinish the current match first 🏏",
            parse_mode=ParseMode.HTML,
        )
        return

    if await _bot_can_send_media(client, chat_id):
        try:
            await message.reply_photo(
                photo=START_IMAGE_GROUP,
                caption=PICKER_CAPTION,
                parse_mode=ParseMode.HTML,
                reply_markup=_mode_buttons(),
            )
            return
        except Exception:
            pass

    await message.reply_text(
        PICKER_CAPTION,
        parse_mode=ParseMode.HTML,
        reply_markup=_mode_buttons(),
    )


async def _expire_vote(client: Client, chat_id: int) -> None:
    await asyncio.sleep(VOTE_TIMEOUT)
    state = VOTE_STATE.pop(chat_id, None)
    if not state:
        return
    try:
        await state["message"].delete()
    except Exception:
        pass
    try:
        await client.send_message(
            chat_id,
            "⏰ <b>Voting expired.</b>\nNot enough votes to start the match.",
            parse_mode=ParseMode.HTML,
        )
    except Exception:
        pass


async def _start_vote(client: Client, message) -> None:
    chat_id = message.chat.id
    user = message.from_user
    initiator_name = user.first_name or "Captain"

    if chat_id in VOTE_STATE:
        await message.reply_text(
            "🗳️ <b>A vote is already in progress!</b>\nTap the Vote button above.",
            parse_mode=ParseMode.HTML,
        )
        return

    if await is_game_active(chat_id):
        await message.reply_text(
            "⚠️ <b>Game already running</b>\nFinish the current match first 🏏",
            parse_mode=ParseMode.HTML,
        )
        return

    caption = _vote_caption(initiator_name, 0)
    buttons = _vote_buttons(chat_id, 0)

    try:
        vote_msg = await message.reply_photo(
            photo=VOTE_IMAGE,
            caption=caption,
            parse_mode=ParseMode.HTML,
            reply_markup=buttons,
        )
    except Exception:
        vote_msg = await message.reply_text(
            caption,
            parse_mode=ParseMode.HTML,
            reply_markup=buttons,
        )

    task = asyncio.create_task(_expire_vote(client, chat_id))

    VOTE_STATE[chat_id] = {
        "initiator_id": user.id,
        "initiator_name": initiator_name,
        "voters": set(),
        "message": vote_msg,
        "task": task,
        "client": client,
    }


@Client.on_message(filters.command("start") & filters.group)
async def start_in_group(client: Client, message):
    if await _is_group_admin(client, message.chat.id, message.from_user.id):
        await _send_mode_picker(client, message)
    else:
        await _start_vote(client, message)


@Client.on_callback_query(filters.regex(r"^vote_start:(-?\d+)$"))
async def handle_vote(client, query):
    chat_id = int(query.matches[0].group(1))
    user_id = query.from_user.id

    state = VOTE_STATE.get(chat_id)
    if not state:
        return await query.answer("⏰ This vote has already ended.", show_alert=True)

    if user_id in state["voters"]:
        return await query.answer("✅ You already voted!", show_alert=True)

    state["voters"].add(user_id)
    count = len(state["voters"])

    await query.answer(f"✅ Vote counted! ({count}/{VOTES_REQUIRED})")

    if count >= VOTES_REQUIRED:
        state["task"].cancel()
        VOTE_STATE.pop(chat_id, None)

        try:
            await query.message.delete()
        except Exception:
            pass

        try:
            await client.send_photo(
                chat_id=chat_id,
                photo=START_IMAGE_GROUP,
                caption=PICKER_CAPTION,
                parse_mode=ParseMode.HTML,
                reply_markup=_mode_buttons(),
            )
        except Exception:
            await client.send_message(
                chat_id=chat_id,
                text=PICKER_CAPTION,
                parse_mode=ParseMode.HTML,
                reply_markup=_mode_buttons(),
            )
        return

    caption = _vote_caption(state["initiator_name"], count)
    buttons = _vote_buttons(chat_id, count)
    try:
        await query.message.edit_caption(
            caption=caption,
            parse_mode=ParseMode.HTML,
            reply_markup=buttons,
        )
    except Exception:
        try:
            await query.message.edit_text(
                caption,
                parse_mode=ParseMode.HTML,
                reply_markup=buttons,
            )
        except Exception:
            pass


@Client.on_callback_query(filters.regex(r"^vote_cancel:(-?\d+)$"))
async def handle_vote_cancel(client, query):
    chat_id = int(query.matches[0].group(1))
    state = VOTE_STATE.get(chat_id)

    user_id = query.from_user.id
    is_initiator = state and state["initiator_id"] == user_id
    is_admin = await _is_group_admin(client, chat_id, user_id)

    if not (is_initiator or is_admin):
        return await query.answer("Only the starter or an admin can cancel.", show_alert=True)

    if state:
        state["task"].cancel()
        VOTE_STATE.pop(chat_id, None)

    try:
        await query.message.delete()
    except Exception:
        try:
            await query.message.edit_text("✖ Vote cancelled.")
        except Exception:
            pass
    await query.answer("Vote cancelled.")


@Client.on_callback_query(filters.regex("^mode_cancel$"))
async def cancel_start(client, query):
    try:
        await query.message.delete()
    except Exception:
        try:
            await query.message.edit_text("✖ Cancelled.")
        except Exception:
            pass
    await query.answer("Cancelled")


@Client.on_callback_query(filters.regex("^mode_back$"))
async def back_to_start(client, query):
    await query.answer()
    try:
        await query.message.edit_media(
            media=InputMediaPhoto(
                media=START_IMAGE_GROUP,
                caption=PICKER_CAPTION,
                parse_mode=ParseMode.HTML,
            ),
            reply_markup=_mode_buttons(),
        )
    except MessageNotModified:
        pass
    except Exception:
        try:
            await query.message.edit_text(
                PICKER_CAPTION,
                parse_mode=ParseMode.HTML,
                reply_markup=_mode_buttons(),
            )
        except Exception:
            pass


@Client.on_message(filters.private & filters.text & ~filters.regex(r"^/"), group=1)
async def auto_register_user(client: Client, message):
    user = message.from_user
    if not user:
        return
    try:
        await add_user(user.id, user.first_name)
    except Exception:
        pass
