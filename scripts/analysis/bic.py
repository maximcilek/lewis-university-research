import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import pathlib

from sklearn.preprocessing import StandardScaler
from hmmlearn.hmm import GaussianHMM

# =========================
# LOAD DATA
# =========================
DATA_DIR = pathlib.Path(__file__).resolve().parent.parent.parent / "data"

df = pd.concat(
    pd.read_json(
        DATA_DIR / "prod/charting_points_clean.jsonl",
        lines=True,
        chunksize=10000
    ),
    ignore_index=True
)

# =========================
# CLEANING
# =========================
df["is_double"] = df["is_double"].fillna(0).astype(int)

hmm_features = [
    "game_pressure",
    "set_pressure",
    "match_pressure",
    "rally_count"
]

df = df.dropna(subset=hmm_features + ["is_double"])

# =========================
# BUILD SEQUENCES
# =========================
sequences = []
lengths = []
index_map = []

for (match_id, player_id), group in df.groupby(["match_id", "server_player_id"]):
    group = group.sort_values("point_number")

    X_seq = group[hmm_features].values

    if len(X_seq) >= 20:
        sequences.append(X_seq)
        lengths.append(len(X_seq))
        index_map.extend(group.index.values)

print(f"{len(sequences)} sequences used")
print("avg sequence length:", np.mean(lengths))

X_all = np.vstack(sequences)

# =========================
# SCALE
# =========================
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X_all)

# =========================
# MULTI-START HMM FIT (STABILITY FIX)
# =========================
def fit_hmm_best(k, X, lengths, n_restarts=5):
    best_model = None
    best_score = -np.inf

    for seed in range(n_restarts):
        model = GaussianHMM(
            n_components=k,
            covariance_type="diag",
            n_iter=300,
            tol=1e-3,
            random_state=seed
        )

        model.fit(X, lengths)
        score = model.score(X, lengths)

        if score > best_score:
            best_model = model
            best_score = score

    return best_model, best_score

# =========================
# MODEL SELECTION (BIC)
# =========================
results = []
best_model = None
best_k = None
best_bic = np.inf

for k in range(2, 7):

    model, logL = fit_hmm_best(k, X_scaled, lengths)

    # parameter estimate (good enough for BIC ranking)
    n_params = k * X_scaled.shape[1] * 2
    bic = -2 * logL + n_params * np.log(len(X_scaled))

    results.append((k, logL, bic))

    print(f"States={k} | LogL={logL:.2f} | BIC={bic:.2f}")

    if bic < best_bic:
        best_bic = bic
        best_model = model
        best_k = k

# =========================
# FINAL MODEL
# =========================
print("\n================ BEST MODEL =================")
print(f"Optimal number of states: {best_k}")

# =========================
# ASSIGN STATES
# =========================
hidden_states = best_model.predict(X_scaled)

flat_index = np.array(index_map)[:len(hidden_states)]
df_model = df.loc[flat_index].copy()
df_model["state"] = hidden_states

# =========================
# STATE INTERPRETATION
# =========================
state_means = scaler.inverse_transform(best_model.means_)
state_df = pd.DataFrame(state_means, columns=hmm_features)
state_df["state"] = range(best_k)

# =========================
# DF RISK
# =========================
df_rate = df_model.groupby("state")["is_double"].mean().reset_index()

state_summary = state_df.merge(df_rate, on="state", how="left")

print("\n================ STATE SUMMARY =================")
print(state_summary)

# =========================
# =========================
# VISUAL (POSTER-READY)
# =========================
# =========================

fig, axes = plt.subplots(best_k, 1, figsize=(10, 2.2 * best_k), sharex=True)

if best_k == 1:
    axes = [axes]

for i, ax in enumerate(axes):
    row = state_summary.iloc[i]

    features = ["game_pressure", "set_pressure", "match_pressure"]
    values = [row[f] for f in features]

    color = plt.cm.Reds(row["is_double"] * 8)

    ax.bar(features, values, color=color)

    ax.set_title(f"State {int(row['state'])} | DF Rate: {row['is_double']:.3f}")

    ax.set_ylim(0, 1)
    ax.tick_params(axis='x', rotation=30)

axes[-1].set_xlabel("Context Features")
axes[0].set_ylabel("Feature Level")

plt.suptitle("Hidden Serving States + Double Fault Risk (HMM + Risk Layer)", fontsize=14)
plt.tight_layout()
plt.show()