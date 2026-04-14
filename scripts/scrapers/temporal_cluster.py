import pandas as pd
import numpy as np

import matplotlib.pyplot as plt

from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.metrics import silhouette_score

# =========================
# 1. LOAD DATA
# =========================
path = "/home/mcilek/Github/maximcilek/lewis-university-research/data/analysis/double_faults.jsonl"
df = pd.read_json(path, lines=True)

print("\n================ SHAPE ================")
print(df.shape)

print("\n================ COLUMNS ================")
print(df.columns.tolist())

# =========================
# 2. BASIC CLEANING
# =========================
numeric_cols = [
    "distance_from_last_df", "point_lag", "game_lag", "set_lag",
    "serve_number", "match_pressure", "set_pressure", "game_pressure",
    "server_set_diff", "game_state", "first_serve_in_play",
    "is_ace", "is_unret", "is_forced_error", "is_unforced_error",
    "match_duration", "best_of",
    "total_sets_played", "point", "game", "set"
]

for col in numeric_cols:
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors="coerce")

df[numeric_cols] = df[numeric_cols].fillna(0)

# =========================
# 3. FEATURE SET
# =========================
features = [
    "distance_from_last_df",
    "point_lag",
    "game_lag",
    "set_lag",
    "serve_number",
    "match_pressure",
    "set_pressure",
    "game_pressure",
    "server_set_diff",
    "game_state",
    "first_serve_in_play",
    "is_ace",
    "is_unret",
    "is_forced_error",
    "is_unforced_error",
    "surface",
    "level",
    "gender",
    "best_of",
    "match_duration",
    "total_sets_played"
]

X = df[features].copy()
X = X.fillna(0)

# categorical encoding
X = pd.get_dummies(X, columns=["surface", "level", "gender"], drop_first=True)

# =========================
# 4. SCALE
# =========================
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)

# =========================
# 5. CLUSTERING
# =========================
k = 4
kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
df["cluster"] = kmeans.fit_predict(X_scaled)

# =========================
# 6. QUALITY METRICS
# =========================
sil = silhouette_score(X_scaled, df["cluster"])
inertia = kmeans.inertia_

print("\n================ CLUSTER QUALITY ================")
print(f"Silhouette Score: {sil:.4f} (higher is better, ~0.2–0.5 is typical)")
print(f"Inertia (within-cluster variance): {inertia:.2f}")

# =========================
# 7. PCA VISUALIZATION
# =========================
pca = PCA(n_components=2)
X_2d = pca.fit_transform(X_scaled)

df["pca_x"] = X_2d[:, 0]
df["pca_y"] = X_2d[:, 1]

plt.figure(figsize=(8,6))
plt.scatter(df["pca_x"], df["pca_y"], c=df["cluster"], cmap="tab10", alpha=0.6)
plt.title("Double Fault Clusters (PCA View)")
plt.xlabel("PC1")
plt.ylabel("PC2")
plt.show()

# =========================
# 8. CLUSTER PROFILING (VERY IMPORTANT FOR POSTER)
# =========================
print("\n================ CLUSTER PROFILES ================")

profile = df.groupby("cluster")[[
    "distance_from_last_df",
    "point_lag",
    "game_lag",
    "set_lag",
    "serve_number",
    "match_pressure",
    "set_pressure",
    "game_pressure",
    "game_state",
    "total_sets_played"
]].mean()

print(profile)

# =========================
# 9. DOUBLE FAULT DISTRIBUTION BY SET / GAME
# =========================
print("\n================ TEMPORAL DISTRIBUTION ================")

print("By Set:")
print(df.groupby("set")["is_double"].mean())

print("\nBy Game (binned):")
df["game_bin"] = pd.cut(df["game"], bins=10)
print(df.groupby("game_bin")["is_double"].mean())










"""
plt.figure(figsize=(14, 8))

for set_id in sorted(dfs["set"].unique()):
    subset = dfs[dfs["set"] == set_id]

    plt.scatter(
        subset["point"],
        subset["game"],
        alpha=0.6,
        s=20,
        label=f"Set {set_id}"
    )

plt.title("Layered Double Fault Structure (Set Separation)")
plt.xlabel("Point Number")
plt.ylabel("Game Number")
plt.legend()
plt.show()
"""

"""
plt.figure(figsize=(12, 7))

scatter = plt.scatter(
    dfs["point"],
    dfs["game"],
    c=dfs["match_pressure"],
    cmap="viridis",
    alpha=0.7,
    s=20
)

plt.colorbar(scatter, label="Match Pressure")

plt.title("Double Faults: Point vs Game Position")
plt.xlabel("Point Number")
plt.ylabel("Game Number")

plt.show()
"""

"""
plt.figure(figsize=(12, 7))

scatter = plt.scatter(
    dfs["point"],
    dfs["set"],
    c=dfs["match_pressure"],
    cmap="coolwarm",
    alpha=0.7,
    s=20
)

plt.colorbar(scatter, label="Match Pressure")

plt.title("Double Fault Temporal Structure: Point vs Set")
plt.xlabel("Point Number (Match Timeline)")
plt.ylabel("Set Number")

plt.yticks(sorted(dfs["set"].unique()))

plt.show()
"""