"""
/settings — per-group feature toggle panel (admins only).

Free features  : super_over, ai_summary, achievement_alerts, auto_play_again
Premium features: spam_free (Basic+), disabled_numbers (Standard+), edge_rule (Pro)

Callback scheme:
  gs_home                   main panel
  gs_view_<feature>         feature sub-panel
  gs_toggle_<feature>_<1|0> toggle ON/OFF
  gs_dn                     disabled numbers panel
  gs_dn_toggle_<n>          toggle number n (0-6)
"""

from pyrogram import Client, filters
from pyrogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CallbackQuery,
    Message,
)
from pyrogram.enums import ParseMode

from database.group_settings import get_group_settings, set_group_setting
from database.premium import get_premium, PLANS, plan_unlocked
from utils.guards import is_group_admin


FREE_FEATURES = [
    ("super_over",         "⚡ Super Over on Tie"),
    ("ai_summary",         "🧠 AI Over Summary"),
    ("achievement_alerts", "🔔 Achievement Alerts"),
    ("auto_play_again",    "🔄 Auto Play Again"),
]

PREMIUM_FEATURES = [
    ("spam_free",        "🛡️ Spam Free Mode",   "basic"),
    ("disabled_numbers", "🔲 Disabled Numbers", "standard"),
    ("edge_rule",        "⚠️ Edge Rule",        "pro"),
]

FEATURE_DESC = {
    "super_over": (
        "⚡ <b>Super Over on Tie</b>\n\n"
        "When a match ends in a tie a Super Over is automatically triggered.\n"
        "Both captains pick 1 batter and 1 bowler.\n"
        "Each team plays 1 over with 1 wicket in hand.\n"
        "Highest score wins. Double-tie → match declared a Tie."
    ),
    "ai_summary": (
        "🧠 <b>AI Over Summary</b>\n\n"
        "After every over our AI commentator delivers a sharp,\n"
        "funny 2–3 line analysis of what just happened.\n"
        "Powered by Llama 3.1 70B via NVIDIA API."
    ),
    "achievement_alerts": (
        "🔔 <b>Achievement Alerts</b>\n\n"
        "Real-time announcements in the group for:\n"
        "50s, 100s, 150s, 250s, 3-wicket hauls, 5-fors,\n"
        "hat-tricks, ducks, and partnership milestones."
    ),
    "auto_play_again": (
        "🔄 <b>Auto Play Again</b>\n\n"
        "After every match a 'Play Again?' prompt appears\n"
        "in the group so players can quickly start a new game."
    ),
    "spam_free": (
        "🛡️ <b>Spam Free Mode</b>  <i>(Premium)</i>\n\n"
        "Prevents bowlers from sending the same number\n"
        "3 consecutive times in a row.\n\n"
        "Example: 4 → 4 → 4 is blocked. 4 → 4 → 5 is fine.\n\n"
        "📦 Requires <b>Basic plan (₹29)</b> or above."
    ),
    "disabled_numbers": (
        "🔲 <b>Disabled Numbers</b>  <i>(Premium)</i>\n\n"
        "Block up to 2 numbers (0–6) from the game entirely.\n"
        "Neither batters nor bowlers can use them.\n\n"
        "Great for custom game modes and tighter strategies.\n\n"
        "📦 Requires <b>Standard plan (₹49)</b> or above."
    ),
    "edge_rule": (
        "⚠️ <b>Edge Rule</b>  <i>(Premium)</i>\n\n"
        "Batter plays 3 consecutive 0s → warning DM sent.\n"
        "Batter plays a 4th consecutive 0 → automatically out!\n\n"
        "Encourages active batting and punishes pure defence.\n\n"
        "📦 Requires <b>Pro plan (₹70)</b>."
    ),
}

PLAN_LOCK_MSG = {
    "basic":    "🔒 Unlock with <b>Basic Plan (₹29)</b>.",
    "standard": "🔒 Unlock with <b>Standard Plan (₹49)</b>.",
    "pro":      "🔒 Unlock with <b>Pro Plan (₹70)</b>.",
}


# ─── Panel builders ───────────────────────────────────────────────────────────

