import pandas as pd
import pathlib
import numpy as np
from collections import defaultdict, deque
from itertools import zip_longest
import json
import re
import sys
sys.path.append(str(pathlib.Path(__file__).resolve().parent.parent.parent))
import tennisabstractscraper.models.data_objects as data_objects
import pyarrow.parquet as pq
IGNORED_TOURNAMENT_TYPES = ("Olympics", "Hobart", "Birmingham", "Fort_Worth", "Cancun", "ITF_Midland", "United_Cup", "Davis_Cup", "Laver_Cup", "BJK_", "Fed_Cup",
                            "Pepsi_Grand_Slam", "WITC_Hilton_Head", "_WCT", "Wembley", "Virginia_Slims_Championships") # "Tour_Championships" "_Indoor", "_Outdoor", 
UNIQUE_TOUNRNS = []

def load_points(filenames):
    result = []
    for f in filenames:
        charting_points = data_objects.DataObjectFactory.create(f)
        result.extend(charting_points.data)
    return result

def build_match_point_dict(seq, key):
    grouped = defaultdict(dict)
    for i, d in enumerate(seq):
        match_id = d[key]
        point_num = int(d["Pt"])   # your point number field
        grouped[match_id][point_num] = dict(d, index=i)
    return dict(grouped)

def load_charting_matches(filename):
    charting_matches = data_objects.DataObjectFactory.create(filename).data
    results = []
    for batch in charting_matches:
        for _, match in batch.to_pandas().iterrows():
            results.append(match.to_dict())
    return results

def build_dict(seq, key):
    return {d[key]: dict(d, index=i) for i, d in enumerate(seq)}

def rename_point_keys(point, prev, match):
    server_num = int(point["Svr"])
    returner_num = 2 if server_num == 1 else 1

    point["point_number"] = point["Pt"]
    point["server_sets"] = point[f"Set{server_num}"]
    point["returner_sets"] = point[f"Set{returner_num}"]
    point["server_games"] = point[f"Gm{server_num}"]
    point["returner_games"] = point[f"Gm{returner_num}"]
    point["game_number"] = point["Gm#"]
    # point["is_tb_set"] = point["TbSet"]
    point["server_player_number"] = point["Svr"]
    point["returner_player_number"] = returner_num
    point["first_serve_rally"] = point["1st"]
    point["second_serve_rally"] = point["2nd"]
    point["notes"] = point["Notes"]
    point["point_winner_player_number"] = point["PtWinner"]
    for c in ["Pt", "Svr", "Set1", "Set2", "Gm1", "Gm2", "Gm#", "TbSet", "1st", "2nd", "Notes", "PtWinner"]:
        del point[c]
    for c in ["point_number", "server_sets", "returner_sets", "server_games", "returner_games", "game_number", "server_player_number", "point_winner_player_number"]:
        if point[c] is not None and point[c].isdigit():
            point[c] = int(point[c])
        elif c == "game_number":
            # Infer game number from previous point
            if point["server_sets"] == prev["server_sets"] and point["returner_sets"] == prev["returner_sets"] and point["server_games"] == prev["server_games"] and point["returner_games"] == prev["returner_games"]:
                point["game_number"] = prev["game_number"]
            else:
                print("Failed to update game_number")
                print(json.dumps(prev, indent=4))
                print(json.dumps(point, indent=4))
                quit()
        elif c == "server_games":
            try:
                if point["game_number"] not in [None, ""] and prev["game_number"] not in [None, ""] and point["game_number"] == prev["game_number"]:
                    point["server_games"] = prev["server_games"]
            except:
                print("Failed to update server_games")
                print(json.dumps(point, indent=4))
                print(json.dumps(prev, indent=4))
                quit()
        elif c == "returner_games":
            try:
                if point["game_number"] not in [None, ""] and prev["game_number"] not in [None, ""] and point["game_number"] == prev["game_number"]:
                    point["returner_games"] = prev["returner_games"]
            except:
                print("Failed to update returner_games")
                print(json.dumps(point, indent=4))
                print(json.dumps(prev, indent=4))
                quit()
        else:
            print(f"Failed to cast point key to integer ({c}): {point}\n{prev}")
            quit()
    for k, v in point.items():
        if isinstance(v, str) and v.strip() == "":
            point[k] = None
    if point["point_winner_player_number"] == server_num:
        point["is_server_point_winner"] = 1
    elif point["point_winner_player_number"] == returner_num:
        point["is_server_point_winner"] = 0
    else:
        print(f"UNKNOWN PLAYER POINT WINNER NUMBER: {point} - {server_num} - {returner_num}")
        quit()
    return point

