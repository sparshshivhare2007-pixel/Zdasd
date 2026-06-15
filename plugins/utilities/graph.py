import asyncio
import time
import io
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from concurrent.futures import ThreadPoolExecutor
from pyrogram import Client, filters
from plugins.game.team import ACTIVE_MATCHES

GRAPH_COOLDOWN = {}
_EXECUTOR = ThreadPoolExecutor(max_workers=2)


def _build_graph_sync(match_snapshot):
    overs_limit = int(match_snapshot.get("overs", 5))

    def build_over_worm(team_key):
        team = match_snapshot["teams"].get(team_key, {})
        balls = int(team.get("balls", 0) or 0)
        if balls <= 0:
            return [], []
        per_ball = team.get("over_history", [])
        usable = min(len(per_ball), balls)
        padded = per_ball[:usable] + [0] * max(0, balls - usable)
        overs, cumulative, total, ball_no = [], [], 0, 0
        for r in padded:
            ball_no += 1
            total += r
            overs.append(ball_no / 6)
            cumulative.append(total)
        return overs, cumulative

    plt.style.use("dark_background")
    fig, ax = plt.subplots(figsize=(9, 4))

    xa, ya = build_over_worm("A")
    if xa:
        ax.plot(xa, ya, lw=2.5, color="#ff4c4c", label="Team A")

    xb, yb = build_over_worm("B")
    if xb:
        ax.plot(xb, yb, lw=2.5, color="#4da6ff", label="Team B")

    if match_snapshot.get("innings") == 2 and match_snapshot.get("target"):
        target = int(match_snapshot["target"])
        ax.axhline(target, ls="--", lw=1.8, color="gold", alpha=0.8, label=f"Target {target}")

        bat_team = match_snapshot["teams"].get(match_snapshot.get("batting_team"), {})
        runs_now = int(bat_team.get("runs", 0) or 0)
        balls_now = int(bat_team.get("balls", 0) or 0)
        balls_left = max(0, overs_limit * 6 - balls_now)
        runs_left = max(0, target - runs_now)

        if balls_left > 0 and runs_left > 0 and balls_now > 0:
            req_rr = (runs_left / balls_left) * 6
            cur_rr = (runs_now / balls_now) * 6
            win_prob = max(0, min(100, 50 + (cur_rr - req_rr) * 8))
        else:
            win_prob = 100 if runs_now >= target else 0

        ax.text(0.99, 0.95, f"Win % : {int(win_prob)}%",
                transform=ax.transAxes, ha="right", va="top",
                fontsize=10, color="gold", weight="bold")

    ax.set_title("CRICKET WORM", fontsize=12, weight="bold")
    ax.set_xlabel("Overs", fontsize=9)
    ax.set_ylabel("Runs", fontsize=9)
    ax.set_xlim(0, overs_limit)
    ax.set_xticks(range(0, overs_limit + 1))
    ax.grid(True, alpha=0.2)
    ax.legend(loc="upper left", fontsize=9)
    ax.tick_params(labelsize=8)
    fig.tight_layout(pad=1.0)

    buf = io.BytesIO()
    plt.savefig(buf, dpi=110, bbox_inches="tight")
    buf.seek(0)
    plt.close(fig)
    return buf


async def get_graph_buffer(match):
    snapshot = {
        "overs": match.get("overs", 5),
        "innings": match.get("innings", 1),
        "target": match.get("target"),
        "batting_team": match.get("batting_team"),
        "teams": {
            k: {
                "balls": v.get("balls", 0),
                "runs": v.get("runs", 0),
                "over_history": list(v.get("over_history", [])),
            }
            for k, v in match.get("teams", {}).items()
        },
    }
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(_EXECUTOR, _build_graph_sync, snapshot)


@Client.on_message(filters.command("graph") & filters.private)
async def graph_dm_redirect(client, message):
    await message.reply_text(
        "📊 <b>/graph only works in a group</b> where a live team match is running.\n\n"
        "Use it in the group chat to see the score worm chart.",
        parse_mode="html",
    )


@Client.on_message(filters.command("graph") & filters.group)
async def score_graph(client, message):
    chat_id = message.chat.id
    now = time.time()

    if chat_id in GRAPH_COOLDOWN and (now - GRAPH_COOLDOWN[chat_id]) < 10:
        return await message.reply_text("⏳ <b>Cooldown active.</b>", parse_mode="html")

    match = ACTIVE_MATCHES.get(chat_id)
    if not match:
        return await message.reply_text("❌ <b>No active match.</b>", parse_mode="html")

    GRAPH_COOLDOWN[chat_id] = now
    buf = await get_graph_buffer(match)

    a_runs, a_wick = match["teams"]["A"]["runs"], match["teams"]["A"]["wickets"]
    b_runs, b_wick = match["teams"]["B"]["runs"], match["teams"]["B"]["wickets"]

    caption = (
        f"📊 <b>𝗦𝗖𝗢𝗥𝗘 𝗣𝗥𝗢𝗚𝗥𝗘𝗦𝗦𝗜𝗢𝗡</b>\n"
        "────┈┄┄╌╌╌╌┄┄┈────\n"
        f"🔴 <b>Team A:</b> <code>{a_runs}/{a_wick}</code>\n"
        f"🔵 <b>Team B:</b> <code>{b_runs}/{b_wick}</code>\n"
        "────┈┄┄╌╌╌╌┄┄┈────"
    )

    await message.reply_photo(photo=buf, caption=caption, parse_mode="html")
