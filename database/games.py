import uuid
import asyncio
from datetime import datetime
from database.connection import db


async def _col():
    await db.ensure_pool()
    if db.db is None:
        raise RuntimeError("Database unavailable. Please try again in a moment.")
    return db.db


async def is_game_active(chat_id: int) -> bool:
    try:
        col = (await _col())["games"]
        return await col.find_one({"chat_id": chat_id, "status": "active"}) is not None
    except Exception as e:
        print(f"[DB] is_game_active error: {e}")
        return False


async def create_game(chat_id: int, mode: str, host_id: int, title: str):
    game_id = str(uuid.uuid4())
    try:
        col = (await _col())["games"]
        await col.insert_one({
            "game_id": game_id,
            "chat_id": chat_id,
            "title": title,
            "mode": mode,
            "host_id": host_id,
            "status": "active",
            "phase": "setup",
            "winner": None,
            "team_a_runs": 0,
            "team_b_runs": 0,
            "team_a_wickets": 0,
            "team_b_wickets": 0,
            "team_a_balls": 0,
            "team_b_balls": 0,
            "team_a_penalty": 0,
            "team_b_penalty": 0,
            "target": None,
            "innings": 1,
            "motm": None,
            "toss_winner": None,
            "batting_team": None,
            "bowling_team": None,
            "overs": 0,
            "created_at": datetime.utcnow(),
        })
    except Exception as e:
        print(f"[DB] create_game error: {e}")
    return game_id


async def end_game(chat_id: int):
    try:
        col = (await _col())["games"]
        await col.update_one(
            {"chat_id": chat_id, "status": "active"},
            {"$set": {"status": "ended"}}
        )
    except Exception as e:
        print(f"[DB] end_game error: {e}")


async def get_active_game(chat_id: int):
    try:
        col = (await _col())["games"]
        return await col.find_one({"chat_id": chat_id, "status": "active"})
    except Exception as e:
        print(f"[DB] get_active_game error: {e}")
        return None


async def set_phase(chat_id: int, phase: str):
    try:
        col = (await _col())["games"]
        await col.update_one(
            {"chat_id": chat_id, "status": "active"},
            {"$set": {"phase": phase}}
        )
    except Exception as e:
        print(f"[DB] set_phase error: {e}")


async def get_phase(chat_id: int):
    try:
        col = (await _col())["games"]
        row = await col.find_one({"chat_id": chat_id, "status": "active"}, {"phase": 1})
        return row.get("phase") if row else None
    except Exception as e:
        print(f"[DB] get_phase error: {e}")
        return None


async def user_in_other_game(user_id: int, current_chat_id: int):
    try:
        database = await _col()
        player_col = database["game_players"]
        games_col = database["games"]
        player = await player_col.find_one({"user_id": user_id})
        if not player:
            return None
        game = await games_col.find_one({
            "game_id": player["game_id"],
            "chat_id": {"$ne": current_chat_id},
            "status": "active"
        })
        return game
    except Exception as e:
        print(f"[DB] user_in_other_game error: {e}")
        return None


async def get_shift_count(game_id, user_id):
    try:
        col = (await _col())["team_shifts"]
        row = await col.find_one({"game_id": str(game_id), "user_id": user_id})
        return row.get("shifts", 0) if row else 0
    except Exception as e:
        print(f"[DB] get_shift_count error: {e}")
        return 0


async def increment_shift(game_id, user_id):
    try:
        col = (await _col())["team_shifts"]
        await col.update_one(
            {"game_id": str(game_id), "user_id": user_id},
            {"$inc": {"shifts": 1}},
            upsert=True
        )
    except Exception as e:
        print(f"[DB] increment_shift error: {e}")


async def get_team_players(game_id, team: str):
    try:
        col = (await _col())["game_players"]
        cursor = col.find(
            {"game_id": str(game_id), "team": team},
            {"user_id": 1, "is_out": 1, "is_captain": 1, "role": 1}
        ).sort("joined_at", 1)
        return await cursor.to_list(length=100)
    except Exception as e:
        print(f"[DB] get_team_players error: {e}")
        return []


async def update_team_penalty(game_id, team: str, amount: int = 6):
    field = "team_a_penalty" if team == "A" else "team_b_penalty"
    try:
        col = (await _col())["games"]
        await col.update_one(
            {"game_id": str(game_id)},
            {"$inc": {field: amount}}
        )
    except Exception as e:
        print(f"[DB] update_team_penalty error: {e}")


async def increment_user_penalty_count(user_id: int):
    try:
        col = (await _col())["user_stats"]
        await col.update_one(
            {"user_id": user_id},
            {"$inc": {"penalties_received": 1}},
            upsert=True
        )
    except Exception as e:
        print(f"[DB] increment_user_penalty_count error: {e}")


async def save_match_result(conn, match, winner, motm_id):
    try:
        col = db.db["games"]
        await col.update_one(
            {"game_id": str(match["game_id"])},
            {"$set": {
                "winner": winner,
                "team_a_runs": match["teams"]["A"]["runs"],
                "team_a_wickets": match["teams"]["A"]["wickets"],
                "team_b_runs": match["teams"]["B"]["runs"],
                "team_b_wickets": match["teams"]["B"]["wickets"],
                "team_a_penalty": match["teams"]["A"].get("penalty", 0),
                "team_b_penalty": match["teams"]["B"].get("penalty", 0),
                "motm": motm_id,
                "status": "ended",
                "phase": "finished",
            }}
        )
    except Exception as e:
        print(f"[DB] save_match_result error: {e}")