async def _main_panel(chat_id: int):
    settings = await get_group_settings(chat_id)
    premium  = await get_premium(chat_id)
    plan_name = PLANS[premium["plan"]]["name"] if premium else None

    lines = ["⚙️ <b>GROUP SETTINGS</b>\n────┈┄┄╌╌╌╌┄┄┈────\n"]
    if plan_name:
        lines.append(f"✨ Premium: <b>{plan_name}</b>\n")
    else:
        lines.append("🔓 Free tier  |  contact owner for premium\n")
    lines.append("────┈┄┄╌╌╌╌┄┄┈────\n🆓 <b>Free Features</b>")

    buttons = []
    for key, label in FREE_FEATURES:
        val    = settings.get(key, True)
        status = "✅" if val else "❌"
        buttons.append([InlineKeyboardButton(f"{status} {label}", callback_data=f"gs_view_{key}")])

    lines.append("\n💎 <b>Premium Features</b>")
    for key, label, req_plan in PREMIUM_FEATURES:
        if key == "disabled_numbers":
            dn      = settings.get(key, [])
            dn_str  = f"[{', '.join(map(str, dn))}]" if dn else "[none]"
            unlocked = premium and plan_unlocked(premium, req_plan)
            status  = f"🔲 {dn_str}" if unlocked else "🔒"
            buttons.append([InlineKeyboardButton(f"{status} {label}", callback_data="gs_dn")])
        else:
            unlocked = premium and plan_unlocked(premium, req_plan)
            if unlocked:
                val    = settings.get(key, False)
                status = "✅" if val else "❌"
            else:
                status = "🔒"
            buttons.append([InlineKeyboardButton(f"{status} {label}", callback_data=f"gs_view_{key}")])

    return "\n".join(lines), InlineKeyboardMarkup(buttons)


async def _feature_panel(chat_id: int, feature: str):
    settings         = await get_group_settings(chat_id)
    premium          = await get_premium(chat_id)
    is_prem_feature  = feature in {f[0] for f in PREMIUM_FEATURES}
    req_plan         = next((f[2] for f in PREMIUM_FEATURES if f[0] == feature), None)
    has_access       = not is_prem_feature or (premium and plan_unlocked(premium, req_plan))
    desc             = FEATURE_DESC.get(feature, f"⚙️ <b>{feature}</b>")

    if not has_access:
        lock_msg = PLAN_LOCK_MSG.get(req_plan, "🔒 Upgrade to unlock.")
        text = f"{desc}\n\n────┈┄┄╌╌╌╌┄┄┈────\n{lock_msg}"
        return text, InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="gs_home")]])

    default = False if is_prem_feature else True
    val     = settings.get(feature, default)
    status  = "✅ <b>ON</b>" if val else "❌ <b>OFF</b>"
    text    = f"{desc}\n\n────┈┄┄╌╌╌╌┄┄┈────\nStatus: {status}"
    buttons = [
        [
            InlineKeyboardButton("✅ Enable",  callback_data=f"gs_toggle_{feature}_1"),
            InlineKeyboardButton("❌ Disable", callback_data=f"gs_toggle_{feature}_0"),
        ],
        [InlineKeyboardButton("🔙 Back", callback_data="gs_home")],
    ]
    return text, InlineKeyboardMarkup(buttons)


async def _dn_panel(chat_id: int):
    settings = await get_group_settings(chat_id)
    premium  = await get_premium(chat_id)
    dn       = settings.get("disabled_numbers", [])

    if not premium or not plan_unlocked(premium, "standard"):
        text = (
            f"{FEATURE_DESC['disabled_numbers']}\n\n"
            "────┈┄┄╌╌╌╌┄┄┈────\n"
            f"{PLAN_LOCK_MSG['standard']}"
        )
        return text, InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="gs_home")]])

    text = (
        "🔲 <b>Disabled Numbers</b>\n"
        "────┈┄┄╌╌╌╌┄┄┈────\n"
        "Tap a number to toggle it.\n"
        "Up to <b>2 numbers</b> can be disabled at once.\n\n"
        f"Disabled: <b>{', '.join(map(str, dn)) if dn else 'None'}</b>\n"
        "────┈┄┄╌╌╌╌┄┄┈────"
    )
    row = [
        InlineKeyboardButton(
            f"🚫{n}" if n in dn else str(n),
            callback_data=f"gs_dn_toggle_{n}",
        )
        for n in range(7)
    ]
    buttons = [row, [InlineKeyboardButton("🔙 Back", callback_data="gs_home")]]
    return text, InlineKeyboardMarkup(buttons)


# ─── Command ──────────────────────────────────────────────────────────────────

