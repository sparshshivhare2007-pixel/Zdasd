import io
import os
import random
from PIL import Image, ImageDraw, ImageFont

ASSETS = os.path.join(os.path.dirname(__file__), "..", "..", "Assets")
FONT_PATH = os.path.join(ASSETS, "namefont.ttf")   # all text uses this font

W, H = 920, 510

# ── font loader ───────────────────────────────────────────────────────────────

def _font(size):
    try:
        return ImageFont.truetype(FONT_PATH, size)
    except Exception:
        return ImageFont.load_default()

# ── circle mask ───────────────────────────────────────────────────────────────

def _circle_mask(size):
    m = Image.new("L", (size, size), 0)
    ImageDraw.Draw(m).ellipse((0, 0, size - 1, size - 1), fill=255)
    return m

# ── stroke patterns ───────────────────────────────────────────────────────────

def _stroke_diagonal(d, ac, acd, dark):
    def s(pts, c, a): d.polygon(pts, fill=c + (a,))
    s([(0,int(H*.45)),(0,H),(70,H),(45,int(H*.35))], acd, 230)
    s([(0,int(H*.15)),(0,int(H*.50)),(110,int(H*.38)),(75,int(H*.05))], acd, 200)
    s([(0,int(H*.50)),(0,H),(100,H),(60,int(H*.40))], ac, 155)
    s([(0,int(H*.20)),(0,int(H*.55)),(50,int(H*.45)),(20,int(H*.12))], ac, 90)
    s([(85,H),(260,int(H*.08)),(340,int(H*.22)),(165,H)], acd, 215)
    s([(40,H),(195,int(H*.05)),(270,int(H*.20)),(115,H)], ac, 135)
    s([(140,H),(310,int(H*.12)),(390,int(H*.30)),(225,H)], acd, 165)
    s([(0,0),(200,0),(160,55),(0,70)], acd, 175)
    s([(0,0),(130,0),(95,38),(0,50)], ac, 110)
    s([(W-60,0),(W,0),(W,int(H*.35)),(W-80,int(H*.25))], acd, 180)
    s([(W-100,0),(W-55,0),(W-35,int(H*.25)),(W-115,int(H*.15))], ac, 115)
    s([(55,int(H*.65)),(85,int(H*.60)),(175,H),(135,H)], dark, 195)
    s([(235,int(H*.10)),(295,int(H*.02)),(365,int(H*.22)),(300,int(H*.30))], dark, 170)

def _stroke_frost(d, ac, acd, dark):
    def s(pts, c, a): d.polygon(pts, fill=c + (a,))
    s([(0,int(H*.06)),(W,int(H*.06)),(W,int(H*.18)),(0,int(H*.14))], acd, 80)
    s([(0,int(H*.40)),(W,int(H*.36)),(W,int(H*.52)),(0,int(H*.56))], acd, 70)
    s([(0,int(H*.80)),(W,int(H*.76)),(W,int(H*.86)),(0,int(H*.90))], acd, 75)
    s([(0,int(H*.10)),(int(W*.6),int(H*.09)),(int(W*.6),int(H*.12)),(0,int(H*.13))], ac, 160)
    s([(0,int(H*.44)),(int(W*.55),int(H*.42)),(int(W*.55),int(H*.46)),(0,int(H*.48))], ac, 145)
    s([(0,int(H*.82)),(int(W*.65),int(H*.80)),(int(W*.65),int(H*.83)),(0,int(H*.85))], ac, 155)
    s([(0,0),(int(W*.35),0),(int(W*.28),int(H*.22)),(0,int(H*.28))], acd, 190)
    s([(0,0),(int(W*.20),0),(int(W*.14),int(H*.14)),(0,int(H*.18))], ac, 130)
    s([(int(W*.50),H),(W,H),(W,int(H*.70)),(int(W*.60),int(H*.78))], acd, 175)

def _stroke_explosion(d, ac, acd, dark):
    def s(pts, c, a): d.polygon(pts, fill=c + (a,))
    s([(0,H),(120,H),(80,int(H*.30)),(20,int(H*.42))], acd, 220)
    s([(60,H),(200,H),(155,int(H*.15)),(100,int(H*.28))], ac, 160)
    s([(170,H),(310,H),(265,int(H*.22)),(210,int(H*.35))], acd, 200)
    s([(260,H),(360,H),(330,int(H*.40)),(285,int(H*.50))], ac, 130)
    s([(int(W*.55),H),(int(W*.70),H),(int(W*.66),int(H*.55)),(int(W*.58),int(H*.62))], acd, 150)
    s([(0,0),(160,0),(120,int(H*.28)),(0,int(H*.38))], acd, 170)
    s([(0,0),(90,0),(60,int(H*.18)),(0,int(H*.24))], ac, 115)
    s([(W-50,H),(W,H),(W,int(H*.45)),(W-70,int(H*.55))], acd, 175)
    s([(W-90,H),(W-45,H),(W-40,int(H*.60)),(W-100,int(H*.68))], ac, 120)
    s([(50,int(H*.70)),(90,int(H*.65)),(160,H),(110,H)], dark, 200)

