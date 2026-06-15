from utils.mentions import mention_html
import random
import html


def format_player_line(name, runs, balls, bowling=None, is_striker=False):
    safe_name = html.escape(name)
    star = " 🏏" if is_striker else ""
    line = f"✧ <b>{safe_name}</b>{star} = {runs} ({balls}b)"
    if bowling and len(bowling) > 0:
        balls_str = " • ".join(map(str, bowling))
        line += f"\n╰⊚ ʙᴏᴡʟɪɴɢ: ({balls_str})"
    else:
        line += "\n╰⊚ ʙᴏᴡʟɪɴɢ: Yet to bowl"
    return line


def _eco(r, b):
    if not b:
        return "—"
    return f"{r / b * 6:.1f}"


async def build_over_summary(client, match):
    bat_team_key = match.get("batting_team", "A")
    bowl_team_key = match.get("bowling_team", "B")
    user_cache = match.get("user_cache", {})

    striker_id = match.get("striker")
    non_striker_id = match.get("non_striker")

    team_balls = match.get("teams", {}).get(bat_team_key, {}).get("balls", 0)
    completed_over = team_balls // 6

    partnership_runs = match.get("partnership", 0)
    partnership_balls = match.get("partnership_balls", 0)

    next_bowler_id = match.get("current_bowler")
    raw_bowler = user_cache.get(next_bowler_id, "TBD") if next_bowler_id else "TBD"
    next_bowler_name = html.escape(raw_bowler)

    recent_list = match.get("current_over_balls", [])
    recent = " • ".join(str(b) for b in recent_list) if recent_list else "—"

    raw_next_batter = user_cache.get(striker_id, "TBD")
    next_batter = html.escape(raw_next_batter)
    safe_host = html.escape(match.get("host_name", "Admin"))

    def team_line(t_key):
        t = match.get("teams", {}).get(t_key, {"runs": 0, "wickets": 0, "balls": 0})
        r, w, b = t.get("runs", 0), t.get("wickets", 0), t.get("balls", 0)
        ov = f"{b // 6}.{b % 6}"
        icon = "🌊" if t_key == "A" else "🔥"
        return f"{icon} <b>Team {t_key}:</b> {r}/{w} ({ov}ov)"

    def player_line(uid):
        p = match.get("players", {}).get(uid, {})
        if not p:
            return None
        name = html.escape(user_cache.get(uid, "Player"))
        runs = p.get("runs", 0)
        balls_f = p.get("balls_faced", 0)
        r_con = p.get("runs_conceded", 0)
        b_bow = p.get("balls_bowled", 0)
        eco = _eco(r_con, b_bow)
        tag = " 🏏" if uid == striker_id else (" 🏃" if uid == non_striker_id else "")
        out = " ◼" if p.get("is_out") else ""
        bat_line = f"• {name}{tag}{out}: <b>{runs}</b>({balls_f}b)"
        bowl_part = f" | Eco {eco}" if b_bow > 0 else ""
        return bat_line + bowl_part

    bat_team_data = match.get("teams", {}).get(bat_team_key, {})
    team_players = bat_team_data.get("players", [])

    player_lines = []
    for uid in team_players:
        if uid in [striker_id, non_striker_id] or match.get("players", {}).get(uid, {}).get("balls_faced", 0) > 0:
            line = player_line(uid)
            if line:
                player_lines.append(line)

    lines = [
        f"📋 <b>Over {completed_over} Summary</b>",
        "────╌╌┄┄┈───",
        team_line("A"),
        team_line("B"),
        "────╌╌┄┄┈───",
    ]

    if player_lines:
        lines.append(f"🏏 <b>Batting (Team {bat_team_key}):</b>")
        lines.extend(player_lines)

    lines += [
        "────╌╌┄┄┈───",
        f"🕒 Last Over: <code>[ {recent} ]</code>",
        f"🤝 Partnership: <b>{partnership_runs}</b> ({partnership_balls}b)",
        f"👉 On Strike: {next_batter}",
        f"🎙 Host: {safe_host}",
    ]

    return "\n".join(lines)