def get_official_score(match):
    score = match.get("score")
    match_score = match.get("match_score")

    candidates = []

    if pd.notna(score):
        candidates.append(("score", str(score).strip()))

    if pd.notna(match_score):
        candidates.append(("match_score", str(match_score).strip()))
    
    if len(candidates) == 2:
        if score != match_score:
            set_scores = score.split(" ")
            match_set_scores = match_score.split(" ")
            new_official_score_parts = []
            for set_score, match_set_score in zip_longest(set_scores, match_set_scores):
                if set_score and match_set_score:
                    if "(" in match_set_score:
                        new_official_score_parts.append(match_set_score)
                    else:
                        new_official_score_parts.append(set_score)
                else:
                    new_official_score_parts.append(set_score or match_set_score)
            return (" ".join(new_official_score_parts))
        else:
            return max(candidates, key=lambda x: (len(x[1].split()), x[0] == "score"), default=(None, None))[1]
    elif len(candidates) == 1:
        return candidates[0][1]
    else:
        print(f"Failed to find match score candidates: {match}")
        quit()

    #return official_score
    # return merge_scores(score, match_score)

def get_set_info(m):
    official_score = get_official_score(m)
    set_scores_info = {}
    m["official_score"] = official_score
    set_scores = official_score.split(" ")
    for set_num, set_score in enumerate(set_scores):
        s1 = re.sub(r"\[(\d+-\d+|\*)\]", r"\1", re.sub(r"\(\d+\)", "", set_score))
        nums = [int(x) for x in re.findall(r"\d+", s1)]
        set_scores_info[f"{set_num+1}"] = {
            "set_score_raw": set_score,
            "set_score": s1,
            "is_super_tb_set": 0,
            "is_tb_set": 0,
            "diff": abs(nums[0]-nums[1]),
            "official_score": official_score,
            "match_score": m["match_score"],
            "raw_match_score": m["score"],
            "is_final_set": 0
        }
        if "[" in set_score or "]" in set_score:
            set_scores_info[f"{set_num+1}"]["is_super_tb_set"] = 1
        elif "(" in set_score or ")" in set_score:
            set_scores_info[f"{set_num+1}"]["is_tb_set"] = 1
    if set_scores_info:
        last_set_key = str(len(set_scores))
        set_scores_info[f"{last_set_key}"]["is_final_set"] = 1
    return set_scores_info

def get_regular_set_tb_rule(tournament):
    if tournament == "NextGen":
        return {"trigger": 3, "target": 7}
    # Masters 1000, ATP 500/250, WTA 1000/500/250, Challengers (_CH), ITFs (ITF_), Davis Cup / BJK Cup (modern standard format)
    return {"trigger": 6, "target": 7}

def get_final_set_tb_rule(tournament, year):
    if tournament == "NextGen_Finals":
        return {"trigger": 3, "target": 7}

    if tournament == "Australian_Open":
        if year >= 2019:
            return {"trigger": 6, "target": 10}
        return None

    if tournament == "Wimbledon":
        if year >= 2022:
            return {"trigger": 6, "target": 10}
        elif year >= 2019:
            return {"trigger": 12, "target": 7}
        return None

    if tournament == "Roland_Garros":
        if year >= 2022:
            return {"trigger": 6, "target": 10}
        return None

    if tournament == "US_Open":
        if year >= 2022:
            return {"trigger": 6, "target": 10}
        return {"trigger": 6, "target": 7}

    return {"trigger": 6, "target": 7}


