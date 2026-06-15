import asyncio
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.enums import ParseMode
from plugins.game.team import ACTIVE_MATCHES

HOST_VOTES = {}
VOTE_TIMEOUT = 120 

async def sync_captain_to_db(game_id, team, new_captain_id):
    try:
        from database.connection import db
        await db.db["game_players"].update_many({"game_id": game_id, "team": team}, {"$set": {"is_captain": False}})
        await db.db["game_players"].update_one({"game_id": game_id, "user_id": new_captain_id}, {"$set": {"is_captain": True}})
    except Exception as e:
        print(f"❌ DB Captain Sync Error: {e}")
        
def sync_captain_flags(match, team):
    captain_id = match["teams"][team].get("captain_id")

    for uid, pdata in match["players"].items():
        if pdata.get("team") == team:
            pdata["is_captain"] = (uid == captain_id)

@Client.on_message(filters.command("changehost") & filters.group)
async def change_host_logic(client, message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    match = ACTIVE_MATCHES.get(chat_id)

    if not match:
        return await message.reply_text("❌ No active match in this group.")

    if user_id == match["host_id"]:
        match["prev_phase"] = match.get("phase", "LIVE")
        match["phase"] = "HOST_CHANGE"

        btn = InlineKeyboardMarkup([
            [InlineKeyboardButton("🎯 I am Host", callback_data="claim_host")],
            [InlineKeyboardButton("✖ Cancel", callback_data="cancel_host_change")]
        ])

        msg = await message.reply_text(
            "👑 **HOST RESIGNATION**\n\n"
            "Host has stepped down.\n"
            "Someone claim host within **2 minutes**.",
            reply_markup=btn,
            parse_mode=ParseMode.MARKDOWN
        )

        asyncio.create_task(host_claim_timeout(msg, chat_id))
        return

    all_players = match["teams"]["A"]["players"] + match["teams"]["B"]["players"]
    if user_id not in all_players:
        return await message.reply_text("🚫 Only players can initiate host vote.")

    if chat_id in HOST_VOTES:
        return await message.reply_text("⚠️ A vote is already running.")

    HOST_VOTES[chat_id] = {"A": [], "B": [], "initiator": user_id}

    btn = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Vote Change Host", callback_data="vote_host_change")],
        [InlineKeyboardButton("✖ Cancel Vote", callback_data="cancel_host_vote")]
    ])

    msg = await message.reply_text(
        "🗳️ **HOST CHANGE VOTE**\n\n"
        "Requirement:\n"
        "• Team A: 2 votes\n"
        "• Team B: 2 votes\n\n"
        "`A: 0/2 | B: 0/2`",
        reply_markup=btn,
        parse_mode=ParseMode.MARKDOWN
    )

    HOST_VOTES[chat_id]["task"] = asyncio.create_task(
        vote_timeout(msg, chat_id)
    )

@Client.on_callback_query(filters.regex("^vote_host_change$"))
async def handle_host_vote(client, query):
    chat_id = query.message.chat.id
    user_id = query.from_user.id
    match = ACTIVE_MATCHES.get(chat_id)

    if chat_id not in HOST_VOTES:
        return await query.answer("Vote expired.", show_alert=True)

    team = None
    if user_id in match["teams"]["A"]["players"]:
        team = "A"
    elif user_id in match["teams"]["B"]["players"]:
        team = "B"

    if not team:
        return await query.answer("Not a participant.", show_alert=True)

    if user_id in HOST_VOTES[chat_id][team]:
        return await query.answer("Already voted.", show_alert=True)

    HOST_VOTES[chat_id][team].append(user_id)

    v_a = len(HOST_VOTES[chat_id]["A"])
    v_b = len(HOST_VOTES[chat_id]["B"])

    if v_a >= 2 and v_b >= 2:
        HOST_VOTES[chat_id]["task"].cancel()
        HOST_VOTES.pop(chat_id, None)

        match["prev_phase"] = match.get("phase", "LIVE")
        match["phase"] = "HOST_CHANGE"

        btn = InlineKeyboardMarkup([
            [InlineKeyboardButton("🎯 I am Host", callback_data="claim_host")],
            [InlineKeyboardButton("✖ Cancel", callback_data="cancel_host_change")]
        ])

        await query.message.edit_text(
            "✅ **VOTE PASSED**\n\n"
            "Claim host within **2 minutes**.",
            reply_markup=btn,
            parse_mode=ParseMode.MARKDOWN
        )

        asyncio.create_task(host_claim_timeout(query.message, chat_id))
        return

    await query.message.edit_text(
        f"🗳️ **HOST CHANGE VOTE**\n\n"
        f"A: `{v_a}/2` | B: `{v_b}/2`",
        reply_markup=query.message.reply_markup,
        parse_mode=ParseMode.MARKDOWN
    )
    await query.answer("Vote counted")

