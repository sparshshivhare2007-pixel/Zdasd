import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from config import Config


class Database:
    def __init__(self):
        self.client = None
        self.db = None

    async def connect(self, retries: int = 10, delay: float = 3.0):
        for attempt in range(1, retries + 1):
            try:
                print(f"🗄️ Connecting to MongoDB... (attempt {attempt}/{retries})")
                self.client = AsyncIOMotorClient(Config.MONGO_URL)
                self.db = self.client.get_default_database()
                await self.client.admin.command("ping")
                print("✅ MongoDB Connected.")
                return
            except Exception as e:
                print(f"⚠️ DB connect attempt {attempt} failed: {e}")
                if attempt < retries:
                    wait = delay * attempt
                    print(f"🔄 Retrying in {wait:.0f}s…")
                    await asyncio.sleep(wait)
        print("❌ Could not connect to MongoDB after all retries. Some features will be unavailable.")

    async def ensure_pool(self):
        if not self.client:
            await self.connect(retries=5, delay=2.0)

    async def close(self):
        if self.client:
            self.client.close()
            self.client = None
            self.db = None


db = Database()
