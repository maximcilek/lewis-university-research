import csv
import json
from pathlib import Path
import pathlib
import sys
from collections import Counter, defaultdict

sys.path.append(str(pathlib.Path(__file__).resolve().parent.parent.parent))

import tennisabstractscraper.models.data_objects as data_objects
from tennisabstractscraper.models.tennisabstract_data import TennisAbstractPointsData


DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
METADATA_DIR = DATA_DIR / "canonical/tennisabstract/_meta"


# =========================================================
# 1. STATE CLASSIFICATION (EXPOSURE VARIABLE ONLY)
# =========================================================
def assign_state(score_state):
    """
    Classifies only SCORE CONTEXT (no outcome logic here)
    """

    neutral = {"0-0", "15-15", "30-30", "40-40"}

    pressure = {
        "0-15", "0-30", "0-40",
        "15-0", "30-0", "40-0",
        "15-30", "15-40",
        "30-15", "40-15",
        "30-40", "40-30",
        "AD-40", "40-AD",
    }

    if score_state in neutral:
        return "NEUTRAL"
    if score_state in pressure:
        return "PRESSURE"
    return None


# =========================================================
# 2. CORE DATA TRANSFORMATION
# =========================================================
def extract_features(p):
    """
    Converts raw point into clean analytical variables
    """

    p1_won = int(p["point_winner_player_number"]) == 1
    p1_is_server = int(p["server_player_number"]) == 1

    return {
        "state": assign_state(p.get("game_score")),
        "p1_won": p1_won,
        "p1_is_server": p1_is_server,
        "server_won": p["server_player_number"] == p["point_winner_player_number"]
    }


# =========================================================
# 3. ANALYSIS ENGINE (STATISTICALLY CLEAN)
# =========================================================
def analyze(points_by_match):

    stats = defaultdict(lambda: {
        "n": 0,
        "p1_wins": 0,
        "server_wins": 0
    })

    for _, points in points_by_match.items():
        for p in points:

            f = extract_features(p)
            state = f["state"]

            if state is None:
                continue

            stats[state]["n"] += 1
            stats[state]["p1_wins"] += int(f["p1_won"])
            stats[state]["server_wins"] += int(f["server_won"])

    return stats


# =========================================================
# 4. SUMMARY STATS + EFFECT SIZES
# =========================================================
def print_results(stats):

    print("\n================ STATE DISTRIBUTION ================\n")

    total = sum(v["n"] for v in stats.values())

    for state, s in stats.items():
        pct = s["n"] / total if total else 0

        print(f"{state}: {s['n']} ({pct:.2%})")

    print("\n================ EFFECT ESTIMATES ===================\n")

    neutral = stats.get("NEUTRAL", {"n": 0, "p1_wins": 0})
    pressure = stats.get("PRESSURE", {"n": 0, "p1_wins": 0})

    def rate(x):
        return x["p1_wins"] / x["n"] if x["n"] else 0

    neutral_rate = rate(neutral)
    pressure_rate = rate(pressure)

    print(f"P1 win rate (NEUTRAL):  {neutral_rate:.4f}")
    print(f"P1 win rate (PRESSURE): {pressure_rate:.4f}")

    if neutral_rate > 0:
        lift = pressure_rate / neutral_rate
        print(f"\nPressure effect (ratio): {lift:.3f}")

    print("\n================ SERVER EFFECT =====================\n")

    neutral_srv = stats.get("NEUTRAL", {"n": 0, "server_wins": 0})
    pressure_srv = stats.get("PRESSURE", {"n": 0, "server_wins": 0})

    def srate(x):
        return x["server_wins"] / x["n"] if x["n"] else 0

    print(f"Server win rate (NEUTRAL):  {srate(neutral_srv):.4f}")
    print(f"Server win rate (PRESSURE): {srate(pressure_srv):.4f}")


# =========================================================
# 5. BUILD INDEX
# =========================================================
def build_dict(seq, key):
    return {d[key]: dict(d, index=i) for i, d in enumerate(seq)}


# =========================================================
# 6. MAIN
# =========================================================
if __name__ == "__main__":

    input_csv = DATA_DIR / "canonical/tennisabstract/charting_points.csv"

    points_object = TennisAbstractPointsData(
        input_csv,
        METADATA_DIR / "rally_codes.json"
    )

    CHARTED_MATCHES = data_objects.JsonlDataObject(
        DATA_DIR / "dev/tennisabstract/charting_matches.jsonl"
    ).data

    CHARTED_MATCHES_BY_ID = build_dict(CHARTED_MATCHES, "match_id")
    print(CHARTED_MATCHES[0])

    points_by_match, count_points = points_object.load_points(CHARTED_MATCHES_BY_ID)

    print(f"Loaded Points ({count_points}): {len(points_by_match)}")

    stats = analyze(points_by_match)

    print_results(stats)