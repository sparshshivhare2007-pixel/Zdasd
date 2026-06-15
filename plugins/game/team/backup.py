import json
import os
import uuid
from pyrogram import Client, filters
from pyrogram.enums import ParseMode
from plugins.game.team import ACTIVE_MATCHES
from utils.permissions import host_only
from utils.guards import is_group_admin
from config import Config

def fix_json_keys(data):
    if isinstance(data, dict):
        new_dict = {}
        for k, v in data.items():
            new_key = int(k) if isinstance(k, str) and k.isdigit() else k
            new_dict[new_key] = fix_json_keys(v)
        return new_dict
    elif isinstance(data, list):
        return [fix_json_keys(i) for i in data]
    else:
        return data

@Client.on_message(filters.command("restore") & filters.group)
async def restore_game_cmd(client, message):
    chat_id = message.chat.id
    user_id = message.from_user.id

    if user_id not in Config.OWNER_IDS and not await is_group_admin(client, chat_id, user_id):
        return await message.reply_text("🚫 **Access Denied:** only **Group Admins** can restore the game!")

    if not message.reply_to_message or not message.reply_to_message.document:
        return await message.reply_text("⚠️ Please reply to a **.json** Save File first!")

    doc = message.reply_to_message.document
    if not doc.file_name.endswith(".json"):
        return await message.reply_text("⚠️ Invalid file! Only `.json` match files are supported.")

    wait_msg = await message.reply_text("🔄 **Downloading and restoring match data...**")

    try:
        file_path = await message.reply_to_message.download()
        with open(file_path, "r") as f:
            raw_data = json.load(f)
        os.remove(file_path)

        backup_data = fix_json_keys(raw_data)

        backup_data["client"] = client
        backup_data["timeouts"] = {
            "bowler": {"fails": 0, "task": None},
            "batter": {"fails": 0, "task": None},
        }
        backup_data["announced_achievements"] = {
            "batting": {}, "bowling": {}, "partnerships": set()
        }

        ACTIVE_MATCHES[chat_id] = backup_data

        await wait_msg.edit_text(
            f"✅ **𝗠𝗔𝗧𝗖𝗛 𝗥𝗘𝗦𝗧𝗢𝗥𝗘𝗗 𝗦𝗨𝗖𝗖𝗘𝗦𝗦𝗙𝗨𝗟𝗟𝗬!**\n"
            f"──┈┄┄╌╌╌╌┄┄┈──\n"
            f"Phase: **{backup_data.get('phase', 'LIVE')}**\n"
            f"Total Balls: **{backup_data.get('total_balls', 0)}**\n\n"
            f"▶️ Game is live again! Send the next command."
        )
    except Exception as e:
        await wait_msg.edit_text(f"❌ **Restoration Failed:**\nError: `{e}`")
        
@Client.on_message(filters.command(["change_side", "changeside"]) & filters.group)
@host_only
async def change_side_cmd(client, message):
    chat_id = message.chat.id
    match = ACTIVE_MATCHES.get(chat_id)

    if not match or match.get("phase") != "LIVE":
        return await message.reply_text("⚠️ No live match running right now!")

    if match.get("total_balls", 0) > 0:
        return await message.reply_text("⚠️ **Not Allowed!** You can only change sides BEFORE the first ball of the innings is bowled.")

    striker = match.get("striker")
    non_striker = match.get("non_striker")

    if not striker or not non_striker:
        return await message.reply_text("⚠️ Both opening batters must be on the pitch to change sides!")
        
    match["striker"], match["non_striker"] = non_striker, striker
    
    match["prompt_dispatched"] = False 

    striker_name = match.get("user_cache", {}).get(match["striker"], "Batter 1")
    non_striker_name = match.get("user_cache", {}).get(match["non_striker"], "Batter 2")

    await message.reply_text(
        f"🔄 **𝗦𝗜𝗗𝗘𝗦 𝗖𝗛𝗔𝗡𝗚𝗘𝗗 𝗦𝗨𝗖𝗖𝗘𝗦𝗦𝗙𝗨𝗟𝗟𝗬!** (Host Action)\n"
        f"──┈┄┄╌╌╌╌┄┄┈──\n"
        f"🏏 **On Strike:** <a href='tg://user?id={match['striker']}'>{striker_name}</a>\n"
        f"🏃 **Non-Striker:** <a href='tg://user?id={match['non_striker']}'>{non_striker_name}</a>\n\n"
        f"Ready for the first ball!",
        parse_mode=ParseMode.HTML
    )
    
