import pathlib
import sys
import json
import logging
sys.path.append(str(pathlib.Path(__file__).resolve().parent.parent.parent))
import tennisabstractscraper.models.data_objects as data_objects

DATA_DIR = pathlib.Path(__file__).resolve().parent.parent.parent / "data"
METADATA_DIR = DATA_DIR / "canonical/tennisabstract/_meta"

def build_dict(seq, key):
    return {d[key]: dict(d, index=i) for i, d in enumerate(seq)}

def parse_score(server_game_score, returner_game_score, is_tb_point):
        if not server_game_score or not returner_game_score:
            return None, None
        
        score_map = {"0": 0, "15": 1, "30": 2, "40": 3, "AD": 4}
        if is_tb_point:
            if server_game_score.isdigit():
                s = int(server_game_score or None)
            else:
                s = score_map.get(server_game_score)
            if returner_game_score.isdigit():
                r = int(returner_game_score or None)
            else:
                r = score_map.get(returner_game_score)
        else:
            # CASE 2: NORMAL GAME
            s = score_map.get(server_game_score)
            r = score_map.get(returner_game_score)
            # safety fallback
            if s is None or r is None:
                return None, None
        return s, r

def update_point_player_data(point, server_player_number, returner_player_number):
    server_player_data = PLAYERS_BY_ID.get(p.get(f"player_{server_player_number}_id"))
    returner_player_data = PLAYERS_BY_ID.get(p.get(f"player_{returner_player_number}_id"))
    point["server_country"] = server_player_data.get("country")
    point["server_dob"] = server_player_data.get("dob")
    point["server_hand"] = server_player_data.get("hand")
    point["server_backhand"] = server_player_data.get("backhand")
    point["server_country"] = server_player_data.get("country")
    point["server_player_id"] = point.get(f"player_{server_player_number}_id")
    point["server_player_rank"] = point.get(f"player_{server_player_number}_rank")
    point["server_player_seed"] = point.get(f"player_{server_player_number}_seed")
    point["server_player_entry"] = point.get(f"player_{server_player_number}_entry")
    point["returner_country"] = returner_player_data.get("country")
    point["returner_dob"] = returner_player_data.get("dob")
    point["returner_hand"] = returner_player_data.get("hand")
    point["returner_backhand"] = returner_player_data.get("backhand")
    point["returner_country"] = returner_player_data.get("country")
    point["returner_player_id"] = point.get(f"player_{returner_player_number}_id")
    point["returner_player_rank"] = point.get(f"player_{returner_player_number}_rank")
    point["returner_player_seed"] = point.get(f"player_{returner_player_number}_seed")
    point["returner_player_entry"] = point.get(f"player_{returner_player_number}_entry")
    del point[f"player_{server_player_number}_id"]
    del point[f"player_{server_player_number}_hand"]
    del point[f"player_{server_player_number}_rank"]
    del point[f"player_{server_player_number}_seed"]
    del point[f"player_{server_player_number}_entry"]
    del point[f"player_{returner_player_number}_id"]
    del point[f"player_{returner_player_number}_hand"]
    del point[f"player_{returner_player_number}_rank"]
    del point[f"player_{returner_player_number}_seed"]
    del point[f"player_{returner_player_number}_entry"]

    if point.get("best_of", None) in [None, ""]:
        print(f"Missing best of: {p}")
        matches = json.loads(server_player_data.get("matches"))
        for match_id, match in matches.items():
            charting_id = match.get("charting_id") 
            if charting_id is not None and charting_id == point.get("match_id"):
                if match.get("best_of") not in [None, ""]:
                    point["best_of"] = int(match.get("best_of"))
                else:
                    print(match_id, f"{match.get('charting_id')}")
                    quit()
    return point

