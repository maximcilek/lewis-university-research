import pandas as pd
import pathlib
from collections import defaultdict, deque

import sys
sys.path.append(str(pathlib.Path(__file__).resolve().parent.parent.parent))
import tennisabstractscraper.models.data_objects as data_objects

def load_charting_matches(filename):
    charting_matches = data_objects.DataObjectFactory.create(filename).data
    results = []
    for batch in charting_matches:
        for _, match in batch.to_pandas().iterrows():
            results.append(match.to_dict())
    return results

def load_points(filenames):
    result = []
    for f in filenames:
        charting_points = data_objects.DataObjectFactory.create(f)
        result.extend(charting_points.data)
    return result

def build_match_point_dict(seq, key):
    grouped = defaultdict(dict)
    for i, d in enumerate(seq):
        grouped[d[key]][int(d["Pt"])] = dict(d)
    return dict(grouped)


def build_match_set_game_dict(points):
    """
    {
        match_id: {set_number: {game_number: [point_dict, ...]}}
    }
    """
    grouped = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
    for point in points:
        grouped[point["match_id"]][int(point["Set1"]) + int(point["Set2"]) + 1][int(point["Gm#"])].append((int(point["Pt"]), dict(point)))
    
    result = {}
    for match_id, sets in grouped.items():
        result[match_id] = {}
        for set_number in sorted(sets.keys()):
            games = sets[set_number]
            result[match_id][set_number] = {}
            for game_number in sorted(games.keys()):
                sorted_points = [
                    p for _, p in sorted(games[game_number], key=lambda x: x[0])
                ]
                result[match_id][set_number][game_number] = sorted_points

    return result

if __name__ == "__main__":
    DATA_DIR = pathlib.Path(__file__).resolve().parent.parent.parent / "data"
    raw_points_filenames = [DATA_DIR / "raw/tennisabstract/tennis_MatchChartingProject-master/charting-m-points-to-2009.csv", 
                  DATA_DIR / "raw/tennisabstract/tennis_MatchChartingProject-master/charting-w-points-to-2009.csv", 
                  DATA_DIR / "raw/tennisabstract/tennis_MatchChartingProject-master/charting-m-points-2010s.csv",
                  DATA_DIR / "raw/tennisabstract/tennis_MatchChartingProject-master/charting-w-points-2010s.csv",
                  DATA_DIR / "raw/tennisabstract/tennis_MatchChartingProject-master/charting-m-points-2020s.csv",
                  DATA_DIR / "raw/tennisabstract/tennis_MatchChartingProject-master/charting-w-points-2020s.csv"
    ]
    charting_matches_filename = DATA_DIR / "prod/charting-matches-new.parquet"
    count_matches = 0
    
    # Load Matches 
    matches = load_charting_matches(charting_matches_filename)
    matches_by_id = {d["match_id"]: dict(d, index=i) for i, d in enumerate(matches)} # matches_by_id = {d["match_id"]: d for d in matches}

    # Load Points
    points = load_points(raw_points_filenames)
    # points_by_id = build_match_point_dict(points, "match_id")
    points_by_id = build_match_set_game_dict(points)

    print(f"Found {len(matches)} Matches")
    print(f"Found {len(points)} Points")



    for m in matches:
        match_id = m["match_id"]
        tournament_type = match_id.split("-")[2]
        if tournament_type.endswith("_CH"):
            tournament_type = tournament_type[:-3]
        match_year = int(match_id[:4])

        if match_id not in points_by_id or (("RET" in str(m["score"]) or "RET" in str(m["match_score"])) or ("DEF" in str(m["score"]) or "DEF" in str(m["match_score"]))): # or (any(keyword in match_id for keyword in IGNORED_TOURNAMENT_TYPES))
            continue
        # match_points = dict(sorted(points_by_id[match_id].items(), key=lambda x: int(x[0])))
        #print(f"{match_id} has {len(match_points)} Points")
        #print(match_points[1])
        #quit()

        match_sets = points_by_id[match_id]

        print(f"{match_id} has {len(match_sets)} set(s)")
        for set_number, games in match_sets.items():
            print(f"  Set {set_number}: {len(games)} games")
            for game_number, game in games.items():
                print(f"  Game: {game}")
                # print("-----------------------------------------------")
                break
            print("===============================================")
            
        count_matches += 1
        quit()
    print(f"Successfully Validated {count_matches} Matches")