def infer_match_scoring_format(match, set_info):
    print(m["match_id"], set_info)
    year = int(match.get("match_id")[:4])
    if "Wimbledon" in match.get("match_id"):
        if year < 2019:
            tb_points_format = None
            set_info["tb_games_format"] = 6
            set_info["tb_win_by_2_point0s"] = 1
            set_info["win_by_2_games"] = 1
            set_info["tb_final_points_format"] = None
            set_info["tb_final_games_format"] = 6
            set_info["tb_final_win_by_2_points"] = 1
            set_info["final_win_by_2_games"] = 1
        if 2019 <= year <= 2021:
            tb_points_format = 7
            tb_games_format = 6
            tb_win_by_2_points = 1
            tb_final_points_format = 7
            tb_final_games_format = 12
            tb_final_win_by_2_points = 1
            win_by_2_games = 0
            final_win_by_2_games = 0
        elif year >= 2022:
            tb_points_format = 7
            tb_games_format = 6
            tb_win_by_2_points = 1
            tb_final_points_format = 10
            tb_final_games_format = 6
            tb_final_win_by_2_points = 1
            win_by_2_games = 0
            final_win_by_2_games = 0
    #quit()
    """
    official_score = get_official_score(match)
    terminating_set = int(last_point['Set1']) + int(last_point['Set2']) + 1

    set_scores = official_score.split(" ")
    results = {}
    year = int(match.get("match_id")[:4])
    tb_final_points_format = None
    tb_final_games_format = None
    tb_final_win_by_2_points = None
    final_win_by_2_games = None
    if "US_Open" in match["match_id"]:
        tb_points_format = 7
        tb_games_format = 6
        tb_win_by_2_points = 1
        win_by_2_games = 0
        if year < 2022:
            tb_final_points_format = 10
            tb_final_games_format = 6
            tb_final_win_by_2_points = 1
            final_win_by_2_games = 0
        elif year >= 2022:
            tb_final_points_format = 7
            tb_final_games_format = 6
            tb_final_win_by_2_points = 1
            final_win_by_2_games = 0
    elif "Australian_Open" in match.get("match_id"):
        if year < 2019:
            tb_points_format = None
            tb_games_format = 6
            tb_win_by_2_points = 1
            win_by_2_games = 1
            tb_final_points_format = None
            tb_final_games_format = 6
            tb_final_win_by_2_points = 1
            final_win_by_2_games = 1
        else:
            tb_points_format = 7
            tb_games_format = 6
            tb_win_by_2_points = 1
            win_by_2_games = 0
            tb_final_points_format = 10
            tb_final_games_format = 6
            tb_final_win_by_2_points = 1
            final_win_by_2_games = 0
    elif "Wimbledon" in match.get("match_id"):
        if year < 2019:
            tb_points_format = None
            tb_games_format = 6
            tb_win_by_2_points = 1
            win_by_2_games = 1
            tb_final_points_format = None
            tb_final_games_format = 6
            tb_final_win_by_2_points = 1
            final_win_by_2_games = 1
        if 2019 <= year <= 2021:
            tb_points_format = 7
            tb_games_format = 6
            tb_win_by_2_points = 1
            tb_final_points_format = 7
            tb_final_games_format = 12
            tb_final_win_by_2_points = 1
            win_by_2_games = 0
            final_win_by_2_games = 0
        elif year >= 2022:
            tb_points_format = 7
            tb_games_format = 6
            tb_win_by_2_points = 1
            tb_final_points_format = 10
            tb_final_games_format = 6
            tb_final_win_by_2_points = 1
            win_by_2_games = 0
            final_win_by_2_games = 0
    elif "Roland_Garros" in match["match_id"] or "French_Open" in match["match_id"]:
        if year < 2022:
            tb_points_format = 7
            tb_games_format = 6
            tb_win_by_2_points = 1
            tb_final_points_format = None
            tb_final_games_format = 6
            tb_final_win_by_2_points = 1
            final_win_by_2_games = 1
            win_by_2_games = 0
        elif year >= 2022:
            tb_points_format = 7
            tb_games_format = 6
            tb_win_by_2_points = 1
            tb_final_points_format = 10
            tb_final_games_format = 6
            tb_final_win_by_2_points = 1
            final_win_by_2_games = 0
            win_by_2_games = 0
    elif "Olympics" in match["match_id"]:
        tb_points_format = None
        tb_games_format = 6
        tb_win_by_2_points = 1
        win_by_2_games = 1
        tb_final_points_format = None
        tb_final_games_format = 6
        tb_final_win_by_2_points = 1
        final_win_by_2_games = 1
    
    else:
        s1 = re.sub(r"\[(\d+-\d+|\*)\]", r"\1", re.sub(r"\(\d+\)", "", " ".join(set_scores[:-1])))
        s2 = re.sub(r"\[(\d+-\d+|\*)\]", r"\1", re.sub(r"\(\d+\)", "", set_scores[-1]))
        nums = [int(x) for x in re.findall(r"\d+", s1)]
        nums2 = [int(x) for x in re.findall(r"\d+", s2)]
        if max(nums) <= 7:
            tb_points_format = 7
            tb_games_format = 6
            tb_win_by_2_points = 1
            win_by_2_games = 0
            final_win_by_2_games = 0
            tb_final_win_by_2_points = 1
            tb_final_games_format = 6
        elif max(nums) >= 8 and abs(nums[0] - nums[1]) >= 2:
            print(f"Adv Set: {official_score}")
            tb_points_format = None
            tb_games_format = 6
            tb_win_by_2_points = 1
            win_by_2_games = 2
            if not tb_final_points_format:
                tb_final_points_format = None
            if not tb_final_games_format:
                tb_final_games_format = 6
            tb_final_win_by_2_points = 1
            final_win_by_2_games = 1
        else:
            print(match)
            print(nums, nums2)
            print(last_point)
            quit()
    """


def is_serve_in(x):
    if x is None or pd.isna(x):
        return None
    x = str(x).strip()
    if len(x) == 0 or x == "":
        return None
    char = x[1] if len(x) > 1 else x
    if char in ["P", "Q", "R", "S"]:
        return None
    elif char in "nwdxge!V":
        return 0
    return 1