def _stroke_corners(d, ac, acd, dark):
    def s(pts, c, a): d.polygon(pts, fill=c + (a,))
    s([(0,0),(int(W*.30),0),(int(W*.22),int(H*.45)),(0,int(H*.50))], acd, 210)
    s([(0,0),(int(W*.18),0),(int(W*.12),int(H*.30)),(0,int(H*.35))], ac, 155)
    s([(W,0),(int(W*.72),0),(int(W*.80),int(H*.38)),(W,int(H*.45))], acd, 190)
    s([(W,0),(int(W*.85),0),(int(W*.90),int(H*.22)),(W,int(H*.28))], ac, 130)
    s([(0,H),(int(W*.28),H),(int(W*.20),int(H*.58)),(0,int(H*.52))], acd, 200)
    s([(0,H),(int(W*.16),H),(int(W*.10),int(H*.72)),(0,int(H*.66))], ac, 140)
    s([(W,H),(int(W*.75),H),(int(W*.82),int(H*.60)),(W,int(H*.55))], acd, 185)
    cx = W // 2
    s([(cx-28,0),(cx+28,0),(cx+20,H),(cx-20,H)], acd, 45)
    s([(cx-12,0),(cx+12,0),(cx+8,H),(cx-8,H)], ac, 60)
    s([(int(W*.18),int(H*.48)),(int(W*.24),int(H*.44)),(int(W*.32),int(H*.60)),(int(W*.26),int(H*.64))], dark, 190)

def _stroke_criss_cross(d, ac, acd, dark):
    """Dual X-crossing slashes — Rose / Neon style."""
    def s(pts, c, a): d.polygon(pts, fill=c + (a,))
    # Forward slash (bottom-left → top-right)
    s([(0,H),(0,int(H*.60)),(int(W*.55),0),(int(W*.70),0),(int(W*.15),int(H*.40)),(0,H)], acd, 200)
    s([(0,H),(0,int(H*.75)),(int(W*.40),0),(int(W*.52),0),(int(W*.10),int(H*.55)),(0,H)], ac, 140)
    # Back slash (top-left → bottom-right)
    s([(0,0),(int(W*.18),0),(int(W*.65),H),(int(W*.50),H),(0,int(H*.38))], acd, 185)
    s([(0,0),(int(W*.09),0),(int(W*.50),H),(int(W*.38),H),(0,int(H*.22))], ac, 115)
    # Right edge vertical slabs
    s([(W-55,0),(W,0),(W,H),(W-75,H)], acd, 130)
    s([(W-100,0),(W-55,0),(W-70,H),(W-115,H)], ac, 80)
    # Top-right corner blot
    s([(int(W*.65),0),(W,0),(W,int(H*.30)),(int(W*.75),int(H*.18))], acd, 160)
    # Dark depth
    s([(int(W*.25),int(H*.42)),(int(W*.32),int(H*.38)),(int(W*.42),int(H*.55)),(int(W*.35),int(H*.60))], dark, 185)
    s([(int(W*.10),int(H*.28)),(int(W*.16),int(H*.24)),(int(W*.24),int(H*.38)),(int(W*.18),int(H*.42))], dark, 165)

def _stroke_wave(d, ac, acd, dark):
    """Curved wave bars — Neon Teal style."""
    def s(pts, c, a): d.polygon(pts, fill=c + (a,))
    # Simulate wave as a series of tapered bars at angles
    # Wave 1: upper-left
    for i, ox in enumerate(range(0, 220, 38)):
        shade = acd if i % 2 == 0 else ac
        alpha = 190 - i * 12
        s([(ox, int(H*.05 + i*8)), (ox+35, int(H*.02 + i*8)),
           (ox+28, int(H*.28 + i*5)), (ox-5, int(H*.31 + i*5))], shade, alpha)
    # Wave 2: lower
    for i, ox in enumerate(range(0, 280, 42)):
        shade = ac if i % 2 == 0 else acd
        alpha = 175 - i * 10
        s([(ox, int(H*.65 + i*4)), (ox+38, int(H*.62 + i*4)),
           (ox+30, int(H*.88 + i*2)), (ox-6, int(H*.91 + i*2))], shade, alpha)
    # Right side vertical accent
    s([(W-65,0),(W,0),(W,H),(W-80,H)], acd, 140)
    s([(W-105,0),(W-65,0),(W-80,H),(W-120,H)], ac, 85)
    # Top band
    s([(0,0),(W,0),(W,28),(0,38)], acd, 110)
    s([(0,0),(W,0),(W,14),(0,20)], ac, 80)