@Client.on_message(filters.command("settings") & filters.group)
async def settings_cmd(client: Client, message: Message):
    chat_id = message.chat.id
    if not await is_group_admin(client, chat_id, message.from_user.id):
        return await message.reply_text("⚠️ Only group admins can use /settings.", parse_mode=ParseMode.HTML)

    text, markup = await _main_panel(chat_id)
    await message.reply_text(text, reply_markup=markup, parse_mode=ParseMode.HTML)


# ─── Callbacks ────────────────────────────────────────────────────────────────

@Client.on_callback_query(filters.regex("^gs_home$"))
async def gs_home_cb(client: Client, query: CallbackQuery):
    chat_id = query.message.chat.id
    if not await is_group_admin(client, chat_id, query.from_user.id):
        return await query.answer("Admins only!", show_alert=True)
    text, markup = await _main_panel(chat_id)
    try:
        await query.message.edit_text(text, reply_markup=markup, parse_mode=ParseMode.HTML)
    except Exception:
        pass
    await query.answer()


@Client.on_callback_query(filters.regex(r"^gs_view_\w+$"))
async def gs_view_cb(client: Client, query: CallbackQuery):
    chat_id = query.message.chat.id
    if not await is_group_admin(client, chat_id, query.from_user.id):
        return await query.answer("Admins only!", show_alert=True)
    feature = query.data[len("gs_view_"):]
    text, markup = await _feature_panel(chat_id, feature)
    try:
        await query.message.edit_text(text, reply_markup=markup, parse_mode=ParseMode.HTML)
    except Exception:
        pass
    await query.answer()


@Client.on_callback_query(filters.regex(r"^gs_toggle_[\w]+_[01]$"))
async def gs_toggle_cb(client: Client, query: CallbackQuery):
    chat_id = query.message.chat.id
    if not await is_group_admin(client, chat_id, query.from_user.id):
        return await query.answer("Admins only!", show_alert=True)

    parts   = query.data.split("_")
    value   = int(parts[-1])
    feature = "_".join(parts[2:-1])

    is_prem = feature in {f[0] for f in PREMIUM_FEATURES}
    if is_prem:
        req_plan = next((f[2] for f in PREMIUM_FEATURES if f[0] == feature), None)
        premium  = await get_premium(chat_id)
        if not premium or not plan_unlocked(premium, req_plan):
            return await query.answer("🔒 Upgrade your plan to use this feature!", show_alert=True)

    await set_group_setting(chat_id, feature, bool(value))
    await query.answer("✅ Setting updated!")
    text, markup = await _feature_panel(chat_id, feature)
    try:
        await query.message.edit_text(text, reply_markup=markup, parse_mode=ParseMode.HTML)
    except Exception:
        pass


@Client.on_callback_query(filters.regex("^gs_dn$"))
async def gs_dn_cb(client: Client, query: CallbackQuery):
    chat_id = query.message.chat.id
    if not await is_group_admin(client, chat_id, query.from_user.id):
        return await query.answer("Admins only!", show_alert=True)
    text, markup = await _dn_panel(chat_id)
    try:
        await query.message.edit_text(text, reply_markup=markup, parse_mode=ParseMode.HTML)
    except Exception:
        pass
    await query.answer()


@Client.on_callback_query(filters.regex(r"^gs_dn_toggle_[0-6]$"))
async def gs_dn_toggle_cb(client: Client, query: CallbackQuery):
    chat_id = query.message.chat.id
    if not await is_group_admin(client, chat_id, query.from_user.id):
        return await query.answer("Admins only!", show_alert=True)

    premium = await get_premium(chat_id)
    if not premium or not plan_unlocked(premium, "standard"):
        return await query.answer("🔒 Standard plan required!", show_alert=True)

    n        = int(query.data.split("_")[-1])
    settings = await get_group_settings(chat_id)
    dn       = list(settings.get("disabled_numbers", []))

    if n in dn:
        dn.remove(n)
        await query.answer(f"✅ Number {n} re-enabled!")
    else:
        if len(dn) >= 2:
            return await query.answer("🚫 Max 2 numbers can be disabled!", show_alert=True)
        dn.append(n)
        await query.answer(f"🚫 Number {n} disabled!")

    await set_group_setting(chat_id, "disabled_numbers", dn)
    text, markup = await _dn_panel(chat_id)
    try:
        await query.message.edit_text(text, reply_markup=markup, parse_mode=ParseMode.HTML)
    except Exception:
        pass