@Client.on_callback_query(filters.regex("^claim_host$"))
async def claim_host(client, query):
    chat_id = query.message.chat.id
    user = query.from_user
    match = ACTIVE_MATCHES.get(chat_id)

    if not match or match.get("phase") != "HOST_CHANGE":
        return await query.answer("Invalid or expired action.", show_alert=True)

    match["host_id"] = user.id
    match["host_name"] = user.first_name or "Host"

    match.setdefault("user_cache", {})
    match["user_cache"][user.id] = match["host_name"]

    match["phase"] = match.pop("prev_phase", "LIVE")
    match.pop("prev_host_id", None)

    try:
        from database.connection import db
        await db.db["games"].update_one({"game_id": match["game_id"]}, {"$set": {"host_id": user.id}})
    except Exception as e:
        print("❌ Host DB sync failed:", e)

    await query.message.edit_text(
        (
            "🎊 <b>NEW HOST ASSIGNED</b>\n\n"
            f"<a href='tg://user?id={user.id}'>{match['host_name']}</a> "
            "is now the host.\n\n"
            "<i>Authority transferred instantly.</i>"
        ),
        parse_mode=ParseMode.HTML
    )

    await query.answer("You are now the host ✅")

@Client.on_callback_query(filters.regex("^cancel_host_vote$"))
async def cancel_vote(client, query):
    chat_id = query.message.chat.id
    match = ACTIVE_MATCHES.get(chat_id)

    if not match or query.from_user.id != match["host_id"]:
        return await query.answer("Only host can cancel.", show_alert=True)

    task = HOST_VOTES.get(chat_id, {}).get("task")
    if task:
        task.cancel()

    HOST_VOTES.pop(chat_id, None)

    await query.message.edit_text(
        "❌ **VOTE CANCELLED**\n\n"
        "Host remains unchanged.",
        parse_mode=ParseMode.MARKDOWN
    )

@Client.on_callback_query(filters.regex("^cancel_host_change$"))
async def cancel_claim(client, query):
    chat_id = query.message.chat.id
    match = ACTIVE_MATCHES.get(chat_id)

    if not match or query.from_user.id != match["host_id"]:
        return await query.answer("Only host can cancel.", show_alert=True)

    match["phase"] = match.pop("prev_phase", "LIVE")

    await query.message.edit_text(
        "❌ **HOST CHANGE CANCELLED**\n\n"
        "Host remains unchanged.",
        parse_mode=ParseMode.MARKDOWN
    )

async def vote_timeout(message, chat_id):
    await asyncio.sleep(VOTE_TIMEOUT)

    if chat_id in HOST_VOTES:
        HOST_VOTES.pop(chat_id, None)
        await message.edit_text(
            "⏱️ **VOTE EXPIRED**\n\n"
            "Host remains unchanged.",
            parse_mode=ParseMode.MARKDOWN
        )

async def host_claim_timeout(message, chat_id):
    await asyncio.sleep(VOTE_TIMEOUT)

    match = ACTIVE_MATCHES.get(chat_id)
    if match and match.get("phase") == "HOST_CHANGE":
        match["phase"] = match.pop("prev_phase", "LIVE")
        await message.edit_text(
            "⏱️ **NO HOST CLAIMED**\n\n"
            "Host remains unchanged.",
            parse_mode=ParseMode.MARKDOWN
        )