def is_rally(serve_rally, in_play):
    if in_play is None:
        return None
    elif in_play == 0:
        return 0
    elif in_play == 1:
        if len(serve_rally) > 2 or serve_rally[-1] == "C":
            return 1
        return 0
    else:
        print(f"Unknown ({is_in}): {s1}")
        quit()

def get_serve_sequence(has_rally, rally):
    if has_rally is None:
        return None
    elif has_rally == 0:
        return rally
    elif has_rally == 1:
        return rally[0]
    else:
        print(f"Unknown Serve Rally Pattern ({has_rally}): {rally}")
        quit()

def get_serve_rally(first_serve_has_rally, first_no_serve_and_volley, second_serve_has_rally, second_no_serve_and_volley):
    if pd.notna(first_serve_has_rally) and first_serve_has_rally == 1:
        return first_no_serve_and_volley[1:]
    if pd.notna(second_serve_has_rally) and second_serve_has_rally == 1:
        return second_no_serve_and_volley[1:] 
    return None

def is_ace(first_serve_sequence, second_serve_sequence):
    if pd.notna(first_serve_sequence) and "*" in first_serve_sequence:
        return 1
    if pd.notna(second_serve_sequence) and "*" in second_serve_sequence:
        return 1
    if pd.notna(first_serve_sequence) or pd.notna(second_serve_sequence):
        return 0
    return None

def is_unreturned(first_serve_sequence, second_serve_sequence):
    if pd.notna(first_serve_sequence) and "#" in first_serve_sequence:
        return 1
    if pd.notna(second_serve_sequence) and "#" in second_serve_sequence:
        return 1
    if pd.notna(first_serve_sequence) or pd.notna(second_serve_sequence):
        return 0
    return None

def is_rally_winner(rally):
    if pd.notna(rally):
        if "*" in rally:
            return 1
        return 0
    return None
def is_forced_error(rally):
    if pd.notna(rally):
        if "#" in rally:
            return 1
        return 0
    return None
def is_unforced_error(rally):
    if pd.notna(rally):
        if "@" in rally:
            return 1
        return 0
    return None
def is_double_fault(first_serve_in, second_serve_in):
    if pd.notna(first_serve_in) and pd.notna(second_serve_in):
        if first_serve_in == 0 and second_serve_in == 0:
            return 1
        return 0
    return None
def rally_length(rally):
    if pd.notna(rally):
        rally_no_spec = rally.replace("-", "").replace("=", "").replace("C", "").replace("@", "").replace("#", "").replace("*", "").replace(";", "").replace("+", "").replace("^", "")
        rally_no_error = rally_no_spec.replace("d", "").replace("w", "").replace("x", "").replace("e", "").replace("n", "").replace("!", "")
        rally_no_direction = rally_no_error.replace("1", "").replace("2", "").replace("3", "").replace("7", "").replace("8", "").replace("9", "")
        return len(rally_no_direction)
    return None
def normalize_points(points):
    points_map = {"0": 0, "15": 1, "30": 2, "40": 3, "45": 4}
    server_points, returner_points = points.lower().replace("ad", "45").split("-")
    point["server_points"] = int(points[0])
    point["returner_points"] = int(points[1])
    return point

