import io
from PIL import Image, ImageDraw, ImageFont

PROFILE_TEMPLATE = "Assets/user.jpeg"
STATS_FONT_PATH = "Assets/fonts.ttf"
NAME_FONT_PATH = "Assets/namefont.ttf"

async def load_profile_photo(client, user, size):
    try:
        photos = await client.get_profile_photos(user.id, limit=1)
        if not photos:
            raise ValueError("No profile photo")

        file = await client.download_media(photos[0].file_id, in_memory=True)
        img = Image.open(io.BytesIO(file.getvalue())).convert("RGBA")
        return img.resize((size, size), Image.LANCZOS)

    except Exception as e:
        print("PFP fallback:", e)
        return Image.new("RGBA", (size, size), (120, 120, 120, 255))

def circular_crop(img, size):
    mask = Image.new("L", (size, size), 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse((0, 0, size, size), fill=255)

    out = Image.new("RGBA", (size, size))
    out.paste(img, (0, 0), mask)
    return out

async def generate_profile_card(client, user, stats):
    base = Image.open(PROFILE_TEMPLATE).convert("RGBA")
    draw = ImageDraw.Draw(base)

    name_font = ImageFont.truetype(NAME_FONT_PATH, 42)
    stat_font = ImageFont.truetype(STATS_FONT_PATH, 30)

    CIRCLE_SIZE = 320
    CIRCLE_X = 170
    CIRCLE_Y = 110

    pfp = await load_profile_photo(client, user, CIRCLE_SIZE)
    pfp = circular_crop(pfp, CIRCLE_SIZE)

    base.paste(pfp, (CIRCLE_X, CIRCLE_Y), pfp)

    name_text = (user.first_name or "Player")[:18]
    text_width = draw.textlength(name_text, font=name_font)

    name_x = CIRCLE_X + (CIRCLE_SIZE // 2) - (text_width // 2)
    name_y = CIRCLE_Y + CIRCLE_SIZE + 25

    draw.text((name_x, name_y), name_text, font=name_font, fill=(255, 215, 160))

    value_x = 750
    start_y = 105
    gap = 48

    matches = stats.get("matches", 0)
    runs = stats.get("runs", 0)
    balls = max(1, stats.get("balls_faced", 1))

    values = [
        str(matches),
        str(runs),
        str(stats.get("highest_score", 0)),
        f"{runs / max(1, matches):.2f}",
        f"{(runs / balls) * 100:.2f}",
        f"{stats.get('fifties', 0)}/{stats.get('centuries', 0)}",
    ]

    for i, val in enumerate(values):
        draw.text((value_x, start_y + i * gap), val, font=stat_font, fill=(235, 235, 235))

    buf = io.BytesIO()
    base.save(buf, format="PNG")
    buf.seek(0)
    return buf
    
