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


def infer_match_scoring_format(match, last_point):
    
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
def normalize_points(point):
    points = point.get("Pts").split("-")
    if points[0].lower().strip() == "ad":
        points[0] = 45
    if points[1].lower().strip() == "ad":
        points[1] = 45
    point["server_points"] = int(points[0])
    point["returner_points"] = int(points[1])
    return point

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

    for m in matches:
        if m.get("match_id") not in points_by_id:
            continue
        if m.get("match_id") in ["20190208-W-Fed_Cup_G1-RR-Yulia_Putintseva-Ankita_Raina", "20140423-M-Barcelona-R32-Albert_Ramos-Rafael_Nadal", '20200918-W-Rome-R16-Victoria_Azarenka-Daria_Kasatkina', '20190701-W-Wimbledon-R128-Daria_Saville-Elina_Svitolina', '20131005-M-Tokyo-SF-Nicolas_Almagro-Juan_Martin_Del_Potro', '19910604-M-Roland_Garros-QF-Michael_Chang-Boris_Becker']:
            continue
        
        if pd.isna(m["best_of"]):
            if (len(m.get("score").split(" ")))<=3:
                m["best_of"] = 3
        match_points = dict(sorted(points_by_id[m.get("match_id")].items(), key=lambda x: int(x[0])))
        last_point_number, last_point = next(reversed(match_points.items()))

        official_score = get_official_score(m)
        set_scores_info = {}
        if "RET" in official_score or "DEF" in official_score:
            tmp = official_score.split(" ")[-2:]
            # ended on set end
            if m["score"].replace(tmp[-1], "").strip() == str(m["match_score"]).strip():
                # set_scores = re.sub(r"\(\d+\)", "", official_score.strip().split(" "))
                set_scores = official_score.replace(tmp[-1], "").strip().split(" ")
                clean_set_score = re.sub(r"\(\d+\)", "", set_scores[-1])
                a, b = map(int, clean_set_score.split("-"))
                if (f"{int(last_point["Gm1"]) + 1}-{int(last_point["Gm2"])}".strip() == clean_set_score or f"{int(last_point["Gm1"])}-{int(last_point["Gm2"])+1}".strip() == clean_set_score) or \
                (f"{int(last_point["Gm2"]) + 1}-{int(last_point["Gm1"])}".strip() == clean_set_score or f"{int(last_point["Gm2"])}-{int(last_point["Gm1"])+1}".strip() == clean_set_score):
                    pass
                else:
                    g1 = int(last_point["Gm1"])
                    g2 = int(last_point["Gm2"])
                    deciding_set = f"{max(g1, g2)}-{min(g1, g2)}"
                    set_scores.append(f"{deciding_set}")
            else:
                # print(m["match_id"], ": ", official_score.replace(tmp[-1], '').strip(), " | ", m['score'], " | ", m["match_score"])
                # print(json.dumps(last_point, indent=4))
                set_scores = official_score.replace(tmp[-1], '').strip().split(" ")
            m["official_score"] = " ".join(set_scores)
            official_score = m["official_score"]
            continue

        m["official_score"] = official_score
        set_scores = official_score.split(" ")
        for set_num, set_score in enumerate(set_scores):
            s1 = re.sub(r"\[(\d+-\d+|\*)\]", r"\1", re.sub(r"\(\d+\)", "", set_score))
            nums = [int(x) for x in re.findall(r"\d+", s1)]
            set_scores_info[f"{set_num+1}"] = {
                "set_num": set_num,
                "set_score_raw": set_score,
                "set_score": s1,
                "is_super_tb_set": 0,
                "is_tb_set": 0,
                "max_game_number": max(nums),
                "diff": abs(nums[0]-nums[1]),
                "official_score": official_score
            }
            if "[" in set_score or "]" in set_score:
                set_scores_info[f"{set_num+1}"]["is_super_tb_set"] = 1
            elif "(" in set_score or ")" in set_score:
                set_scores_info[f"{set_num+1}"]["is_tb_set"] = 1
            
        serve_window = defaultdict(lambda: deque(maxlen=5))
        prev_point = None
        point_map = {"0": 0, "15": 1, "30": 2, "40": 3, "45": 4}
        for point_number, point in match_points.items():
            del point["index"]
            point = rename_point_keys(point, prev_point, m)
            set_num = int(point['server_sets']) + int(point['returner_sets'])+1
            set_info = set_scores_info[str(set_num)]
            point.update({k: set_info[k] for k in ("is_super_tb_set", "is_tb_set")})
            point["is_game_point"] = 0
            if prev_point == None:
                point["is_game_point"] = 0
                point["is_set_point"] = 0
                point["is_match_point"] = 0
            else:
                if point["game_number"] == prev_point["game_number"] and point["is_tb_set"] == 0 and point["is_super_tb_set"] == 0:
                    prev_server, prev_returner = (prev_point["Pts"].lower().replace("ad", "45").split("-"))
                    server, returner = (point["Pts"].lower().replace("ad", "45").split("-"))
                    point["server_points"] = point_map[server]
                    point["returner_points"] = point_map[returner]
                    point["is_game_point"] = int((point["server_points"] == 3 and point["returner_points"] <= 2) or (point["server_points"] >= 4 and point["server_points"] == point["returner_points"] + 1))
                    diff = abs(int(server) - int(prev_server)) + abs(int(returner) - int(prev_returner))
                    if point["is_game_point"] == 1:
                        print(f"Diff: {diff}")

                        print(set_info)
                        print(json.dumps(prev_point, indent=4))
                        print(json.dumps(point, indent=4))
                        quit()
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


            #if m.get("match_id") == "20000708-W-Wimbledon-SF-Venus_Williams-Serena_Williams" and int(point['server_sets']) + int(point['returner_sets']) + 1 > 1:
            # if point["server_games"] == 6 and point["returner_games"] == 6 and set_info["is_advantage_set"] == 0 and set_info["is_tb_set"] == 0:
            #     print(json.dumps(point, indent=4))
            #     print(set_num, scoring_format)
            #     print(m.get("match_id"), m.get("official_score"))
            #     print("=============================================================")







































#key = (m["match_id"], point["server_player_id"])
#hist = serve_window[key]

#point["server_last5_serve_win_rate"] = (
#    sum(hist) / len(hist) if len(hist) > 0 else None
#)
#hist.append(point["is_server_point_winner"])
# print(json.dumps(point, indent=4))        
# quit()
#is_tb_set = is_tiebreak_set(point["Set1"], point["Set2"], int(m["best_of"]))
#is_tb_point = is_tiebreak_point(point["Set1"], point["Set2"],point["Gm1"], point["Gm2"], int(m["best_of"]), is_tb_set, point, m)
# print(f"Point (#{point_number}): {point} - {is_tb_point}")