def get_tournament_tiebreak_format(tourn_name, match_id):
    match_year = int(match_id[:4])
    result = {}

    if ("Australian_Open" in tourn_name and match_year <= 1970) or \
        ("Wimbledon" in tourn_name and match_year <= 1970) or \
        ("Roland_Garros" in tourn_name and match_year <= 1972) or \
        ("US_Open" in tourn_name and match_year < 1970):
            result["is_advantage_sets"] = True

    if "NextGen" in tourn_name:
        result["regular_tb_games_trigger"] = 3
        result["regular_tb_points_needed"] = 7
        result["final_tb_games_trigger"] = 3
        result["final_tb_points_needed"] = 10
    elif "Australian_Open" in tourn_name:
        result["regular_tb_games_trigger"] = 6
        result["regular_tb_points_needed"] = 7
        if 1971 <= match_year < 2019:
            result["final_tb_games_trigger"] = 6
            result["final_tb_points_needed"] = 7
        elif match_year >= 2019:
            result["final_tb_games_trigger"] = 6
            result["final_tb_points_needed"] = 10
    elif "Wimbledon" in tourn_name:
        result["regular_tb_points_needed"] = 7
        result["regular_tb_games_trigger"] = 6
        if 1971 <= match_year < 2019:
            result["regular_tb_games_trigger"] = 8
            # No tiebreak final set
        elif 2019 <= match_year <= 2021:
            result["final_tb_games_trigger"] = 12
            result["final_tb_points_needed"] = 7
        elif match_year >= 2022:
            result["final_tb_games_trigger"] = 6
            result["final_tb_points_needed"] = 10
    elif "Roland_Garros" in tourn_name:
        result["regular_tb_games_trigger"] = 6
        result["regular_tb_points_needed"] = 7
        if match_year >= 2022:
            result["final_tb_games_trigger"] = 6
            result["final_tb_points_needed"] = 10
    elif "US_Open" in tourn_name or "Forest_Hills" in tourn_name:
        result["regular_tb_games_trigger"] = 6
        result["regular_tb_points_needed"] = 7
        result["final_tb_games_trigger"] = 6
        # 1970–1974: 5-point sudden-death tiebreak
        if 1970 <= match_year <= 1974:
            result["regular_tb_points_needed"] = 5
            result["final_tb_points_needed"] = 5
        # 1975–2021: standard 7-point tiebreak
        elif 1975 <= match_year <= 2021:
            result["final_tb_points_needed"] = 7
        # 2022+: 10-point final-set tiebreak
        elif match_year >= 2022:
            result["final_tb_points_needed"] = 10
    elif "Grand_Slam_Cup" in tourn_name:
        result["regular_tb_games_trigger"] = 6
        result["regular_tb_points_needed"] = 7

    else:
        if tourn_name not in UNIQUE_TOUNRNS and tourn_name[-3:] != "_CH":
            #print(f"Unknown Tournament Name: {tourn_name} - {match_id}")
            UNIQUE_TOUNRNS.append(tourn_name)
            # quit()
    return result


