import csv
import json
import re
from pathlib import Path
import pathlib
import sys
from collections import Counter, defaultdict

sys.path.append(str(pathlib.Path(__file__).resolve().parent.parent.parent))

import tennisabstractscraper.models.data_objects as data_objects
from tennisabstractscraper.models.tennisabstract_data import TennisAbstractPointsData


DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
METADATA_DIR = DATA_DIR / "canonical/tennisabstract/_meta"

def assign_state(score_state):
    draw_states = {"0-0", "15-15", "30-30", "40-40"}
    stress_states = {
        "0-15", "0-30", "0-40",
        "15-0", "30-0", "40-0",
        "15-30", "15-40",
        "30-15", "40-15",
        "30-40", "40-30",
        "AD-40", "40-AD",
    }

    if score_state in draw_states:
        return "CASE_3"
    if score_state in stress_states:
        return "PRESSURE"
    return None

def assign_case_direction(p1_won, p1_is_server):
    """
    Only valid for PRESSURE points
    """

    case1 = (not p1_won and p1_is_server) or (p1_won and not p1_is_server)
    case2 = (p1_won and p1_is_server) or (not p1_won and not p1_is_server)

    if case1:
        return "CASE_1"
    if case2:
        return "CASE_2"

    return None

# -----------------------------
# CASE DEFINITIONS (PURE SCORE STATE ONLY)
# -----------------------------
def assign_case(score_state):
    """
    Pure state classification:
    - CASE_3 = neutral/deuce-like
    - CASE_1/CASE_2 = pressure states (handled later via outcome)
    """

    draw_states = {"0-0", "15-15", "30-30", "40-40"}
    if score_state in draw_states:
        return "CASE_3"

    stress_states = {
        "0-15", "0-30", "0-40",
        "15-0", "30-0", "40-0",
        "15-30", "15-40",
        "30-15", "40-15",
        "30-40", "40-30",
        "AD-40", "40-AD",
    }

    if score_state in stress_states:
        return "PRESSURE"

    return None


# -----------------------------
# MAIN ANALYSIS
# -----------------------------
def analyze_points2(points_by_match):
    """
    Produces:
    - server win/loss rates under pressure
    - P1 win/loss rates under pressure
    - breakdown by score state class
    """

    stats = defaultdict(lambda: {
        "total": 0,
        "p1_wins": 0,
        "p1_losses": 0,
        "server_wins": 0,
        "server_losses": 0,
    })

    case_counts = Counter()

    for match_id, points in points_by_match.items():
        for p in points:
            print(p)
            quit()

            score = p.get("game_score")

            case = assign_case(score)
            if case is None:
                continue

            p1_won = int(p["point_winner_player_number"]) == 1
            server_is_p1 = int(p["server_player_number"]) == 1

            server_won = (p["server_player_number"] ==
                          p["point_winner_player_number"])

            case_counts[case] += 1

            stats[case]["total"] += 1

            # P1 outcomes
            if p1_won:
                stats[case]["p1_wins"] += 1
            else:
                stats[case]["p1_losses"] += 1

            # Server outcomes
            if server_won:
                stats[case]["server_wins"] += 1
            else:
                stats[case]["server_losses"] += 1

    return stats, case_counts



def print_results(stats, case_counts):

    # -----------------------------
    # HUMAN-READABLE DEFINITIONS
    # -----------------------------
    case_descriptions = {
        "PRESSURE": (
            "Pressure points are situations where one player is close to winning or losing the game.\n"
            "Examples include: 0-30, 0-40, 30-40, 40-AD, etc.\n"
            "These are high-stakes moments where mistakes (like double faults or unforced errors) are more likely."
        ),
        "CASE_3": (
            "Neutral or balanced points where neither player has a clear advantage.\n"
            "Examples include: 0-0, 15-15, 30-30, 40-40 (deuce-like situations)."
        )
    }

    print("\n================ CASE DISTRIBUTION ================\n")

    total_points = sum(case_counts.values())

    for k, v in case_counts.items():
        pct = v / total_points if total_points else 0

        print(f"{k}: {v} ({pct:.2%} of all analyzed points)")
        print(case_descriptions.get(k, "No description available."))
        print("------------------------------------")

    print("\n================ PERFORMANCE =======================\n")

    for case, s in stats.items():
        total = s["total"]

        p1_win_rate = s["p1_wins"] / total if total else 0
        p1_loss_rate = s["p1_losses"] / total if total else 0

        server_win_rate = s["server_wins"] / total if total else 0
        server_loss_rate = s["server_losses"] / total if total else 0

        print(f"\n{case}")
        print("--------------------------------------------------")
        print(f"Total points analyzed in this category: {total}")

        print("\n🔵 Player 1 (P1) performance:")
        print(f"  - Win rate:  {p1_win_rate:.4f}")
        print(f"  - Loss rate: {p1_loss_rate:.4f}")

        print("\n🎾 Server performance:")
        print(f"  - Server win rate:  {server_win_rate:.4f}")
        print(f"  - Server loss rate: {server_loss_rate:.4f}")

        print("\n📌 Interpretation:")
        print(
            "  This section compares how often the player wins the point "
            "and how often the server holds serve in this situation."
        )

        print("------------------------------------")


