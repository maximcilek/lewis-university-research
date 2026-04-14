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


def get_last_double_fault(points_by_match, match_id, player_id=None, player_number=None):
    """
    Returns last double fault for a player in a match.

    FIXES:
    - resolves player identity ONCE (not per point)
    - avoids state contamination bug
    """

    if match_id not in points_by_match:
        return None

    points = points_by_match[match_id]

    def norm(x):
        return str(x).strip().lower() if x is not None else None

    # -----------------------------
    # STEP 1: resolve player_number ONCE
    # -----------------------------
    if player_number is None and player_id is not None:

        player_id = norm(player_id)

        sample = points[0]  # safe because match exists

        p1 = norm(sample.get("player_1_id"))
        p2 = norm(sample.get("player_2_id"))

        if player_id == p1:
            player_number = 1
        elif player_id == p2:
            player_number = 2
        else:
            return None  # player not in match

    # -----------------------------
    # STEP 2: scan for last DF
    # -----------------------------
    last_df = None

    for p in points:

        if int(p.get("is_double") or 0) != 1:
            continue

        server = int(p["server_player_number"])

        if player_number is not None and server != player_number:
            continue

        last_df = p

    return last_df


def update_double_faults_structure(p, players_map, charting_matches_map):
    def get_game_state(server, returner):
        diff = int(server or 0) - int(returner or 0)
        if diff >= 2:
            return 2
        elif diff == 1:
            return 1
        elif diff == 0:
            return 0
        elif diff == -1:
            return -1
        else:
            return -2

    def game_pressure(server_points, returner_points):
        s = int(server_points or 0)
        r = int(returner_points or 0)
        total = s + r
        diff = abs(s - r)
        # Progress (how deep into game)
        progress = total / 6   # ~max around deuce
        # Closeness
        closeness = 1 - (diff / 4)
        return progress * closeness
    
    def set_pressure(p):
        g1 = int(p.get("game_1") or 0)
        g2 = int(p.get("game_2") or 0)

        server = int(p.get("server_player_number"))

        # Align to server
        if server == 1:
            server_games = g1
            returner_games = g2
        else:
            server_games = g2
            returner_games = g1

        total = server_games + returner_games
        diff = abs(server_games - returner_games)

        # -----------------------------
        # Time component (progression)
        # -----------------------------
        if total <= 6:
            time_pressure = 0.2
        elif total <= 10:
            time_pressure = 0.5
        else:
            time_pressure = 0.9

        # -----------------------------
        # Tightness component
        # -----------------------------
        if diff == 0:
            closeness = 1.0   # 5-5, 6-6 → max pressure
        elif diff == 1:
            closeness = 0.7
        else:
            closeness = 0.3

        # -----------------------------
        # Combine
        # -----------------------------
        return time_pressure * closeness
    
    def match_pressure(p):
        p1_sets = int(p.get("set_1") or 0)
        p2_sets = int(p.get("set_2") or 0)
        server = int(p.get("server_player_number"))
        if server == 1:
            s = p1_sets
            r = p2_sets
        else:
            s = p2_sets
            r = p1_sets
        total = s + r
        # normalize for best-of-3
        progress = total / 3
        closeness = 1 - abs(s - r) / 2
        # elimination pressure
        elimination = 1 + max(0, r - s) * 0.5
        return progress * closeness * elimination
    
    def parse_score(p, server_game_score, returner_game_score):

        if not server_game_score or not returner_game_score:
            return None, None

        server = int(p.get("server_player_number"))

        # -----------------------------
        # Detect tiebreak safely
        # -----------------------------
        is_tb = p.get("tb_point") == 1

        # also fallback: both are numeric
        if not is_tb:
            if server_game_score.isdigit() and returner_game_score.isdigit():
                is_tb = True

        # -----------------------------
        # CASE 1: TIEBREAK
        # -----------------------------
        if is_tb:
            s = int(server_game_score)
            r = int(returner_game_score)
            return s, r  # already server-relative

        # -----------------------------
        # CASE 2: NORMAL GAME
        # -----------------------------
        score_map = {
            "0": 0,
            "15": 1,
            "30": 2,
            "40": 3,
            "AD": 4
        }

        s = score_map.get(server_game_score)
        r = score_map.get(returner_game_score)

        # safety fallback
        if s is None or r is None:
            return None, None

        return s, r

    first_serve = {"serve_number": 1, "is_double": 0, "first_serve_rally": p.get("first_serve_rally"), "first_serve_in_play": p.get("first_serve_in_play")}
    second_serve = {"serve_number": 2, "is_double": p.get("is_double"), "second_serve_rally": p.get("second_serve_rally"), "second_serve_in_play": p.get("second_serve_in_play")}
    result = {}
    
    charting_match = charting_matches_map.get(p.get("match_id"))
    if charting_match is None:
        raise Exception(f"Expected a Charting Match Record: {p}")

    server_player_number = int(p.get("server_player_number"))
    returner_player_number = 1 if int(server_player_number) == 2 else 2
    result["match_id"] = p.get("match_id")
    result["match_date"] = charting_match.get("match_date", None)
    result["best_of"] = charting_match.get("best_of", None)
    result["match_duration"] = charting_match.get("time", None)
    result["surface"] = charting_match.get("surface", None)
    result["surface"] = p.get("surface")
    result["match_duration"] = p.get("match_duration")
    result["level"] = p.get("level")
    result[f"server_sets"] = p.get(f"set_{server_player_number}")
    result[f"returner_sets"] = p.get(f"set_{returner_player_number}")
    result[f"server_games"] = p.get(f"game_{server_player_number}")
    result[f"returner_games"] = p.get(f"game_{returner_player_number}")
    result[f"game_state"] = get_game_state(result.get("server_games"), result.get("returner_games"))
    result["game_score"] = p.get("game_score")
    result["point_number"] = p.get("point_number")
    result["game_number"] = p.get("game_number")
    result["is_tiebreaker_set"] = p.get("is_tiebreaker_set")
    result["tb_point_number"] = p.get("tb_point_number")
    result["tb_point"] = p.get("tb_point")
    result["is_ace"] = p.get("is_ace")
    result["is_unret"] = p.get("is_unret")
    result["is_forced_error"] = p.get("is_forced_error")
    result["is_unforced_error"] = p.get("is_unforced_error")
    result["gender"] = p.get("gender")
    result[f"match_pressure"] = match_pressure(p)   
    result[f"set_pressure"] = set_pressure(p)   
    result["game_pressure"] = ((int(result.get("server_games")) + int(result.get("returner_games"))) / 12) * ((1 - abs(int(result.get("server_games")) + int(result.get("returner_games")))) / 6)
    result["server_set_diff"] = int(p.get(f"set_{server_player_number}")) - int(p.get(f"set_{returner_player_number}"))
    result["total_sets_played"] = int(p.get(f"set_{server_player_number}")) + int(p.get(f"set_{returner_player_number}"))
    server_player_data = players_map.get(p.get(f"player_{server_player_number}_id"))
    server_info = {
        "server_player_number": server_player_number, # 1 / 2
        "server_player_id": p.get(f"player_{server_player_number}_id"),
        "server_player_rank": p.get(f"player_{server_player_number}_rank"),
        "server_player_seed": p.get(f"player_{server_player_number}_seed"),
        "server_player_entry": p.get(f"player_{server_player_number}_entry"),
        "server_player_country": server_player_data.get("country", None),
        "server_player_hand": server_player_data.get("hand", None),
        "server_player_backhand": server_player_data.get("backhand", None),
        "server_player_height": server_player_data.get("ht", None),
        "server_player_dob": server_player_data.get("dob", None)
    }
    score_parts = result.get("game_score").split("-")
    sscore, rscore = parse_score(p, score_parts[server_player_number - 1],score_parts[returner_player_number - 1])
    result["server_score"] = sscore
    result["returner_score"] = rscore
    result.update(server_info)

    first_serve.update(result)
    second_serve.update(result)
    return first_serve, second_serve