def get_tb_info(match_id, match_year, best_of, is_final_set, server_sets, returner_sets, server_games, returner_games, points, set_score, set_scores_info, diff):

    is_tb_point = 0
    is_game_point = 0
    is_break_point = 0
    sets_needed = (best_of // 2) + 1
    points_map = {"0": 0, "15": 1, "30": 2, "40": 3, "45": 4}
    server_points, returner_points = points.lower().replace("ad", "45").split("-")
    server_points = int(server_points)
    returner_points = int(returner_points)

    tourn_name = match_id.split("-")[2]
    is_super_tb = is_10_point_super_tb(tourn_name, match_year, server_games, returner_games, is_final_set)
    if "Wimbledon" in tourn_name:
        if int(2019 <= year <= 2021 and sgames == 12 and rgames == 12):
            pass
    if "US_Open" in tourn_name:
        if 1970 <= year >= 1974 and sgames == 4 and rgames == 4:
            is_tb_point = 1
            points_needed = 5
        elif match_year >= 1975 and server_games == 6 and returner_games == 6:
            return 1, 7
    is_tb_point  = any([is_super_tb, is_12_game_tb, is_usopen_super_tb])

    
    if is_tb_point == 0:
        try:
            server_points = int(points_map[str(server_points)])
            returner_points = int(points_map[str(returner_points)])
        except Exception as e:
            print(f"Failed to normalize point scores: {e}")
            print(server_points, returner_points)
            print(f"{set_scores_info}")
            print(points)
            print(match_id)
            print("----------------------------------------------------\n")
        is_game_point = ((server_points + 1 >= 4) and ((server_points + 1) - returner_points >= 2))
        is_break_point = ((returner_points + 1 >= 4) and ((returner_points + 1) - server_points >= 2))

    else:
        try:
            is_game_point = ((server_points + 1 >= points_needed) and ((server_points + 1) - returner_points >= 2))
        except:
            print(f"Failed Game Point (is_tb_point: {is_tb_point}, is_game_point: {is_game_point}, is_break_point: {is_break_point}): {match_id} | Points: {server_points} (S), {returner_points} (R) |  Games: {server_games} (S), {returner_games} (R) | Official Score: {set_score['official_score']}")
            quit()
    return
    
    
    
    
    
    
    
    
    
    if is_tb_point == 1:
        # 10 point
        if is_final_set == 1 and (("Wimbledon" in match_id and match_year >= 2022) or \
            ("Australian_Open" in match_id and match_year >= 2019) or \
            ("Roland Garros" in match_id and match_year >= 2022) or \
            ("US_Open" in match_id and match_year >= 2022)):
            points_needed = 10
        elif is_final_set == 1 and (("Wimbledon" in match_id and match_year < 2019) or \
            ("Australian_Open" in match_id and match_year < 2019) or \
            ("Roland Garros" in match_id and match_year < 2022)):
            points_needed = None # win by 2 games
        else:
            points_needed = 7
        
        if points_needed is not None and ((server_points + 1) >= points_needed and ((server_points+1) - returner_points) >= 2):
            is_game_point = 1


    if is_game_point == 1 and server_sets + 1 >= sets_needed:
        is_match_point = 1
    else:
        is_match_point = 0

if __name__ == "__main__":
    DATA_DIR = pathlib.Path(__file__).resolve().parent.parent.parent / "data"
    raw_points_filenames = [DATA_DIR / "raw/tennisabstract/tennis_MatchChartingProject-master/charting-m-points-to-2009.csv", 
                  DATA_DIR / "raw/tennisabstract/tennis_MatchChartingProject-master/charting-w-points-to-2009.csv", 
                  DATA_DIR / "raw/tennisabstract/tennis_MatchChartingProject-master/charting-m-points-2010s.csv",
                  DATA_DIR / "raw/tennisabstract/tennis_MatchChartingProject-master/charting-w-points-2010s.csv",
                  DATA_DIR / "raw/tennisabstract/tennis_MatchChartingProject-master/charting-m-points-2020s.csv",
                  DATA_DIR / "raw/tennisabstract/tennis_MatchChartingProject-master/charting-w-points-2020s.csv"
    ]
    charting_matches_filename = DATA_DIR / "prod/charting-matches.parquet"
    points = load_points(raw_points_filenames)
    points_by_id = build_match_point_dict(points, "match_id")
    matches = load_charting_matches(charting_matches_filename)
    matches_by_id = build_dict(matches, "match_id")
    print(f"Found {len(matches)} Matches")
    print(f"Found {len(points)} Points")
    um = {}
    c = 0
    ttypes = []

    for m in matches:
        match_id = m["match_id"]
        tournament_type = match_id.split("-")[2]
        if tournament_type.endswith("_CH"):
            tournament_type = tournament_type[:-3]
        match_year = int(match_id[:4])
        #if match_year < 2000:
        #    continue

        #if match_id not in points_by_id or (any(keyword in match_id for keyword in IGNORED_TOURNAMENT_TYPES)) or (("RET" in str(m["score"]) or "RET" in str(m["match_score"])) or ("DEF" in str(m["score"]) or "DEF" in str(m["match_score"]))):
        #    continue
        #if m["match_id"] in ["20190701-W-Wimbledon-R128-Daria_Saville-Elina_Svitolina", "19880722-M-Davis_Cup_World_Group_SF-RR-Stefan_Edberg-Henri_Leconte"]:
        #    continue
        c += 1
        # if match_id in ["20140624-M-Wimbledon-R128-Rafael_Nadal-Martin_Klizan",
        #                 "20160710-M-Winnetka_CH-F-Yoshihito_Nishioka-Francis_Tiafoe",
        #                 "20160807-M-Granby_CH-F-Marcelo_Arevalo-Francis_Tiafoe",
        #                 "20170210-M-San_Francisco_CH-QF-Vasek_Pospisil-Francis_Tiafoe",
        #                 "20170327-M-Miami_Masters-R32-Roger_Federer-Juan_Martin_Del_Potro",
        #                 "20171119-M-Tour_Finals-F-Grigor_Dimitrov-David_Goffin"]:
        #     print(f"Missing Best Of: {m}")
        #     print(pd.isna(m["best_of"]))
        #     print("-------------------------------------------------------------")
        if pd.isna(m["best_of"]):
            print(f"Missing Best Of: {match_id}")
            if (len(m.get("score").split(" ")))<=3:
                m["best_of"] = 3
        continue
        match_points = dict(sorted(points_by_id[m.get("match_id")].items(), key=lambda x: int(x[0])))
        # tourn_set_info = get_tournament_tiebreak_format(m["match_id"].split("-")[2], m["match_id"])

        # last_point_number, last_point = next(reversed(match_points.items()))
        

        #set_scores_info = get_set_info(m)
        #match_year = int(m.get("match_id")[:4])

        prev_point = None
        for point_number, point in match_points.items():
            del point["index"]
            if int(point["Gm1"]) >= 6 and int(point["Gm2"]) >= 6 and tournament_type not in ttypes:
                ttypes.append(tournament_type)
                if "6-7" not in m["score"] and "7-6" not in m["score"]:
                    print(tournament_type, m["score"])
            continue
            # print(point)
            
            
            if prev_point == None or point["Pts"] == "0-0":
                point.update({"is_game_point": 0, "is_set_point": 0, "is_match_point": 0})
                point = rename_point_keys(point, prev_point, m)

            elif prev_point is not None:
                point = rename_point_keys(point, prev_point, m)
                tmp_set_num = (int(point['server_sets']) + int(point['returner_sets']))
                if int(point['server_sets']) + 1 >= m["best_of"] or int(point['returner_sets']) + 1 >= m["best_of"]:
                    set_info = set_scores_info[str(tmp_set_num)]
                else:
                    set_info = set_scores_info[str(tmp_set_num+1)]

                server_points, returner_points = point["Pts"].lower().replace("ad", "45").split("-")
                server_points = int(server_points)
                returner_points = int(returner_points)
                prev_server_points, prev_returner_points = prev_point["Pts"].lower().replace("ad", "45").split("-")
                diff = abs((int(server_points)+int(returner_points)) - (int(prev_server_points)+int(prev_returner_points)))
                if diff not in [1, 5, 10, 15]:
                    print(f"Unexpected Point Differential")
                    print(json.dumps(point, indent=4))
                sets_needed = (m["best_of"] // 2) + 1
                get_tb_info(m["match_id"], match_year, m["best_of"], set_info["is_final_set"], point["server_sets"], point["returner_sets"], point["server_games"], point["returner_games"], point["Pts"], set_info, set_scores_info, diff)
                



                
                # if max(map(int, set_info["set_score"].split("-"))) < 6:
                #     print("Bad Values")
                #     print(json.dumps(point, indent=4))
                #     print(json.dumps(m, indent=4))
                #     print(json.dumps(set_info, indent=4))
                #     quit()

                
                    
                # try:
                #     tmp_set_num = (int(point['server_sets']) + int(point['returner_sets']))
                #     set_info = set_scores_info[str(tmp_set_num)]
                # except Exception as e:
                #     print(tmp_set_num, set_scores_info)
                #     print(json.dumps(prev_point, indent=4))
                #     print(json.dumps(point, indent=4))
                #     c += 1
                #     print(e)
                #     quit()
            prev_point = point
            continue
            point["server_player_id"] = m[f"player_{point['server_player_number']}_id"]
            point["returner_player_id"] = m[f"player_{point['returner_player_number']}_id"]
            
            # Rally
            srv1 = point["first_serve_rally"].strip().replace(" ", "").replace("D", "d").replace("W", "w").replace("M", "m").replace(")*", "0*").replace("&*", "0*").replace("?", "0").replace(".", "")
            srv2 = point["second_serve_rally"].strip().replace(" ", "").replace("D", "d").replace("W", "w").replace("M", "m").replace(".", "") if point["second_serve_rally"] is not None else None
            srv1_no_lets = srv1.replace("c", "")
            srv2_no_lets = srv2.replace("c", "") if srv2 is not None else None
            first_no_serve_and_volley = srv1_no_lets.replace("+", "") if srv1_no_lets else None
            second_no_serve_and_volley = srv2_no_lets.replace("+", "") if srv2_no_lets else None
            first_serve_in = is_serve_in(first_no_serve_and_volley)
            second_serve_in = is_serve_in(second_no_serve_and_volley)
            first_serve_has_rally = is_rally(first_no_serve_and_volley, first_serve_in)
            second_serve_has_rally = is_rally(second_no_serve_and_volley, second_serve_in)
            first_serve_sequence = get_serve_sequence(first_serve_has_rally, first_no_serve_and_volley)
            second_serve_sequence = get_serve_sequence(second_serve_has_rally, second_no_serve_and_volley)
            rally = get_serve_rally(first_serve_has_rally, first_no_serve_and_volley, second_serve_has_rally, second_no_serve_and_volley)
            point["rally"] = rally
            point["is_ace"] = is_ace(first_serve_sequence, second_serve_sequence)
            point["is_unreturned"] = is_unreturned(first_serve_sequence, second_serve_sequence)
            point["is_rally_winner"] = is_rally_winner(rally)
            point["is_forced_error"] = is_forced_error(rally)
            point["is_unforced_error"] = is_unforced_error(rally)
            point["is_double_fault"] = is_double_fault(first_serve_in, second_serve_in)
            point["rally_length"] = rally_length(rally)
            point["first_serve_rally"] = srv1
            point["second_serve_rally"] = srv2
            point["first_serve_is_in"] = first_serve_in
            point["second_serve_is_in"] = second_serve_in
            point["first_serve_has_rally"] = first_serve_has_rally
            point["second_serve_has_rally"] = second_serve_has_rally
            # point["first_serve_sequence"] = first_serve_sequence
            # point["second_serve_sequence"] = second_serve_sequence
            # point = normalize_points(point)
            diff = None

            # if (set_info["set_score"] == "6-7" or set_info["set_score"] == "7-6") and (point["server_games"] == 6 and point["returner_games"] == 6) and (point["server_points"] in [15, 30, 40, 45] and point["returner_points"] in [15, 30, 40, 45]): # ((point["server_games"] == 6 and point["returner_games"] == 7) or (point["server_games"] == 7 and point["returner_games"] == 6)):
            #     print(f"Found Bad Set Info")
            point_map = {"0": 0, "15": 1, "30": 2, "40": 3, "45": 4}
            points_str = point["Pts"].split("-")
            point["server_points_raw"] = int(points_str[0].lower().strip().replace("ad", "45"))
            point["returner_points_raw"] = int(points_str[1].lower().strip().replace("ad", "45"))
            point["is_tb_point"] = 0
            point["is_deuce"] = 0
            point["is_break_point"] = 0
            point["Pts"] = f"{point['server_points_raw']}-{point['returner_points_raw']}"
            points_str = point["Pts"].split("-")
            if (point["is_tb_set"] == 1 or point["is_super_tb_set"] == 1) \
                and (
                    (point["server_games"] == 6 and point["returner_games"] == 6 and ("6-7" in set_info["set_score"] or "7-6" in set_info["set_score"])) \
                    or (point["is_super_tb_set"] == 1 or (point["server_games"] == 12 and point["returner_games"] == 12) and "Wimbledon" in m["match_id"]) \
                    or (point["server_games"] == 3 and point["returner_games"] == 3 and "NextGen" in m["match_id"] and set_info["set_score"] in ["4-3", "3-4"])
                ):
                    point["is_tb_point"] = 1
                    point["server_points"] = int(point["server_points_raw"])
                    point["returner_points"] = int(point["returner_points_raw"])
            else:
                point["server_points"] = int(point_map[str(point["server_points_raw"])])
                point["returner_points"] = int(point_map[str(point["returner_points_raw"])])
            
            
            # if set_info[""] != 0 and point["returner_points"] != 0:
                # try:
                # diff = abs(abs(point["server_points_raw"]+point["returner_points_raw"]) - abs(prev_point["server_points_raw"]+prev_point["returner_points_raw"]))
                # if (point["is_tb_point"] == 1 and diff != 1):
                #     point["server_points"] = int(point_map[str(point["server_points_raw"])])
                #     point["returner_points"] = int(point_map[str(point["returner_points_raw"])])
                #     point["Pts"] = f"{point['server_points']}-{point['returner_points']}"
                # print(prev_point)
                # print(point)
                # print(diff)
                # print(set_info)
                # print(m)
                # print("--------------------------------------")
                # quit()

                    

            if  point["is_tb_point"] == 0:
                if point["Pts"] == "40-40":
                    point["is_deuce"] = 1
                elif point["Pts"] in ["0-40", "15-40", "30-40", "40-45"]:
                    point["is_break_point"] = 1

                # if point["is_tb_point"] == 0:
                #     point["is_break_point"] = int(point["Pts"] in ["0-40", "15-40", "30-40", "40-45"])
                #     if point["is_break_point"] == 1:
                #         print(json.dumps(prev_point, indent=4))
                #         print(json.dumps(point, indent=4), set_info, diff)
                #         print("-------------------------------------------------")
                #         quit()
            prev_point = point

    # print(sorted(UNIQUE_TOUNRNS))
    # print(len(UNIQUE_TOUNRNS))
    # print(f"Total Matches: {c}")
    # print(f"\nTournament Tiebreak Types")
    # print(ttypes)

"""
| Tournament/Event                          | Rationale for Exclusion                                                                                                                                                                                                                                                                         |
| ----------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Wimbledon Championships (`Wimbedon`)      | Wimbledon used a non-standard non-deciding-set tiebreak rule from 1971-2018, with tiebreaks played at 8-8 instead of the standard 6-6. Prior to 1971, no tiebreaks were used. These historical differences create structural incompatibility with tournaments using the modern standard format. |
| Tour Championships (`Tour_Championships`) | Year-end championships historically used round-robin formats and occasionally altered competition structures relative to standard tour events, potentially affecting match incentives and set-level dynamics.                                                                                   |
| `Dallas_WCT`                              | Early World Championship Tennis (WCT) events occurred during the transitional era of tiebreak adoption in professional tennis and may contain non-standard historical scoring implementations.                                                                                                  |
| `Forest_Hills_WCT`                        | Excluded due to potential overlap with early experimental tiebreak structures during the 1970s professional transition period.                                                                                                                                                                  |
| `Wembley`                                 | Older professional-era event with historical scoring and competition structures not fully standardized with modern ATP/WTA formats.                                                                                                                                                             |
| `Tokyo_Indoor`                            | Historical indoor-circuit event potentially overlapping with transitional scoring-rule periods and differing event structures.                                                                                                                                                                  |
| `Sydney_Indoor`                           | Historical indoor event excluded to avoid inconsistencies arising from early-era professional scoring experimentation and format variation.                                                                                                                                                     |
| `Virginia_Slims_Championships`            | Historical women's championship event from an early professional era with potential structural inconsistencies relative to standardized modern WTA scoring formats.                                                                                                                             |
"""