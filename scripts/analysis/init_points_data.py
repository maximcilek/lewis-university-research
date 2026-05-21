import pandas as pd
import pathlib
from collections import defaultdict, deque
import logging
import sys
sys.path.append(str(pathlib.Path(__file__).resolve().parent.parent.parent))
import tennisabstractscraper.models.data_objects as data_objects

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)

def load_charting_matches(filename):
    charting_matches = data_objects.DataObjectFactory.create(filename).data
    matches = []
    for batch in charting_matches:
        for _, match in batch.to_pandas().iterrows():
            matches.append(match.to_dict())
    logger.info(f"Loaded {len(matches)} Matches")
    return {d["match_id"]: dict(d, index=i) for i, d in enumerate(matches)} # matches_by_id = {d["match_id"]: d for d in matches}

def load_points(filenames):
    points = []
    for f in filenames:
        charting_points = data_objects.DataObjectFactory.create(f)
        points.extend(charting_points.data)

    grouped = defaultdict(lambda: defaultdict(lambda: defaultdict(list))); [grouped[p["match_id"]][int(p["Set1"]) + int(p["Set2"]) + 1][int(p["Gm#"])].append((int(p["Pt"]), dict(p))) for p in points]
    points_by_match_set_game = {}
    for match_id, sets in grouped.items():
        points_by_match_set_game[match_id] = {}
        for set_number in sorted(sets.keys()):
            games = sets[set_number]
            points_by_match_set_game[match_id][set_number] = {}
            for game_number in sorted(games.keys()):
                sorted_points = [p for _, p in sorted(games[game_number], key=lambda x: x[0])]
                points_by_match_set_game[match_id][set_number][game_number] = sorted_points
    logger.info(f"Loaded {len(points)} Points")
    return points_by_match_set_game

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
    

    matches_by_id = load_charting_matches(charting_matches_filename)
    points_by_id = load_points(raw_points_filenames)

    for match_id, m in matches_by_id.items():
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

        print(f"\n🎾 Match: {match_id}")
        print(f"Sets: {len(match_sets)}")
        print("=" * 80)
        for set_number, games in match_sets.items():
            print(f"\n[SET {set_number}] — {len(games)} games")
            print("-" * 80)
            for game_number, points in games.items():
                print(f"  Game {game_number:>2} — {len(points)} points")
                for point_number, point_data in points.items():
                    score = point_data["Pts"]
                    winner = point_data["PtWinner"]
                    server = point_data["Svr"]
                    print(
                        f"    Pt {point_number:>2} | "
                        f"Score: {score:<7} | "
                        f"Server: P{server} | "
                        f"Winner: P{winner}"
                    )
                print()
                break  # To get every game
        print("=" * 80)
        count_matches += 1
        quit()
    print(f"Successfully Validated {count_matches} Matches")