STROKE_MAP = {
    "neon_green":    _stroke_diagonal,
    "crimson_fire":  _stroke_diagonal,
    "cosmic_purple": _stroke_diagonal,
    "cyber_gold":    _stroke_corners,
    "arctic_ice":    _stroke_frost,
    "toxic_orange":  _stroke_explosion,
    "steel_blue":    _stroke_corners,
    "neon_rose":     _stroke_criss_cross,
    "neon_teal":     _stroke_wave,
}

# ── themes ────────────────────────────────────────────────────────────────────

THEMES = [
    {
        "id": "neon_green",
        "bg":          (6,  12,  26),
        "accent":      (50, 235,  10),
        "accent_dark": (20, 120,   5),
        "accent_glow": (80, 255,  40),
        "title":       (50, 235,  10),
        "label":       (210, 255, 210),
        "value":       (255, 255, 255),
        "id_col":      (50,  235,  10),
        "divider":     (40, 100,  40),
        "ring":        (50,  235,  10),
        "box_bg":      (10,  30,   10),
        "sub":         (150, 215, 150),
    },
    {
        "id": "crimson_fire",
        "bg":          (15,   5,   8),
        "accent":      (255,  25,  55),
        "accent_dark": (140,  10,  25),
        "accent_glow": (255,  80, 100),
        "title":       (255,  60,  85),
        "label":       (255, 210, 215),
        "value":       (255, 255, 255),
        "id_col":      (255,  80, 100),
        "divider":     (110,  35,  45),
        "ring":        (255,  25,  55),
        "box_bg":      (30,    8,  12),
        "sub":         (240, 155, 170),
    },
    {
        "id": "cosmic_purple",
        "bg":          ( 6,   0,  20),
        "accent":      (150,  40, 255),
        "accent_dark": (80,   10, 160),
        "accent_glow": (190, 100, 255),
        "title":       (200, 110, 255),
        "label":       (230, 210, 255),
        "value":       (255, 255, 255),
        "id_col":      (200, 110, 255),
        "divider":     (75,  35, 125),
        "ring":        (150,  40, 255),
        "box_bg":      (18,    5,  40),
        "sub":         (205, 160, 255),
    },
    {
        "id": "cyber_gold",
        "bg":          (10,   8,   2),
        "accent":      (255, 200,   0),
        "accent_dark": (160, 110,   0),
        "accent_glow": (255, 230,  80),
        "title":       (255, 215,  30),
        "label":       (255, 245, 195),
        "value":       (255, 255, 255),
        "id_col":      (255, 215,  30),
        "divider":     (110,  80,   5),
        "ring":        (255, 200,   0),
        "box_bg":      (28,  20,   2),
        "sub":         (240, 190,  85),
    },
    {
        "id": "arctic_ice",
        "bg":          ( 4,  12,  28),
        "accent":      ( 0, 220, 255),
        "accent_dark": ( 0,  90, 160),
        "accent_glow": (80, 240, 255),
        "title":       ( 0, 232, 255),
        "label":       (185, 242, 255),
        "value":       (255, 255, 255),
        "id_col":      ( 0, 232, 255),
        "divider":     (20,  90, 130),
        "ring":        ( 0, 220, 255),
        "box_bg":      ( 5,  25,  50),
        "sub":         (130, 215, 245),
    },
    {
        "id": "toxic_orange",
        "bg":          (12,   6,   2),
        "accent":      (255, 110,   0),
        "accent_dark": (160,  50,   0),
        "accent_glow": (255, 160,  40),
        "title":       (255, 135,  15),
        "label":       (255, 228, 195),
        "value":       (255, 255, 255),
        "id_col":      (255, 145,  25),
        "divider":     (120,  55,  10),
        "ring":        (255, 110,   0),
        "box_bg":      (30,  14,   3),
        "sub":         (240, 172,  95),
    },
    {
        "id": "steel_blue",
        "bg":          ( 5,  10,  22),
        "accent":      (30, 120, 255),
        "accent_dark": (10,  55, 160),
        "accent_glow": (80, 165, 255),
        "title":       (65, 150, 255),
        "label":       (190, 218, 255),
        "value":       (255, 255, 255),
        "id_col":      (80, 162, 255),
        "divider":     (25,  65, 130),
        "ring":        (30, 120, 255),
        "box_bg":      (10,  20,  55),
        "sub":         (140, 192, 255),
    },
    # ── NEW STYLE 1: Neon Rose ───────────────────────────────────────────────
    {
        "id": "neon_rose",
        "bg":          (14,   4,  14),
        "accent":      (255,  20, 180),
        "accent_dark": (160,   5, 100),
        "accent_glow": (255, 100, 200),
        "title":       (255,  60, 195),
        "label":       (255, 200, 240),
        "value":       (255, 255, 255),
        "id_col":      (255,  80, 200),
        "divider":     (110,  20,  80),
        "ring":        (255,  20, 180),
        "box_bg":      (35,    5,  30),
        "sub":         (240, 140, 210),
    },
    # ── NEW STYLE 2: Neon Teal ───────────────────────────────────────────────
    {
        "id": "neon_teal",
        "bg":          ( 2,  14,  14),
        "accent":      ( 0, 240, 200),
        "accent_dark": ( 0, 110,  90),
        "accent_glow": (80, 255, 220),
        "title":       ( 0, 245, 205),
        "label":       (185, 255, 245),
        "value":       (255, 255, 255),
        "id_col":      ( 0, 245, 205),
        "divider":     (15,  90,  75),
        "ring":        ( 0, 240, 200),
        "box_bg":      ( 5,  32,  28),
        "sub":         (120, 235, 210),
    },
]

