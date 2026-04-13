import numpy as np
import pandas as pd
from pathlib import Path
import pathlib
import sys

from sklearn.linear_model import LogisticRegression

sys.path.append(str(pathlib.Path(__file__).resolve().parent.parent.parent))

import tennisabstractscraper.models.data_objects as data_objects
from tennisabstractscraper.models.tennisabstract_data import TennisAbstractPointsData


DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
METADATA_DIR = DATA_DIR / "canonical/tennisabstract/_meta"


# =========================================================
# 1. STATE CLASSIFICATION
# =========================================================
def assign_state(score_state):

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
        return 0   # NEUTRAL
    if score_state in pressure:
        return 1   # PRESSURE
    return None


# =========================================================
# 2. DATASET BUILDER (DOUBLE FAULT MODEL)
# =========================================================
def build_dataset(points_by_match):

    rows = []

    for _, points in points_by_match.items():
        for p in points:

            state = assign_state(p.get("game_score"))
            if state is None:
                continue

            is_double_fault = int(p.get("is_double") or 0)
            p1_is_server = int(p["server_player_number"]) == 1

            rows.append({
                "double_fault": is_double_fault,
                "pressure": state,
                "p1_is_server": int(p1_is_server)
            })

    return pd.DataFrame(rows)


# =========================================================
# 3. LOGISTIC MODEL
# =========================================================
def run_logit(df):

    X = df[["pressure", "p1_is_server"]]
    y = df["double_fault"]

    model = LogisticRegression(
        solver="lbfgs",
        max_iter=1000,
        class_weight="balanced"  # important because DF is rare
    )

    model.fit(X, y)

    return model


# =========================================================
# 4. INTERPRETATION
# =========================================================
def print_results(model, df):

    X = df[["pressure", "p1_is_server"]]
    y = df["double_fault"]

    preds = model.predict(X)

    pressure_rate = df[df["pressure"] == 1]["double_fault"].mean()
    neutral_rate = df[df["pressure"] == 0]["double_fault"].mean()

    print("\n================ DOUBLE FAULT ANALYSIS ================\n")

    print("Observed probabilities:")
    print(f"  P(DF | Neutral):  {neutral_rate:.6f}")
    print(f"  P(DF | Pressure): {pressure_rate:.6f}")

    if neutral_rate > 0:
        print(f"\nPressure lift (ratio): {pressure_rate / neutral_rate:.3f}")

    print("\nLogistic regression results:")

    print(f"  Pressure effect (log-odds): {model.coef_[0][0]:.4f}")
    print(f"  Serve effect (log-odds):    {model.coef_[0][1]:.4f}")
    print(f"  Intercept:                  {model.intercept_[0]:.4f}")

    print("\nOdds Ratios:")
    print(f"  Pressure OR: {np.exp(model.coef_[0][0]):.4f}")
    print(f"  Serve OR:    {np.exp(model.coef_[0][1]):.4f}")


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

    points_by_match, count_points = points_object.load_points(CHARTED_MATCHES_BY_ID)

    print(f"Loaded Points ({count_points}): {len(points_by_match)}")

    df = build_dataset(points_by_match)

    model = run_logit(df)

    print_results(model, df)