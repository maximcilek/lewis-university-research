import numpy as np
import pandas as pd
from pathlib import Path
import pathlib
import sys

from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report

sys.path.append(str(pathlib.Path(__file__).resolve().parent.parent.parent))

import tennisabstractscraper.models.data_objects as data_objects
from tennisabstractscraper.models.tennisabstract_data import TennisAbstractPointsData


DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
METADATA_DIR = DATA_DIR / "canonical/tennisabstract/_meta"


# =========================================================
# 1. STATE CLASSIFICATION (EXPLANATORY VARIABLE)
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
# 2. FEATURE ENGINEERING
# =========================================================
def build_dataset(points_by_match):
    rows = []

    for _, points in points_by_match.items():
        for p in points:

            state = assign_state(p.get("game_score"))
            if state is None:
                continue

            p1_won = int(p["point_winner_player_number"]) == 1
            p1_is_server = int(p["server_player_number"]) == 1

            rows.append({
                "p1_won": int(p1_won),
                "pressure": state,
                "p1_is_server": int(p1_is_server),
            })

    return pd.DataFrame(rows)


# =========================================================
# 3. LOGISTIC REGRESSION
# =========================================================
def run_logit(df):

    X = df[["pressure", "p1_is_server"]]
    y = df["p1_won"]

    model = LogisticRegression(
        solver="lbfgs",
        max_iter=1000
    )

    model.fit(X, y)

    return model


# =========================================================
# 4. RESULTS INTERPRETATION (ACADEMIC FORMAT)
# =========================================================
def print_results(model, df):

    X = df[["pressure", "p1_is_server"]]
    y = df["p1_won"]

    preds = model.predict(X)

    print("\n================ LOGISTIC REGRESSION RESULTS ================\n")

    print("Coefficients:")
    print(f"  Pressure effect (log-odds): {model.coef_[0][0]:.4f}")
    print(f"  Serve effect (log-odds):    {model.coef_[0][1]:.4f}")
    print(f"  Intercept:                  {model.intercept_[0]:.4f}")

    print("\nOdds Ratios:")
    print(f"  Pressure OR: {np.exp(model.coef_[0][0]):.4f}")
    print(f"  Serve OR:    {np.exp(model.coef_[0][1]):.4f}")

    print("\nClassification report:")
    print(classification_report(y, preds))


# =========================================================
# 5. INDEXING
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