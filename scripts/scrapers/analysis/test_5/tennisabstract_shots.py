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
        return 0
    if score_state in pressure:
        return 1
    return None


# =========================================================
# 2. DATASET BUILDER (WITH FIXED EFFECTS)
# =========================================================
def build_dataset(points_by_match, charted_matches_by_id):

    rows = []

    for match_id, points in points_by_match.items():

        match_meta = charted_matches_by_id.get(match_id, {})
        p1_id = match_meta.get("player_1_id")
        p2_id = match_meta.get("player_2_id")

        for p in points:

            state = assign_state(p.get("game_score"))
            if state is None:
                continue

            is_double = int(p.get("is_double") or 0)

            gender = p.get("gender")
            if gender is None:
                continue

            gender_bin = 1 if gender in ["W", "women", "WTA"] else 0

            p1_is_server = int(p["server_player_number"]) == 1

            rows.append({
                "double_fault": is_double,
                "pressure": state,
                "gender": gender_bin,
                "p1_is_server": int(p1_is_server),

                # =========================
                # FIXED EFFECTS
                # =========================
                "p1_id": p1_id,
                "p2_id": p2_id,
            })

    df = pd.DataFrame(rows)

    # interaction term
    df["pressure_gender"] = df["pressure"] * df["gender"]

    return df


# =========================================================
# 3. MODEL (WITH FIXED EFFECTS VIA DUMMIES)
# =========================================================
def run_logit(df):

    # One-hot encode fixed effects
    df_fe = pd.get_dummies(df, columns=["p1_id", "p2_id"], drop_first=True)

    X = df_fe.drop(columns=["double_fault"])
    y = df_fe["double_fault"]

    model = LogisticRegression(
        solver="saga",          # required for large sparse FE models
        max_iter=200,
        n_jobs=-1,
        class_weight="balanced"
    )

    model.fit(X, y)

    return model, df_fe


# =========================================================
# 4. INTERPRETATION
# =========================================================
def print_results(model, df, df_fe):

    coef = model.coef_[0]

    feature_names = df_fe.drop(columns=["double_fault"]).columns

    print("\n================ DOUBLE FAULT MODEL (WITH FIXED EFFECTS) ================\n")

    # Extract main structural coefficients
    def get(name):
        idx = list(feature_names).index(name)
        return coef[idx]

    print("CORE EFFECTS (LOG-ODDS):")
    print(f"  Pressure effect:        {get('pressure'):.4f}")
    print(f"  Gender effect:          {get('gender'):.4f}")
    print(f"  Pressure × Gender:      {get('pressure_gender'):.4f}")
    print(f"  Serve effect:           {get('p1_is_server'):.4f}")

    print("\nODDS RATIOS:")
    print(f"  Pressure OR:            {np.exp(get('pressure')):.4f}")
    print(f"  Gender OR:              {np.exp(get('gender')):.4f}")
    print(f"  Interaction OR:         {np.exp(get('pressure_gender')):.4f}")
    print(f"  Serve OR:               {np.exp(get('p1_is_server')):.4f}")

    print("\n================ INTERPRETATION =================\n")

    print("""
    FIXED EFFECTS INCLUDED:
    - Player identity controls (p1_id, p2_id)

    WHY THIS MATTERS:
    - Removes bias from inherently 'bad servers'
    - Controls for elite players vs weaker players
    - Isolates true pressure & gender effects

    INTERPRETATION RULES:

    1. Gender coefficient:
       baseline DF difference (women vs men)

    2. Pressure coefficient:
       average psychological pressure effect

    3. Interaction term:
       differential pressure sensitivity by gender

    4. Fixed effects:
       all player-specific tendencies absorbed → cleaner causal estimate
    """)


# =========================================================
# 5. INDEX
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

    df = build_dataset(points_by_match, CHARTED_MATCHES_BY_ID)

    model, df_fe = run_logit(df)

    print_results(model, df, df_fe)