def analyze_points(points_by_match):

    stats = defaultdict(lambda: {
        "total": 0,
        "p1_wins": 0,
        "p1_losses": 0,
        "server_wins": 0,
        "server_losses": 0,
    })

    case_counts = Counter()

    for match_id, points in points_by_match.items():
        for p in points:

            score = p.get("game_score")
            state = assign_state(score)

            if state is None:
                continue

            p1_won = int(p["point_winner_player_number"]) == 1
            server_is_p1 = int(p["server_player_number"]) == 1
            server_won = p["server_player_number"] == p["point_winner_player_number"]

            # CASE 3 (neutral)
            if state == "CASE_3":
                case = "CASE_3"

            # PRESSURE → split into CASE_1 / CASE_2
            else:
                case = assign_case_direction(p1_won, server_is_p1)

            if case is None:
                continue

            case_counts[case] += 1
            stats[case]["total"] += 1

            if p1_won:
                stats[case]["p1_wins"] += 1
            else:
                stats[case]["p1_losses"] += 1

            if server_won:
                stats[case]["server_wins"] += 1
            else:
                stats[case]["server_losses"] += 1

    return stats, case_counts

# -----------------------------
# BUILD INDEX
# -----------------------------
def build_dict(seq, key):
    return {d[key]: dict(d, index=i) for i, d in enumerate(seq)}


# -----------------------------
# MAIN ANALYSIS
# -----------------------------
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

    points_by_match, count_points = points_object.load_points(CHARTED_MATCHES_BY_ID)
    print(f"Loaded Points ({count_points}): {len(points_by_match)}")

    stats, case_counts = analyze_points(points_by_match)
    print(stats)
    print(f"Case Counts: {case_counts}")
    print_results(stats, case_counts)
    # {'PRESSURE': {'total': 1091384, 'p1_wins': 551769, 'p1_losses': 539615, 'server_wins': 676027, 'server_losses': 415357}, 'CASE_3': {'total': 611733, 'p1_wins': 308331, 'p1_losses': 303402, 'server_wins': 378648, 'server_losses': 233085}}) Counter({'PRESSURE': 1091384, 'CASE_3': 611733})
    quit()

    # -----------------------------
    # GLOBAL STATS
    # -----------------------------
    case_counts = Counter()

    stats = defaultdict(lambda: {
        "total": 0,
        "server_wins": 0,
        "server_losses": 0
    })

    # -----------------------------
    # ITERATE ALL POINTS
    # -----------------------------
    for match_id, points in points_by_match.items():
        for p in points:

            # normalize types
            score = p.get("game_score")

            p1_is_server = int(p["server_player_number"]) == 1
            p1_won = int(p["point_winner_player_number"]) == 1

            case = assign_case(score, p1_is_server, p1_won)

            if case is None:
                continue

            server_won = (
                p["server_player_number"] ==
                p["point_winner_player_number"]
            )

            # update case counts
            case_counts[case] += 1

            # update stats per case
            stats[case]["total"] += 1
            if server_won:
                stats[case]["server_wins"] += 1
            else:
                stats[case]["server_losses"] += 1

    # -----------------------------
    # OUTPUT RESULTS
    # -----------------------------
    print("\n================ CASE DISTRIBUTION ================\n")
    for case, count in case_counts.items():
        print(case, count)

    print("\n================ SERVER PERFORMANCE BY CASE ================\n")
    for case, s in stats.items():
        total = s["total"]
        win_rate = s["server_wins"] / total if total else 0
        loss_rate = s["server_losses"] / total if total else 0

        print(case)
        print("total:", total)
        print("server_win_rate:", round(win_rate, 4))
        print("server_loss_rate:", round(loss_rate, 4))
        print("------------------------------------")

    print("\nDONE")