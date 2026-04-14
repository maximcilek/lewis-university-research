import numpy as np
import pandas as pd
from pathlib import Path
import pathlib
import sys

import statsmodels.api as sm

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
# 2. BUILD DATASET
# =========================================================
def build_dataset(points_by_match):

    rows = []

    for _, points in points_by_match.items():
        for p in points:

            state = assign_state(p.get("game_score"))
            if state is None:
                continue

            is_double_fault = int(p.get("is_double") or 0)

            server_is_p1 = int(p["server_player_number"]) == 1
            server_id = p["player_1_id"] if server_is_p1 else p["player_2_id"]

            rows.append({
                "double_fault": is_double_fault,
                "pressure": state,
                "gender": 1 if p.get("gender") == "W" else 0,
                "p1_is_server": int(server_is_p1),
                "server_id": server_id
            })

    return pd.DataFrame(rows)


# =========================================================
# 3. STATS MODELS LOGIT WITH FIXED EFFECTS
# =========================================================
def run_logit(df):

    # -----------------------------
    # FIXED EFFECTS (DUMMIES)
    # -----------------------------
    df_fe = pd.get_dummies(
        df,
        columns=["p1_id", "p2_id"],
        drop_first=True
    )

    y = df_fe["double_fault"]

    X = df_fe.drop(columns=["double_fault"])

    # add intercept (IMPORTANT for statsmodels)
    X = sm.add_constant(X)

    model = sm.Logit(y, X)

    result = model.fit(
        maxiter=200,
        disp=True
    )

    return result, X


# =========================================================
# 4. RESULTS (ACADEMIC OUTPUT)
# =========================================================
def print_results(result, X):

    print("\n================ LOGISTIC REGRESSION (STATS MODELS) ================\n")

    print(result.score)

    # odds ratios
    params = result.get_params()
    print(result.__dir__())
    quit()
    conf = result.conf_int()

    print("\n================ ODDS RATIOS =================\n")

    for name in ["pressure", "gender", "pressure_gender", "p1_is_server"]:
        if name in params.index:
            or_val = np.exp(params[name])
            ci_low = np.exp(conf.loc[name][0])
            ci_high = np.exp(conf.loc[name][1])

            print(f"{name}: OR={or_val:.4f}  CI=[{ci_low:.4f}, {ci_high:.4f}]")


# =========================================================
# 5. INDEX
# =========================================================
def build_dict(seq, key):
    return {d[key]: dict(d, index=i) for i, d in enumerate(seq)}

from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import OneHotEncoder
from scipy.sparse import hstack

def run_logit_sparse(df):
    print(df.columns)

    # Base features
    X_base = df[["pressure", "p1_is_server", "gender"]].values

    # Player fixed effects (sparse)
    encoder = OneHotEncoder(handle_unknown="ignore", sparse_output=True)
    X_players = encoder.fit_transform(df[["server_id"]])

    # Combine
    X = hstack([X_base, X_players])

    y = df["double_fault"].values

    model = LogisticRegression(
        max_iter=1000,
        class_weight="balanced"
    )

    model.fit(X, y)

    return model, encoder
# =========================================================
# 6. MAIN
# =========================================================
if __name__ == "__main__":

    input_csv = DATA_DIR / "prod/charting_points.jsonl"

    points_object = TennisAbstractPointsData(
        input_csv,
        METADATA_DIR / "rally_codes.json"
    )

    matches = data_objects.JsonlDataObject(
        DATA_DIR / "prod/charting_matches.jsonl"
    ).data

    matches_by_id = build_dict(matches, "match_id")

    points_by_match, count_points = points_object.load_points(matches_by_id)

    print(f"Loaded Points ({count_points}): {len(points_by_match)}")

    """df = build_dataset(points_by_match)

    result, X = run_logit_sparse(df)

    print_results(result, X)"""