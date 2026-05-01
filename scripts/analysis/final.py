import pandas as pd
import pathlib
import numpy as np
from collections import defaultdict
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

def is_tiebreak_set(set1, set2, best_of):
    if not (int(set1)+int(set2)+1)<best_of:
        return True
    return False

def is_tiebreak_point(set1, set2, game1, game2, best_of, is_tb_set, point, match):
    """
    0 = Advantage Set
    S = 10-point Super-Tiebreak
    W = 8-all Tiebreak
    A = 6-all 10-point Super-Tiebreak
    T = 12-all Tiebreak
    V = No Tiebreakers
    """
    set_scores = re.sub(r"\([^)]*\)", "", match.get("score")).split(" ")
    try:
        if int(game1) == 6 and int(game2) == 6:
            if "10" in set_scores[0] or "11" in set_scores[0] or "10" in set_scores[1] or "11" in set_scores[1]:
                print(set_scores)
                quit()
        if int(game1) > 6 or int(game2) > 6:
            print(f"{match}")
            print(f"{point}")
            quit()    
    except:
        print(f"{match}")
        print(f"{point}")

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
        if m.get("match_id") == "19931107-M-Paris_Masters-SF-Stefan_Edberg-Goran_Ivanisevic":
            continue
        if pd.isna(m["best_of"]):
            if (len(m.get("score").split(" ")))<=3:
                m["best_of"] = 3
        match_points = points_by_id[m.get("match_id")]
        # print(f"Match {m.get('match_id')} has {len(match_points)} points")
        # print(match_points[max(match_points)])
        for point_number, point in match_points.items():
            is_tb_set = is_tiebreak_set(point["Set1"], point["Set2"], int(m["best_of"]))
            is_tb_point = is_tiebreak_point(point["Set1"], point["Set2"],point["Gm1"], point["Gm2"], int(m["best_of"]), is_tb_set, point, m)
            continue
            srv1 = point["1st"].strip().replace(" ", "").replace("D", "d").replace("W", "w").replace("M", "m").replace(")*", "0*").replace("&*", "0*").replace("?", "0").replace(".", "")
            srv2 = point["2nd"].strip().replace(" ", "").replace("D", "d").replace("W", "w").replace("M", "m").replace(".", "")
            srv1_no_lets = srv1.replace("c", "") if srv1 else None
            srv2_no_lets = srv2.replace("c", "") if srv2 else None
            first_no_serve_and_volley = srv1_no_lets.replace("+", "") if srv1_no_lets else None
            second_no_serve_and_volley = srv2_no_lets.replace("+", "") if srv2_no_lets else None
            first_serve_in = is_serve_in(first_no_serve_and_volley)
            second_serve_in = is_serve_in(second_no_serve_and_volley)
            first_serve_has_rally = is_rally(first_no_serve_and_volley, first_serve_in)
            second_serve_has_rally = is_rally(second_no_serve_and_volley, second_serve_in)
            first_serve_sequence = get_serve_sequence(first_serve_has_rally, first_no_serve_and_volley)
            second_serve_sequence = get_serve_sequence(second_serve_has_rally, second_no_serve_and_volley)
            
            point["first_serve_is_in"] = first_serve_in
            point["second_serve_is_in"] = second_serve_in
            point["first_serve_has_rally"] = first_serve_has_rally
            point["second_serve_has_rally"] = second_serve_has_rally
            point["first_serve_sequence"] = first_serve_sequence
            point["second_serve_sequence"] = second_serve_sequence
            if srv1 in [None, ""]:
                point["1st"] = None
            if srv2 in [None, ""]:
                point["2nd"] = None

            # print(f"Point (#{point_number}): {point}")
        # quit()