@Client.on_message(filters.command("changecap") & filters.group)
async def change_captain(client, message):
    chat_id = message.chat.id
    user = message.from_user
    user_id = user.id
    args = message.text.split(maxsplit=2)
    match = ACTIVE_MATCHES.get(chat_id)

    if not match:
        return await message.reply_text("❌ No active match found.")

    teams = match.get("teams", {})
    user_cache = match.setdefault("user_cache", {})

    user_team = None
    for t in ("A", "B"):
        if user_id in teams.get(t, {}).get("players", []):
            user_team = t
            break

    is_host = user_id == match.get("host_id")
    current_cap_id = teams.get(user_team, {}).get("captain_id") or teams.get(user_team, {}).get("captain")
    is_captain = user_team and current_cap_id == user_id

    if not is_host and not user_team:
        return await message.reply_text("🚫 Only Host or match players can use this command.")

    if is_host and len(args) >= 2 and args[1] in ("A", "B"):
        team = args[1]
        team_data = teams.get(team)

        if not team_data:
            return await message.reply_text("❌ Invalid team.")

        target_id = None
        if message.reply_to_message:
            target_id = message.reply_to_message.from_user.id
        elif len(args) == 3:
            if args[2].isdigit():
                target_id = int(args[2])
            elif args[2].startswith("@"):
                try:
                    u = await client.get_users(args[2])
                    target_id = u.id
                    user_cache[u.id] = u.first_name
                except:
                    pass

        if target_id not in team_data.get("players", []):
            return await message.reply_text("❌ Target must be a player of that team.")

        team_data["captain_id"] = target_id
        team_data["captain"] = target_id # Pro Mode Fix
        user_cache[target_id] = user_cache.get(target_id, "Player")

        for uid, pdata in match["players"].items():
            if pdata.get("team") == team:
                pdata["is_captain"] = (uid == target_id)

        match["phase"] = match.get("prev_phase", "LIVE")
        
        await sync_captain_to_db(match["game_id"], team, target_id)

        return await message.reply_text(
            f"🎖 <b>CAPTAIN CHANGED</b>\n\n"
            f"👤 Team {team} Captain:\n"
            f"<a href='tg://user?id={target_id}'>{user_cache[target_id]}</a>\n"
            f"⚡ Changed by Host.",
            parse_mode=ParseMode.HTML
        )

    if is_captain and len(args) == 2:
        team_data = teams[user_team]

        target_id = None
        if message.reply_to_message:
            target_id = message.reply_to_message.from_user.id
        elif args[1].isdigit():
            target_id = int(args[1])
        elif args[1].startswith("@"):
            try:
                u = await client.get_users(args[1])
                target_id = u.id
                user_cache[u.id] = u.first_name
            except:
                pass

        if target_id not in team_data.get("players", []):
            return await message.reply_text("❌ You can only assign captain within your team.")

        team_data["captain_id"] = target_id
        team_data["captain"] = target_id # Pro Mode Fix
        user_cache[target_id] = user_cache.get(target_id, "Player")

        for uid, pdata in match["players"].items():
            if pdata.get("team") == user_team:
                pdata["is_captain"] = (uid == target_id)

        match["phase"] = match.get("prev_phase", "LIVE")
        
        await sync_captain_to_db(match["game_id"], user_team, target_id)

        return await message.reply_text(
            f"🎖 <b>NEW TEAM {user_team} CAPTAIN</b>\n\n"
            f"👤 <a href='tg://user?id={target_id}'>{user_cache[target_id]}</a>\n"
            f"✅ Changed by current Captain.",
            parse_mode=ParseMode.HTML
        )

    if not is_host and not is_captain:
        return await message.reply_text(
            "⚠️ Permission denied.\n"
            "Only Host or current Captain can release captaincy."
        )

    match["prev_phase"] = match.get("phase", "LIVE")
    match["phase"] = f"CAP_CHANGE_{user_team}"
    
    async def auto_cancel():
        await asyncio.sleep(120)
        if match.get("phase") == f"CAP_CHANGE_{user_team}":
            match["phase"] = match.pop("prev_phase", "LIVE")
            await client.send_message(
                chat_id,
                f"⌛ **CAPTAIN CHANGE TIMEOUT**\n\n"
                f"No response from Team {user_team}.\n"
                f"Captaincy remains unchanged.",
            )

    task = match.pop("cap_change_task", None)
    if task:
        task.cancel()

    match["cap_change_task"] = asyncio.create_task(auto_cancel())

    btn = InlineKeyboardMarkup([
        [InlineKeyboardButton(
            f"🎖 I am Team {user_team} Captain",
            callback_data=f"claim_cap_{user_team}"
        )],
        [InlineKeyboardButton(
            "✖ Cancel",
            callback_data=f"cancel_cap_{user_team}"
        )]
    ])

    await message.reply_text(
        f"⚡ <b>CAPTAINCY RELEASED — TEAM {user_team}</b>\n\n"
        f"👤 Released by: {user.first_name}\n"
        f"⏳ Auto-cancels in 2 minutes.",
        reply_markup=btn,
        parse_mode=ParseMode.HTML
    )
    
@Client.on_callback_query(filters.regex(r"^claim_cap_(A|B)$"))
async def claim_captain(client, query):
    team = query.data.split("_")[-1]
    chat_id = query.message.chat.id
    user = query.from_user
    match = ACTIVE_MATCHES.get(chat_id)

    if not match or match.get("phase") != f"CAP_CHANGE_{team}":
        return await query.answer("Captaincy session expired.", show_alert=True)

    if user.id not in match["teams"][team]["players"]:
        return await query.answer("You are not in this team.", show_alert=True)

    match["teams"][team]["captain_id"] = user.id
    match["teams"][team]["captain"] = user.id # Pro Mode Fix
    match["user_cache"][user.id] = user.first_name

    for uid, pdata in match["players"].items():
        if pdata.get("team") == team:
            pdata["is_captain"] = (uid == user.id)

    task = match.pop("cap_change_task", None)
    if task:
        task.cancel()

    match["phase"] = match.pop("prev_phase", "LIVE")
    
    await sync_captain_to_db(match["game_id"], team, user.id)

    await query.message.edit_text(
        f"🎖 **NEW TEAM {team} CAPTAIN**\n\n"
        f"👤 {user.mention}\n"
        f"🚀 Match continues!",
        parse_mode=ParseMode.HTML
    )
    
@Client.on_callback_query(filters.regex(r"^cancel_cap_(A|B)$"))
async def cancel_cap_change(client, query):
    team = query.data.split("_")[-1]
    chat_id = query.message.chat.id
    user = query.from_user
    match = ACTIVE_MATCHES.get(chat_id)

    current_cap = match["teams"][team].get("captain_id") if match else None

    if not match or user.id not in (match["host_id"], current_cap):
        return await query.answer("Not allowed.", show_alert=True)

    task = match.pop("cap_change_task", None)
    if task:
        task.cancel()

    match["phase"] = match.pop("prev_phase", "LIVE")

    await query.message.edit_text(
        f"❌ **CAPTAIN CHANGE CANCELLED**\n\n"
        f"Team {team} captain remains unchanged."
    )
    
