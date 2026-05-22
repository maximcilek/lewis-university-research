import pandas as pd
import pathlib
from collections import defaultdict, deque
from itertools import zip_longest
import logging
import sys
sys.path.append(str(pathlib.Path(__file__).resolve().parent.parent.parent))
import tennisabstractscraper.models.data_objects as data_objects

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)

TIEBREAK_MATCHES = []

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

# player_game_points_to_int
def normalize_game_points_score(game_points):

    def normalize_single_points_score(score):
        score = score.strip().lower()
        if not isinstance(score, str):
            logger.fatal(f"Unexpected Player Game Points Value Type, Expected String: {score} ({type(score)})")
            sys.exit(1)
        if not score.isdigit():
            if score == "ad":
                return 45
            logger.fatal(f"Unexpected Game Points Value (non-integer and not AD): {score}")
            sys.exit(1)
        return int(score)

    game_points = game_points.strip().lower() # Points1-Points2
    if not isinstance(game_points, str):
        logger.fatal(f"Unexpected Player Game Points Value Type, Expected String: {game_points} ({type(game_points)})")
        sys.exit(1)
    server_score, returner_score = game_points.split("-")
    return normalize_single_points_score(server_score), normalize_single_points_score(returner_score)


def is_tiebreak_game(points):
    tennis_scores_map = {
        "0": 0, "15": 15, "30": 30, "40": 40, "AD": 45
    }

    num_points = len(points) - 1
    while num_points > 0:
        server_score, returner_score = normalize_game_points_score(points[num_points]["Pts"])
        prev_server_score, prev_returner_score = normalize_game_points_score(points[num_points-1]["Pts"])

        diff = abs(abs(server_score - returner_score) - abs(prev_server_score - prev_returner_score))
        if diff % 5 > 0:
            if diff != 1:
                print(f"Prev/Curr (diff: {((diff)%5):>2}): {points[num_points-1]['Pts']:>5} --> {server_score}-{returner_score}")
                quit()
            return True
        num_points -= 1
    return False

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

        if match_id not in points_by_id or "Laver_Cup" in match_id or (("RET" in str(m["score"]) or "RET" in str(m["match_score"])) or ("DEF" in str(m["score"]) or "DEF" in str(m["match_score"]))): # or (any(keyword in match_id for keyword in IGNORED_TOURNAMENT_TYPES))
            continue
        # match_points = dict(sorted(points_by_id[match_id].items(), key=lambda x: int(x[0])))
        #print(f"{match_id} has {len(match_points)} Points")
        #print(match_points[1])
        #quit()

        m['official_score'] = get_official_score(m)

        match_sets = points_by_id[match_id]

        logger.debug(f"Loading Match: {match_id}")
        for set_number, games in match_sets.items():
            for game_number, points in games.items():
                is_tiebreak = is_tiebreak_game(points)
                if is_tiebreak:
                    logging.info(f"Found tiebreak game: {game_number} ({match_id})")
                    last_game_number, last_game_points = list(games.items())[-1]
                    last_point = last_game_points[-1]
                    print(f"{last_point['Gm1']}-{last_point['Gm2']} | {m['official_score']}")
                    print(last_point)
                    quit()
        count_matches += 1
    print(f"Successfully Validated {count_matches} Matches")