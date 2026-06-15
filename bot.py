import asyncio
import time
from pyrogram import Client, idle
from pyrogram.enums import ParseMode
from config import Config
from database.connection import db
from database.migrate import migrate

LOG_CHANNEL = -1003692127639


async def _db_watchdog():
    while True:
        await asyncio.sleep(15)
        if not db.client:
            print("🔌 DB watchdog: pool is gone, reconnecting…")
            await db.connect(retries=5, delay=3.0)

async def initialize_database():
    await db.connect()
    await migrate()
    try:
        from database.settings import load_settings
        await load_settings(force=True)
        print("✅ Settings loaded")
    except Exception as e:
        print(f"⚠️ Settings load failed: {e}")
    print("✅ Database connected & tables ready")

async def start_nexora():

    start_time = time.time()

    bot = Client(
        "bot",
        bot_token=Config.BOT_TOKEN,
        api_id=Config.API_ID,
        api_hash=Config.API_HASH,
        workers=80,
        plugins=dict(root="plugins")
    )

    try:
        await initialize_database()
    except Exception as e:
        print(f"❌ Database Initialization Failed: {e}")

    await bot.start()

    boot_speed = round(time.time() - start_time, 2)

    print("🚀 Nexora Cricket Bot is Online!")

    try:
        me = await bot.get_me()

        startup_text = (
            "🚀 <b>ʟᴇɢᴀᴄʏ ʙᴏᴛ ɪꜱ ᴏɴʟɪɴᴇ</b>\n\n"
            "━━━━━━━━━━━━━━━\n"
            f"🤖 <b>Bot :</b> {me.first_name}\n"
            f"🆔 <b>ID :</b> <code>{me.id}</code>\n"
            f"⚡ <b>Startup Speed :</b> {boot_speed}s\n"
            f"🧠 <b>Workers :</b> 80\n"
            f"🗄 <b>Database :</b> Connected\n"
            f"🌐 <b>Status :</b> Running\n"
            "━━━━━━━━━━━━━━━\n"
            "✨ <b>ʟᴇɢᴀᴄʏ ᴘᴏᴡᴇʀᴇᴅ</b>"
        )

        await bot.send_message(
            LOG_CHANNEL,
            startup_text,
            parse_mode=ParseMode.HTML
        )

    except Exception as e:
        print("Log channel error:", e)

    from plugins.game.team import ACTIVE_MATCHES
    for m in ACTIVE_MATCHES.values():
        if not m.get("client"):
            m["client"] = bot

    asyncio.create_task(_db_watchdog())
    print("🔌 Database watchdog active.")

    from plugins.game.team.cleanup import auto_clean_matches
    asyncio.create_task(auto_clean_matches(bot))
    print("🧹 Background Garbage Collector is active!")

    from plugins.game.solo.cleanup import auto_clean_solo
    asyncio.create_task(auto_clean_solo(bot))
    print("🧹 Solo Background Cleaner is active!")

    from plugins.utilities.nudge import start_nudge_task
    start_nudge_task(bot)

    await idle()

    print("🛑 Shutting down...")
    await bot.stop()
    await db.close()

if __name__ == "__main__":
    try:
        asyncio.get_event_loop().run_until_complete(start_nexora())
    except KeyboardInterrupt:
        print("👋 Bot stopped manually.")
        