def log_json(data):
    print(f"======================================================")
    print(f"JSON DATA")
    print(f"======================================================")
    print(json.dumps(data, indent=4))

if __name__ == "__main__":
    charting_points = data_objects.DataObjectFactory.create(DATA_DIR / "prod/charting_points.jsonl")
    PLAYERS = data_objects.JsonlDataObject(DATA_DIR / "prod/players.jsonl").data
    PLAYERS_BY_ID = build_dict(PLAYERS, "player_id")

    CHARTING_MATCHES = data_objects.JsonlDataObject(DATA_DIR / "prod/charting_matches.jsonl").data
    CHARTING_MATCHES_BY_ID = build_dict(CHARTING_MATCHES, "match_id")
    
    
    points_by_match = {}
    double_faults = {}
    df = 0
    up = []
    c = 0
    dupes = 0
    for _, points_batch in enumerate(charting_points):
        for p in points_batch:
           
            if p.get("match_id") not in points_by_match:
                points_by_match[p.get("match_id")] = []
            points_by_match[p.get("match_id")].append(p)
            
            if int(p.get("is_double") or 0):
                if p.get("match_id") not in double_faults:
                    double_faults[p.get("match_id")] = []
                
                if p not in double_faults[p.get("match_id")]:
                    first_serve, second_serve = update_double_faults_structure(p, PLAYERS_BY_ID,CHARTING_MATCHES_BY_ID)
                    double_faults[p.get("match_id")].append(first_serve)
                    double_faults[p.get("match_id")].append(second_serve)
                    df += 1
                else:
                    dupes += 1
            c += 1

            
            # log_json(p)
    print(f"Found {df} Unique Points ({dupes} duplicates) out of {c}")
    df_features = []
    for match_id, match_points in double_faults.items():
        
        last, all_dfs = get_last_double_fault1(points_by_match, match_id, match_points[0].get("server_player_id"))
        # points = sorted(all_dfs, key=lambda p: int(p.get("point_number") or 0))

        if all_dfs is not None and len(all_dfs) > 0:
            df_points = sorted(all_dfs, key=lambda p: int(p.get("point_number") or 0))
            df_point_numbers = [int(p.get("point_number") or 0) for p in df_points]
            df_index_map = {int(p.get("point_number") or 0): i for i, p in enumerate(df_points)}
            match_points = sorted(match_points, key=lambda p: int(p.get("point_number") or 0))
            prev_df_point = None
            prev_df_game = None
            prev_df_set = None
            rows = []
            for point in match_points:
                pn = int(point.get("point_number") or 0)
                gn = int(point.get("game_number") or 0)
                sn = int(point.get(f"total_sets_played") or 0)
                is_double = int(point.get("is_double") or 0)

                point_lag = pn - prev_df_point if prev_df_point is not None else None
                game_lag = gn - last_df_game if last_df_game is not None else None
                set_lag = sn - last_df_set if last_df_set is not None else None

                dist = None if prev_df_point is None else pn - prev_df_point

                feature_row = {
                    # ---------------- MATCH CONTEXT ----------------
                    "match_id": match_id,
                    "match_date": point.get("match_date"),
                    "surface": point.get("surface"),
                    "level": point.get("level"),
                    "gender": point.get("gender"),
                    "best_of": point.get("best_of"),
                    "match_duration": point.get("match_duration"),

                    # ---------------- SERVER ----------------
                    "server_player_id": point.get("server_player_id"),
                    "server_player_number": point.get("server_player_number"),
                    "server_rank": point.get("server_player_rank"),
                    "server_seed": point.get("server_player_seed"),
                    "server_country": point.get("server_player_country"),
                    "server_hand": point.get("server_player_hand"),
                    "server_backhand": point.get("server_player_backhand"),
                    "server_height": point.get("server_player_height"),

                    # ---------------- MATCH STATE ----------------
                    "server_sets": point.get("server_sets"),
                    "returner_sets": point.get("returner_sets"),
                    "server_games": point.get("server_games"),
                    "returner_games": point.get("returner_games"),
                    "game_state": point.get("game_state"),
                    "game_score": point.get("game_score"),
                    "server_score": point.get("server_score"),
                    "returner_score": point.get("returner_score"),
                    "total_sets_played": sn,
                    "is_tiebreaker_set": point.get("is_tiebreaker_set"),
                    "tb_point_number": point.get("tb_point_number"),
                    "tb_point": point.get("tb_point"),

                    # ---------------- PRESSURE ----------------
                    "match_pressure": point.get("match_pressure"),
                    "set_pressure": point.get("set_pressure"),
                    "game_pressure": point.get("game_pressure"),
                    "server_set_diff": point.get("server_set_diff"),

                    # ---------------- SERVE OUTCOME ----------------
                    "serve_number": point.get("serve_number"),
                    "first_serve_rally": point.get("first_serve_rally"),
                    "first_serve_in_play": point.get("first_serve_in_play"),
                    "is_ace": point.get("is_ace"),
                    "is_unret": point.get("is_unret"),
                    "is_forced_error": point.get("is_forced_error"),
                    "is_unforced_error": point.get("is_unforced_error"),

                    # ---------------- TARGET ----------------
                    "is_double": is_double,

                    # ---------------- TEMPORAL FEATURES ----------------
                    "point": pn,
                    "game": gn,
                    "set": sn,
                    "distance_from_last_df": None if last_df_point is None else pn - last_df_point,
                    "point_lag": point_lag,
                    "game_lag": game_lag,
                    "set_lag": set_lag,
                    "last_df_point": last_df_point,
                }

                rows.append(feature_row)
                # -------------------------
                # UPDATE STATE (after)
                # -------------------------
                if is_double == 1:
                    prev_df_point = pn
                    last_df_game = gn
                    last_df_set = sn
            df_features.extend(rows)
    print(f"DF Features: {len(df_features)}")
    with open(DATA_DIR / "analysis/double_faults.jsonl", "w", encoding="utf-8") as f:
        for feature in df_features:
            f.write(json.dumps(feature, ensure_ascii=False) + "\n")