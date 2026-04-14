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

X = df[features].copy()

# -------------------------
# 3. CLEAN MISSING VALUES
# -------------------------
X = X.fillna(0)

# convert categorical -> numeric
X = pd.get_dummies(X, columns=["surface", "level", "gender"], drop_first=True)

# -------------------------
# 4. SCALE FEATURES
# -------------------------
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)

# -------------------------
# 5. CLUSTERING
# -------------------------
# k = 4  # try 3–6 for poster comparisons
# kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
# df["cluster"] = kmeans.fit_predict(X_scaled)
kmeans = KMeans(n_clusters=4, random_state=42, n_init=10)
df["cluster"] = kmeans.fit_predict(X_scaled)

# -------------------------
# 6. DIMENSION REDUCTION (for visualization)
# -------------------------
pca = PCA(n_components=2)
X_2d = pca.fit_transform(X_scaled)
df["pca_x"] = X_2d[:, 0]
df["pca_y"] = X_2d[:, 1]

plt.figure(figsize=(8,6))
scatter = plt.scatter(
    df["pca_x"],
    df["pca_y"],
    c=df["cluster"],
    cmap="tab10",
    alpha=0.7
)

plt.title("Double Fault Context Clusters (PCA Projection)")
plt.xlabel("PC1")
plt.ylabel("PC2")
plt.legend(*scatter.legend_elements(), title="Cluster")
plt.show()

# -------------------------
# 7. OUTPUT SUMMARY
# -------------------------
print(df["cluster"].value_counts())











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