import asyncio
import time
from plugins.game.team import ACTIVE_MATCHES

IDLE_TIMEOUT = 600  # 10 minutes idle = auto-clean


async def auto_clean_solo(bot):
    while True:
        try:
            await asyncio.sleep(60)
            now = time.time()
            to_remove = []

            for chat_id, match in list(ACTIVE_MATCHES.items()):
                if match.get("mode") != "Solo":
                    continue

                last = match.get("last_active", now)
                if (now - last) > IDLE_TIMEOUT and match.get("phase") == "LIVE":
                    to_remove.append((chat_id, match))

            for chat_id, match in to_remove:
                try:
                    timeouts = match.get("timeouts", {})
                    for role in ("batter", "bowler"):
                        task = timeouts.get(role, {}).get("task")
                        if task and not task.done():
                            task.cancel()
                except Exception:
                    pass

                try:
                    from pyrogram.enums import ParseMode
                    await bot.send_message(
                        chat_id,
                        "🧹 <b>Solo game auto-ended</b> due to inactivity (10 min).\n"
                        "Start a new game with /start",
                        parse_mode=ParseMode.HTML,
                    )
                except Exception:
                    pass

                try:
                    from database.games import end_game as close_db_game
                    await close_db_game(chat_id)
                except Exception:
                    pass

                ACTIVE_MATCHES.pop(chat_id, None)
                print(f"🧹 Solo match in {chat_id} auto-cleaned (idle).")

        except Exception as e:
            print(f"Solo cleanup error: {e}")
