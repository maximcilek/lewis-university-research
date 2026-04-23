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

numeric_cols = [
    "distance_from_last_df", "point_lag", "game_lag", "set_lag",
    "serve_number", "match_pressure", "set_pressure", "game_pressure",
    "server_set_diff", "game_state", "first_serve_in_play",
    "is_ace", "is_unret", "is_forced_error", "is_unforced_error",
    "match_duration", "best_of"
]

for col in numeric_cols:
    df[col] = pd.to_numeric(df[col], errors="coerce")
df[numeric_cols] = df[numeric_cols].fillna(0)

# -------------------------
# 2. SELECT FEATURES
# -------------------------
features = [
    # temporal
    "distance_from_last_df",
    "point_lag",
    "game_lag",
    "set_lag",
    "serve_number",

    # pressure
    "match_pressure",
    "set_pressure",
    "game_pressure",
    "server_set_diff",
    "game_state",

    # serve behavior
    "first_serve_in_play",
    "is_ace",
    "is_unret",
    "is_forced_error",
    "is_unforced_error",

    # context (optional but useful for poster stratification)
    "surface",
    "level",
    "best_of",
    "match_duration",
    "gender"
]

# X = df[features].copy()
# -------------------------
# 3. CREATE STRUCTURAL FEATURES
# -------------------------

# Match progression
df["set_pos"] = df["total_sets_played"].astype(int)

df["game_pos"] = df["game"].astype(int)

# Normalize game position within match (VERY IMPORTANT for comparability)
df["game_pos_norm"] = df.groupby("match_id")["game_pos"].transform(
    lambda x: x / (x.max() if x.max() > 0 else 1)
)

# Pressure binning (for clean heatmaps)
df["pressure_bin"] = pd.cut(df["match_pressure"], bins=10)

df["set_bin"] = pd.cut(df["set_pos"], bins=5)

df["game_bin"] = pd.cut(df["game_pos_norm"], bins=10)

# -------------------------
# 4. HEATMAP 1: SET × PRESSURE
# -------------------------
heat_set_pressure = df.pivot_table(
    index="set_pos",
    columns="pressure_bin",
    values="is_double",
    aggfunc="mean",
    fill_value=0
)

plt.figure(figsize=(10,6))
plt.imshow(heat_set_pressure, aspect="auto", cmap="Reds")

plt.title("Double Fault Density: Set Position vs Match Pressure")
plt.xlabel("Match Pressure (binned)")
plt.ylabel("Set Position")

plt.colorbar(label="DF Rate")

plt.xticks(
    range(len(heat_set_pressure.columns)),
    heat_set_pressure.columns.astype(str),
    rotation=45
)
plt.yticks(range(len(heat_set_pressure.index)), heat_set_pressure.index)

plt.tight_layout()
plt.show()

# -------------------------
# 5. HEATMAP 2: SET × GAME POSITION
# -------------------------
heat_set_game = df.pivot_table(
    index="set_pos",
    columns="game_bin",
    values="is_double",
    aggfunc="mean",
    fill_value=0
)

plt.figure(figsize=(10,6))
plt.imshow(heat_set_game, aspect="auto", cmap="viridis")

plt.title("Double Fault Density: Set Position vs Game Progression")
plt.xlabel("Normalized Game Position")
plt.ylabel("Set Position")

plt.colorbar(label="DF Rate")

plt.xticks(
    range(len(heat_set_game.columns)),
    heat_set_game.columns.astype(str),
    rotation=45
)
plt.yticks(range(len(heat_set_game.index)), heat_set_game.index)

plt.tight_layout()
plt.show()

# -------------------------
# 6. HEATMAP 3: GAME × PRESSURE (within match structure)
# -------------------------
df["pressure_bin2"] = pd.cut(df["game_pressure"], bins=10)

heat_game_pressure = df.pivot_table(
    index="game_bin",
    columns="pressure_bin2",
    values="is_double",
    aggfunc="mean",
    fill_value=0
)

plt.figure(figsize=(10,6))
plt.imshow(heat_game_pressure, aspect="auto", cmap="magma")

plt.title("Double Fault Density: Game Position vs Game Pressure")
plt.xlabel("Game Pressure (binned)")
plt.ylabel("Game Progression")

plt.colorbar(label="DF Rate")

plt.xticks(
    range(len(heat_game_pressure.columns)),
    heat_game_pressure.columns.astype(str),
    rotation=45
)
plt.yticks(range(len(heat_game_pressure.index)), heat_game_pressure.index)

plt.tight_layout()
plt.show()

# -------------------------
# 7. SUMMARY STATISTICS (for poster)
# -------------------------
print("\nDF rate by set:")
print(df.groupby("set_pos")["is_double"].mean())

print("\nDF rate by pressure quantiles:")
print(df.groupby("pressure_bin")["is_double"].mean())








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