def update_point_pressure_metrics(point, server_player_number, returner_player_number):
    server_sets = int(point.get(f"set_{server_player_number}") or None)
    returner_sets = int(point.get(f"set_{server_player_number}") or None)
    server_games = int(point.get(f"game_{server_player_number}") or 0)
    returner_games = int(point.get(f"game_{returner_player_number}") or 0)
    score_parts = point.get("game_score").split("-")
    server_points, returner_points = parse_score(score_parts[server_player_number - 1],score_parts[returner_player_number - 1], point.get("tb_point"))
    
    best_of = int(point.get("best_of", None) or 3) # Fallback: normalize for best-of-3
    
    # MATCH PRESSURE
    total_sets = server_sets + returner_sets
    progress_sets = total_sets / best_of
    closeness_sets = 1 - abs(server_sets - returner_sets) / 2
    elimination_sets = 1 + max(0, returner_sets - server_sets) * 0.5  # elimination pressure
    point["server_set_diff"] = server_sets - returner_sets
    # point["total_sets"] = total_sets
    point["match_pressure"] = progress_sets * closeness_sets * elimination_sets

    # SET
    total_games = server_games + returner_games
    diff_games = abs(server_games - returner_games)
    # Time component (progression)
    if total_games <= 6:
        time_pressure_games = 0.2
    elif total_games <= 10:
        time_pressure_games = 0.5
    else:
        time_pressure_games = 0.9
    if diff_games == 0:
        closeness_games = 1.0   # 5-5, 6-6 → max pressure
    elif diff_games == 1:
        closeness_games = 0.7
    else:
        closeness_games = 0.3
    # point["total_games"] = total_games
    point["server_game_diff"] = server_games - returner_games
    # point["game_abs_diff"] = diff_games
    point["set_pressure"] = time_pressure_games * closeness_games

    # GAME PRESSURE
    s = int(server_points or 0)
    r = int(returner_points or 0)
    total_points = s + r
    diff_points = abs(s - r)
    # Progress (how deep into game)
    progress_points = total_points / 6   # ~max around deuce
    # Closeness
    closeness_points = 1 - (diff_points / 4)
    point["server_point_diff"] = diff_points
    point["game_pressure"] = progress_points * closeness_points
    return point

def get_last_double_fault1(points_by_match, match_id, player_id=None, player_number=None):
    """
    Returns the most recent double fault committed by a player in a match.

    You can specify:
      - player_id (preferred, uses player_1_id / player_2_id)
      - OR player_number (1 or 2)

    Returns:
      dict (point) or None if no double fault exists
    """

    if match_id not in points_by_match:
        return None

    last_df = None
    all_dfs = []

    for p in points_by_match[match_id]:
        is_double = int(p.get("is_double") or 0)

        if not is_double:
            continue

        # Identify who committed the DF (server always commits it)
        server = int(p["server_player_number"])

        # Resolve player number if needed
        if player_number is None and player_id is not None:
            if p.get("player_1_id") == player_id:
                player_number = 1
            elif p.get("player_2_id") == player_id:
                player_number = 2
            else:
                continue

        if player_number is not None and server != player_number:
            continue

        last_df = p  # overwrite → keeps the latest one
        if p not in all_dfs:
            all_dfs.append(p)

    return last_df, all_dfs

if __name__ == "__main__":
    charting_points = data_objects.DataObjectFactory.create(DATA_DIR / "prod/charting_points.jsonl")
    PLAYERS = data_objects.JsonlDataObject(DATA_DIR / "prod/players.jsonl").data
    PLAYERS_BY_ID = build_dict(PLAYERS, "player_id")

    CHARTING_MATCHES = data_objects.JsonlDataObject(DATA_DIR / "prod/charting_matches.jsonl").data
    CHARTING_MATCHES_BY_ID = build_dict(CHARTING_MATCHES, "match_id")


    
    points_by_match = {}
    c = 0
    c_u = 0
    for _, points_batch in enumerate(charting_points):
        for p in points_batch:
            match_id = p.get("match_id")
            charting_match = CHARTING_MATCHES_BY_ID.get(match_id)
            if not charting_match:
                print(f"[FATAL] - Skipping, no charting match found: {match_id}")
                continue

            if match_id not in points_by_match:
                points_by_match[match_id] = []
            
            if p.get("match_date") is None:
                p["match_date"] = match_id.split("-")[0]

            if "best_of" not in p or p.get("best_of") in [None, ""]:
                p["best_of"] = charting_match.get("best_of", None)
            
            server_player_number = int(p.get("server_player_number"))
            returner_player_number = 1 if server_player_number == 2 else 2
            point = update_point_player_data(p, server_player_number, returner_player_number)
            point = update_point_pressure_metrics(point, server_player_number, returner_player_number)

            for k, v in point.items():
                if v in [None, [], {}]:
                    point[k] = None
                elif isinstance(v, str) and v.strip().isdigit():
                    if v.strip() == "":
                        point[k] = None
                    elif "." in v:
                        point[k] = float(v)
                    else:
                        point[k] = int(v)
            
            if point not in points_by_match[match_id]:
                points_by_match[match_id].append(point)
                c_u += 1
            c += 1
    print(f"Total Points: {c}")
    print(f"Unique Points: {c_u}")