# ── draw brush strokes ────────────────────────────────────────────────────────

def _draw_strokes(img: Image.Image, theme: dict):
    ov   = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d    = ImageDraw.Draw(ov)
    ac   = theme["accent"]
    acd  = theme["accent_dark"]
    dark = tuple(max(0, c - 18) for c in theme["bg"])
    STROKE_MAP.get(theme["id"], _stroke_diagonal)(d, ac, acd, dark)
    img.paste(ov, mask=ov.split()[3])

# ── draw profile box ──────────────────────────────────────────────────────────

def _draw_profile_box(card: Image.Image, photo_bytes, theme: dict):
    glow = theme["accent_glow"]
    ring = theme["ring"]
    bbg  = theme["box_bg"]

    bsz = 280
    bx  = W - bsz - 38
    by  = (H - bsz) // 2

    # Box outer glow
    gl = Image.new("RGBA", card.size, (0, 0, 0, 0))
    gd = ImageDraw.Draw(gl)
    for sp in range(22, 0, -1):
        a = int(135 * (sp / 22) ** 1.6)
        gd.rounded_rectangle([bx - sp, by - sp, bx + bsz + sp, by + bsz + sp],
                              radius=30 + sp, fill=glow + (a,))
    card.paste(gl, mask=gl.split()[3])

    # Box background
    bl = Image.new("RGBA", card.size, (0, 0, 0, 0))
    ImageDraw.Draw(bl).rounded_rectangle([bx, by, bx + bsz, by + bsz],
                                         radius=26, fill=bbg + (255,))
    card.paste(bl, mask=bl.split()[3])

    # Circle dimensions
    cd = 220
    cx = bx + (bsz - cd) // 2
    cy = by + (bsz - cd) // 2

    # Load profile photo
    pfp = None
    if photo_bytes:
        try:
            photo_bytes.seek(0)
            pfp = Image.open(photo_bytes).convert("RGBA")
            pfp = pfp.resize((cd, cd), Image.LANCZOS)
        except Exception:
            pfp = None

    if pfp is None:
        pfp = Image.new("RGBA", (cd, cd), (45, 45, 45, 255))
        ImageDraw.Draw(pfp).ellipse((0, 0, cd - 1, cd - 1), fill=(60, 60, 60, 255))

    mask = _circle_mask(cd)

    # Glow ring
    rl = Image.new("RGBA", card.size, (0, 0, 0, 0))
    rd = ImageDraw.Draw(rl)
    for i in range(14, 0, -1):
        a = int(210 * (i / 14) ** 2)
        rd.ellipse([cx - i, cy - i, cx + cd + i, cy + cd + i],
                   outline=glow + (a,), width=2)
    card.paste(rl, mask=rl.split()[3])

    # Hard ring border
    brd = Image.new("RGBA", card.size, (0, 0, 0, 0))
    bdd = ImageDraw.Draw(brd)
    bdd.ellipse([cx - 6, cy - 6, cx + cd + 6, cy + cd + 6],
                outline=(255, 255, 255, 200), width=5)
    bdd.ellipse([cx - 2, cy - 2, cx + cd + 2, cy + cd + 2],
                outline=ring + (255,), width=3)
    card.paste(brd, mask=brd.split()[3])

    # Paste photo
    pl = Image.new("RGBA", card.size, (0, 0, 0, 0))
    pl.paste(pfp, (cx, cy), mask=mask)
    card.paste(pl, mask=pl.split()[3])

