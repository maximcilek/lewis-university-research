import pandas as pd
import numpy as np

from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
import matplotlib.pyplot as plt

# -------------------------
# 1. LOAD DATA
# -------------------------
path = "/home/mcilek/Github/maximcilek/lewis-university-research/data/analysis/double_faults.jsonl"
df = pd.read_json(path, lines=True)

print(df.shape)
print(df.columns)

# -------------------------
# 2. CLEAN
# -------------------------
df["point"] = pd.to_numeric(df["point"], errors="coerce")
df["is_double"] = pd.to_numeric(df["is_double"], errors="coerce").fillna(0)
df["match_pressure"] = pd.to_numeric(df["match_pressure"], errors="coerce").fillna(0)

df = df.dropna(subset=["point"])

# -------------------------
# 3. SORT (VERY IMPORTANT)
# -------------------------
df = df.sort_values(["match_id", "point"])

# -------------------------
# 4. ASSIGN MATCH INDEX (Y-axis)
# -------------------------
match_ids = df["match_id"].unique()
match_to_y = {m: i for i, m in enumerate(match_ids)}
df["y"] = df["match_id"].map(match_to_y)

# -------------------------
# 5. FILTER DOUBLE FAULTS ONLY
# -------------------------
dfs = df[df["is_double"] == 1].copy()

# -------------------------
# 6. PLOT
# -------------------------
plt.figure(figsize=(14, 8))

plt.scatter(
    dfs["point"],
    dfs["y"],
    c=dfs["match_pressure"],
    cmap="Reds",
    s=20,
    alpha=0.8
)

plt.title("Double Fault Timeline Across Matches")
plt.xlabel("Point Number (Match Timeline)")
plt.ylabel("Match Index")

plt.colorbar(label="Match Pressure")

plt.yticks(
    list(match_to_y.values())[::50],
    list(match_to_y.keys())[::50],
    fontsize=6
)

plt.tight_layout()
plt.show()




"""
df_features = [
    # MATCH CONTEXT
    "match_id",
    "match_date",
    "surface",
    "level",
    "gender",
    "best_of",
    "match_duration",

    # SERVER
    "server_player_id",
    "server_player_number",
    "server_rank",
    "server_seed",
    "server_country",
    "server_hand",
    "server_backhand",
    "server_height",

    # MATCH STATE
    "server_sets",
    "returner_sets",
    "server_games",
    "returner_games",
    "game_state",
    "game_score",
    "server_score",
    "returner_score",
    "total_sets_played",
    "is_tiebreaker_set",
    "tb_point_number",
    "tb_point",

    # PRESSURE
    "match_pressure",
    "set_pressure",
    "game_pressure",
    "server_set_diff",

    # SERVE OUTCOME
    "serve_number",
    "first_serve_rally",
    "first_serve_in_play",
    "is_ace",
    "is_unret",
    "is_forced_error",
    "is_unforced_error",

    # TARGET
    "is_double",

    # TEMPORAL FEATURES
    "point",
    "game",
    "set",
    "distance_from_last_df",
    "point_lag",
    "game_lag",
    "set_lag",
    "last_df_point",
]
"""