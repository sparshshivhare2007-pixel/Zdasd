import os


class Config:
    # Telegram API
    API_ID = int(os.getenv("API_ID", "25887786"))
    API_HASH = os.getenv("API_HASH", "e4201277f5f2883f22c150167bd24479")
    BOT_TOKEN = os.getenv("BOT_TOKEN", "8917961129:AAF3Dmr88w6nx5quMT9mc9XQ5NaJHe1_bSk")

    # Database
    MONGO_URL = os.getenv(
        "MONGO_URL",
        "mongodb+srv://bsdk:betichod@cluster0.fgj1r9z.mongodb.net/Cricketlegacy?retryWrites=true&w=majority"
    )

    # Bot Info
    BOT_USERNAME = os.getenv("BOT_USERNAME", "@testingpgcbot")
    SUPPORT_GROUP = os.getenv(
        "SUPPORT_GROUP",
        "https://t.me/+joF1bCfiMT9jMzVh"
    )
    PLAY_ZONE_INFO = os.getenv(
        "PLAY_ZONE_INFO",
        "https://t.me/+joF1bCfiMT9jMzVh"
    )

    # Owners
    OWNER_IDS = {
        int(x)
        for x in os.getenv("OWNER_IDS", "8933874700").split()
    }

    # GitHub
    GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
    UPSTREAM_REPO = os.getenv(
        "UPSTREAM_REPO",
        "https://github.com/sparshshivhare2007-pixel/Zdasd"
    )

    # AI / NVIDIA
    NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY", "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")

    # Images
    START_IMAGE = os.getenv(
        "START_IMAGE",
        "https://graph.org/file/a37d935e98e4c92e04cee-c1871cfafb3f808563.jpg"
    )

    # Logs
    LOG_CHANNEL = int(
        os.getenv("LOG_CHANNEL", "-1003773882799")
    )