# ── draw text (namefont.ttf only, no shadow / border) ────────────────────────

def _t(draw, xy, text, font, color):
    draw.text(xy, text, font=font, fill=color)

def _draw_text(card: Image.Image, user, stats: dict, theme: dict):
    d = ImageDraw.Draw(card)

    f_title  = _font(42)
    f_value  = _font(30)
    f_label  = _font(21)
    f_id     = _font(17)
    f_sub    = _font(19)
    f_footer = _font(14)

    px = 34   # left padding

    # Player ID badge (solid accent pill + text)
    uid_txt = f"#PLAYER ID: {user.id}"
    d.rounded_rectangle([px - 2, 12, px + 20, 36], radius=5, fill=theme["accent"])
    _t(d, (px + 26, 15), uid_txt, f_id, theme["id_col"])

    # Player name
    _t(d, (px, 44), (user.first_name or "Player").upper(), f_title, theme["title"])

    # Rank / title subtitle
    try:
        from plugins.utilities.userinfo import calculate_rank, calculate_title
        score, tier = calculate_rank(stats)
        title_str   = calculate_title(stats)
    except Exception:
        score, tier, title_str = 0, "—", "—"
    sub = title_str if title_str != "—" else tier
    _t(d, (px, 96), sub.upper(), f_sub, theme["sub"])

    # Accent bar under subtitle
    d.line([(px, 124), (490, 124)], fill=theme["accent"], width=2)

    # Stats rows
    runs      = stats.get("runs", 0)
    wickets   = stats.get("wickets", 0)
    matches   = stats.get("matches", 0)
    fifties   = stats.get("fifties", 0)
    centuries = stats.get("centuries", 0)
    balls     = stats.get("balls_faced", 0)
    highest   = stats.get("highest_score", 0)
    sr        = round(runs / balls * 100, 1) if balls > 0 else 0.0

    rows = [
        ("MATCHES",        str(matches)),
        ("RUNS",           str(runs)),
        ("WICKETS",        str(wickets)),
        ("50s / 100s",     f"{fifties}  /  {centuries}"),
        ("STRIKE RATE",    str(sr)),
        ("HIGHEST SCORE",  str(highest)),
    ]

    row_y  = 134
    row_h  = 58
    val_x  = 305

    for i, (label, val) in enumerate(rows):
        y = row_y + i * row_h
        if i > 0:
            d.line([(px, y - 1), (val_x + 145, y - 1)], fill=theme["divider"], width=1)
        _t(d, (px,    y + 9), label, f_label, theme["label"])
        _t(d, (val_x, y + 5), val,   f_value, theme["value"])

    # Footer
    _t(d, (px, H - 32), f"#CricketLegacy  •  Perf Score: {score}", f_footer, theme["sub"])

# ── public API ────────────────────────────────────────────────────────────────

def generate_card(photo_bytes, user, stats: dict) -> io.BytesIO:
    theme = random.choice(THEMES)

    card = Image.new("RGB", (W, H), theme["bg"])
    _draw_strokes(card, theme)

    # Centre-left dark vignette keeps text legible over strokes
    vig = Image.new("RGBA", card.size, (0, 0, 0, 0))
    vd  = ImageDraw.Draw(vig)
    for i in range(200, 0, -1):
        a  = int(125 * (1 - i / 200) ** 2)
        x0 = W // 2 - 40 + (200 - i) // 2
        vd.rectangle([x0, 0, x0 + 1, H], fill=(0, 0, 0, a))
    card.paste(vig, mask=vig.split()[3])

    card = card.convert("RGBA")
    _draw_profile_box(card, photo_bytes, theme)
    card = card.convert("RGB")
    _draw_text(card, user, stats, theme)

    buf = io.BytesIO()
    card.save(buf, format="PNG")
    buf.seek(0)
    return buf


async def download_user_photo(client, user_id: int):
    """Download first profile photo using the correct async-generator API."""
    try:
        photo = None
        async for p in client.get_chat_photos(user_id, limit=1):
            photo = p
            break
        if photo is None:
            return None
        data = await client.download_media(photo, in_memory=True)
        if data:
            data.seek(0)
            return data
        return None
    except Exception:
        return None
