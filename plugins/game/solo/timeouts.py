import asyncio
from pyrogram.enums import ParseMode

SOLO_TIMEOUT_BAN_MINUTES = 20


async def start_solo_timer(match, role):
    client = match.get("client")
    chat_id = match.get("chat_id")
    if not client or not chat_id:
        return

    user_id = match.get("current_bowler") if role == "bowler" else match.get("current_batter")
    name = match.get("user_cache", {}).get(user_id, role.capitalize())
    mention = f"<a href='tg://user?id={user_id}'>{name}</a>"

    await asyncio.sleep(30)
    if _already_played(match, role):
        return
    try:
        await client.send_message(
            chat_id,
            f"⏳ <b>30 seconds gone.</b>\n{mention} still thinking… This is cricket 😭",
            parse_mode=ParseMode.HTML,
        )
    except Exception:
        pass

    await asyncio.sleep(20)
    if _already_played(match, role):
        return
    try:
        await client.send_message(
            chat_id,
            f"⚠️ <b>10 seconds left!</b>\n{mention}, play NOW or face elimination!",
            parse_mode=ParseMode.HTML,
        )
    except Exception:
        pass

    await asyncio.sleep(10)
    if _already_played(match, role):
        return

    await _handle_solo_timeout(match, role)


def _already_played(match, role):
    if role == "bowler":
        return match.get("bowled", False)
    return match.get("batted", False) or not match.get("bowled", False)


async def _apply_timeout_penalty(match, role, user_id):
    """
    Apply -6 to the player's individual run score (can go negative),
    mark them as eliminated in this match, and ban them for future solo games.
    Player stays in match["players"] so the scorecard still shows their -6 score.
    """
    from plugins.game.solo import ban_solo_user

    chat_id = match.get("chat_id")

    # Deduct -6 from the player's individual run score (can go negative: 0 → -6, 2 → -4, 6 → 0)
    stats = match.setdefault("player_stats", {})
    p = stats.setdefault(user_id, {})
    current_runs = p.get("runs", 0)
    p["runs"] = current_runs - 6

    # Mark as eliminated in THIS match (kept in players list so scorecard shows -6)
    match.setdefault("eliminated_player_ids", set()).add(user_id)

    # Issue 20-minute ban from joining future solo games in this group
    ban_solo_user(chat_id, user_id, SOLO_TIMEOUT_BAN_MINUTES)


async def _handle_solo_timeout(match, role):
    client = match.get("client")
    chat_id = match.get("chat_id")
    if not client or not chat_id or match.get("phase") != "LIVE":
        return

    if "timeouts" not in match:
        return

    t_info = match["timeouts"][role]
    user_id = match.get("current_bowler") if role == "bowler" else match.get("current_batter")
    if not user_id:
        return

    name = match.get("user_cache", {}).get(user_id, role.capitalize())
    mention = f"<a href='tg://user?id={user_id}'>{name}</a>"
    fails = t_info.get("fails", 0)

    # ── Strike 1: warn, give one last chance ──────────────────────────────
    if fails == 0:
        t_info["fails"] = 1
        match["prompt_dispatched"] = False
        try:
            await client.send_message(
                chat_id,
                (
                    "🚩 <b>TIME WARNING — LAST CHANCE!</b>\n"
                    f"{mention} is freezing under pressure.\n"
                    f"⚠️ <b>Miss again = -6 runs, elimination & {SOLO_TIMEOUT_BAN_MINUTES}-min ban!</b>"
                ),
                parse_mode=ParseMode.HTML,
            )
        except Exception:
            pass
        t_info["task"] = asyncio.create_task(start_solo_timer(match, role))
        return

    # ── Strike 2: penalty + eliminate + ban ───────────────────────────────
    t_info["fails"] = 0

    await _apply_timeout_penalty(match, role, user_id)

    new_score = match.get("player_stats", {}).get(user_id, {}).get("runs", 0)
    score_display = f"{new_score}" if new_score >= 0 else f"{new_score}"

    penalty_msg = (
        "🚫 <b>TIMEOUT ELIMINATION</b>\n\n"
        f"{mention} missed twice — the clock wins!\n"
        f"🧮 <b>-6 runs penalty</b> applied → Score: <b>{score_display}</b>\n"
        f"❌ <b>Eliminated</b> from this match.\n"
        f"🔴 <b>Banned for {SOLO_TIMEOUT_BAN_MINUTES} min</b> from solo games in this group.\n"
    )

    if role == "batter":
        penalty_msg += "💨 Moving to the next batter…"
        try:
            await client.send_message(chat_id, penalty_msg, parse_mode=ParseMode.HTML)
        except Exception:
            pass
        from plugins.game.solo.engine import solo_advance_ball
        await solo_advance_ball(match, "W", credit_bowler=False)

    else:
        # Bowler eliminated — find next bowler
        from plugins.game.solo import get_next_solo_bowler
        from plugins.game.solo.state import send_solo_ball_prompt

        next_b = get_next_solo_bowler(match)
        if next_b is None:
            # No valid bowler left — end the match
            penalty_msg += "⚠️ No bowlers left. Match ends."
            try:
                await client.send_message(chat_id, penalty_msg, parse_mode=ParseMode.HTML)
            except Exception:
                pass
            from plugins.game.solo.engine import _end_solo_match
            await _end_solo_match(match, forced=True)
            return

        match["current_bowler"] = next_b
        penalty_msg += "🎳 Next bowler steps in."
        match.update({
            "bowled": False,
            "batted": False,
            "prompt_dispatched": False,
            "last_bowl": None,
            "balls_in_spell": 0,
        })
        try:
            await client.send_message(chat_id, penalty_msg, parse_mode=ParseMode.HTML)
        except Exception:
            pass
        await send_solo_ball_prompt(client, match)