async def build_innings_summary(client, match):
    finished_team_key = "A" if match.get("batting_team") == "B" else "B"
    new_batting_team = match.get("batting_team", "A")

    data = match["teams"].get(finished_team_key, {"runs": 0, "wickets": 0, "players": []})
    user_cache = match.get("user_cache", {})
    target = match.get("target", "N/A")

    lines = [
        f"🏁 <b>ɪɴɴɪɴɢs ᴄᴏᴍᴘʟᴇᴛᴇᴅ</b>",
        "× •-•-•-••-•-•⟮ 🏏 ⟯•-•-•-•-•-•-• ×\n",
        f"🏏 <b>Tᴇᴀᴍ {finished_team_key} Fɪɴᴀʟ Sᴄᴏʀᴇ: {data.get('runs', 0)}/{data.get('wickets', 0)}</b> ⊰─\n"
    ]

    team_players = data.get("players", [])

    if not team_players:
        lines.append("✧ <i>No player stats available</i>")
    else:
        player_lines = []
        for uid in team_players:
            p = match.get("players", {}).get(uid, {})
            if not p:
                continue
            p_name = user_cache.get(uid, "Player")
            player_lines.append(format_player_line(p_name, p.get("runs", 0), p.get("balls_faced", 0), p.get("bowling_balls", [])))

        lines.append("\n\n".join(player_lines))

    lines.append("\n× •-•-•-•-•-••-•-•⟮ 🎯 ⟯•-•-•-•-•-•-•-•-• ×\n")
    lines.append(f"🎯 <b>ᴛᴀʀɢᴇᴛ sᴇᴛ: {target} ʀᴜɴs</b>\n")
    lines.append(f"🔄 <b>sᴡɪᴛᴄʜɪɴɢ sɪᴅᴇs...</b>")
    lines.append(f"ᴛᴇᴀᴍ <b>{new_batting_team}</b> captain, use <code>/batting</code>\n")
    lines.append("─────⊱◈◈◈⊰─────")

    return "\n".join(lines)


async def build_match_summary(client, match, winner):
    if winner == "Tie":
        return "🤝 <b>ᴍᴀᴛᴄʜ ᴛɪᴇᴅ!</b>\n\nWhat a spectacular finish! Both teams played brilliantly."

    user_cache = match.get("user_cache", {})
    res = [
        "🏆 <b>ᴍᴀᴛᴄʜ ᴄᴏɴᴄʟᴜᴅᴇᴅ</b> 🏆",
        f"✨ <b>ᴡɪɴɴᴇʀ: ᴛᴇᴀᴍ {winner}</b>\n",
        "× •-•-•-••-•-•⟮ 📊 ⟯•-•-•-•-•-•-• ×"
    ]

    motm_name = "N/A"
    motm_score = -1

    for t_key in ["A", "B"]:
        t_data = match["teams"].get(t_key, {"runs": 0, "wickets": 0, "players": []})
        emoji = "🅰️" if t_key == "A" else "🅱️"
        res.append(f"\n{emoji} <b>ᴛᴇᴀᴍ {t_key}: {t_data.get('runs', 0)}/{t_data.get('wickets', 0)}</b>")

        team_players = {uid: match["players"].get(uid, {}) for uid in t_data.get("players", []) if uid in match.get("players", {})}

        if team_players:
            best_bat_id = max(team_players, key=lambda x: team_players[x].get("runs", 0), default=None)
            if best_bat_id:
                bb = team_players[best_bat_id]
                safe_bat = html.escape(user_cache.get(best_bat_id, "Player"))
                res.append(f"🔥 <b>ʙᴇsᴛ ʙᴀᴛᴛᴇʀ:</b> {safe_bat}")
                res.append(f"╰ {bb.get('runs', 0)} runs ({bb.get('balls_faced', 0)}b)")

            best_bowl_id = max(team_players, key=lambda x: (team_players[x].get("wickets", 0), -team_players[x].get("runs_conceded", 999)), default=None)
            if best_bowl_id and team_players[best_bowl_id].get("wickets", 0) > 0:
                bw = team_players[best_bowl_id]
                safe_bowl = html.escape(user_cache.get(best_bowl_id, "Player"))
                res.append(f"💎 <b>ʙᴇsᴛ ʙᴏᴡʟᴇʀ:</b> {safe_bowl}")
                res.append(f"╰ {bw.get('wickets', 0)} wkts | {bw.get('runs_conceded', 0)} runs | Eco: {_eco(bw.get('runs_conceded', 0), bw.get('balls_bowled', 0))}")

            for uid, p in team_players.items():
                p_score = p.get("runs", 0) + (p.get("wickets", 0) * 25)
                if p_score > motm_score:
                    motm_score = p_score
                    raw_motm = user_cache.get(uid, "Player")
                    motm_name = html.escape(raw_motm)

    res.append("\n× •-•-•-••-•-•⟮ 🎖 ⟯•-•-•-•-•-•-• ×")
    res.append(f"\n🎖 <b>ᴍᴀɴ ᴏғ ᴛʜᴇ ᴍᴀᴛᴄʜ</b>")
    res.append(f"🌟 <b>{motm_name}</b> ({motm_score} pts)")
    res.append("\n─────⊱◈◈◈⊰─────")
    res.append("ᴛʜᴀɴᴋs ғᴏʀ ᴘʟᴀʏɪɴɢ! 🎉")

    return "\n".join(res)
