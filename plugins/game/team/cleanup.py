import asyncio
import time
import html
from pyrogram.enums import ParseMode
from plugins.game.team import ACTIVE_MATCHES
from database.connection import db

async def auto_clean_matches(client):
    """Background task to kill inactive matches ONLY when game is LIVE"""
    print("🧹 Match GC with EVERY MINUTE Warnings Started (Only for LIVE matches)...")
    
    while True:
        await asyncio.sleep(20)
        
        now = time.time()
        stale_chats = []

        for chat_id, match in list(ACTIVE_MATCHES.items()):
            
            if match.get("mode") == "Solo":
                continue 
            
            current_phase = match.get("phase", "UNKNOWN")

            if current_phase != "LIVE":
                match["last_active"] = now 
                continue

            if "last_active" not in match:
                match["last_active"] = now
            
            inactive_time = now - match["last_active"]
            inactive_minutes = int(inactive_time // 60)

            if "warnings_sent" not in match:
                match["warnings_sent"] = []

            if inactive_time < 60:
                match["warnings_sent"] = []

            if inactive_minutes >= 10:
                stale_chats.append(chat_id)
            
            elif inactive_minutes >= 1 and inactive_minutes not in match["warnings_sent"]:
                match["warnings_sent"].append(inactive_minutes)
                mins_left = 10 - inactive_minutes
                
                host_id = match.get("host_id")
                safe_name = html.escape(match.get("host_name", "Host"))
                host_mention = f"<a href='tg://user?id={host_id}'>{safe_name}</a>"
                
                try:
                    await client.send_message(
                        chat_id,
                        f"⚠️ <b>AFK WARNING ({inactive_minutes}/10)</b>\n\n"
                        f"Host {host_mention}, the match is paused!\n"
                        f"⏳ Auto-end in: <b>{mins_left} minutes</b>.",
                        parse_mode=ParseMode.HTML
                    )
                except Exception as e:
                    pass

        for chat_id in stale_chats:
            match = ACTIVE_MATCHES.pop(chat_id, None)
            if not match: 
                continue

            game_id = match.get("game_id")
            
            try:
                await client.send_message(
                    chat_id,
                    "☠️ <b>MATCH ABORTED!</b>\n\n"
                    "Match has been automatically ended due to inactivity.\n"
                    "Players are now free to play elsewhere.",
                    parse_mode=ParseMode.HTML
                )
            except Exception:
                pass

            if game_id:
                try:
                    await db.db["games"].update_one({"game_id": game_id}, {"$set": {"status": "ended"}})
                except Exception as e:
                    print("❌ GC DB Cleanup Error:", e)
                    
