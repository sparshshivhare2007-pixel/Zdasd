import asyncio
from pyrogram import Client

ACTIVE_MATCHES = {}

async def init_match(
    chat_id: int,
    game_id: int,
    host_id: int,
    teams: dict,
    overs: int,
    batting_team: str,
    bowling_team: str,
    striker: int,
    non_striker: int,
    bowler: int,
    client: Client = None,
    host_name: str = "Host",
):

    user_cache = {}
    all_uids = [host_id, striker, non_striker, bowler]
    for team_list in teams.values():
        all_uids.extend(team_list)

    unique_uids = list(set(all_uids))

    try:
        users = await client.get_users(unique_uids)
        for u in users:
            user_cache[u.id] = u.first_name or "Player"
    except Exception as e:
        print(f"User Cache Error: {e}")
        user_cache[host_id] = host_name

    ACTIVE_MATCHES[chat_id] = {
        "chat_id": chat_id,
        "game_id": game_id,
        "host_id": host_id,
        "host_name": user_cache.get(host_id, host_name),
        "client": client,  
        "user_cache": user_cache, 

        "overs": overs,
        "innings": 1,
        "phase": "LIVE",
        "player_count_per_team": len(teams.get("A", [])),
        "target": None,

        "bowled": False,          
        "batted": False,          
        "last_bowl": None,
        "prompt_dispatched": False,

        "batting_team": batting_team or "A",
        "bowling_team": bowling_team or "B",
        
        "current_over": 1,
        "ball_in_over": 1,
        "total_balls": 0,

        "striker": striker,
        "non_striker": non_striker,
        "current_bowler": bowler,
        "last_over_bowler": None,
        "last_over_bowler_name": "None",

        "partnership": 0, 
        "partnership_balls": 0,

        "teams": {
            "A": {
                "runs": 0, 
                "wickets": 0, 
                "balls": 0,
                "over_history": [0], 
                "players": teams.get("A", []) 
            },
            "B": {
                "runs": 0, 
                "wickets": 0, 
                "balls": 0,
                "over_history": [0], 
                "players": teams.get("B", []) 
            },
        },

        "players": {
            uid: {
                "runs": 0, 
                "balls_faced": 0, 
                "wickets": 0, 
                "runs_conceded": 0,
                "balls_bowled": 0, 
                "bowling_balls": [],
                "team": "A" if uid in teams.get("A", []) else "B",
                "is_out": False,
                "sixes_count": 0,
                "fours_count": 0,
                "has_celebrated_50": False,
                "has_celebrated_100": False
            } for uid in unique_uids
        },

        "current_over_balls": [], 
        "last_6_balls": [],     
        "warmup_done": False,
        "join_timer_task": None, 
        "timeouts": {
            "bowler": {"fails": 0, "task": None},
            "batter": {"fails": 0, "task": None},
        }
    }

    return ACTIVE_MATCHES[chat_id]
