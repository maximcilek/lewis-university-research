import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

from sklearn.preprocessing import StandardScaler
from hmmlearn.hmm import GaussianHMM
import pathlib

# =========================
# LOAD DATA
# =========================
DATA_DIR = pathlib.Path(__file__).resolve().parent.parent.parent / "data"

chunks = []
for chunk in pd.read_json(
    DATA_DIR / "prod/charting_points_clean.jsonl",
    lines=True,
    chunksize=10000
):
    chunks.append(chunk)

df = pd.concat(chunks, ignore_index=True)

# =========================
# CLEANING
# =========================
df["is_double"] = df["is_double"].fillna(0).astype(float)

# =========================
# FEATURE ENGINEERING
# =========================
df["df_ema_20"] = df["is_double"].ewm(span=20, adjust=False).mean()

# Reduce dataset (optional)
# df = df.sample(200_000, random_state=42).reset_index(drop=True)

# =========================
# FEATURES
# =========================
features = [
    # Pressure / context
    "game_pressure",
    "set_pressure",
    "match_pressure",
    "server_point_diff",
    "rally_count", # fatigue
    "df_ema_20",
]

df = df.dropna(subset=features).reset_index(drop=True)

# =========================
# BUILD SEQUENCES (FIXED)
# =========================
sequences = []
lengths = []
all_indices = []

for (match_id, player_id), group in df.groupby(["match_id", "server_player_id"]):
    group = group.sort_values("point_number")

    X_seq = group[features].values

    if len(X_seq) >= 20:
        sequences.append(X_seq)
        lengths.append(len(X_seq))
        all_indices.extend(group.index.values)

# stack sequences for HMM
X_all = np.vstack(sequences)

# =========================
# SCALE
# =========================
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X_all)

# =========================
# TRAIN HMM
# =========================
model = GaussianHMM(
    n_components=4,
    covariance_type="diag",
    n_iter=200,
    tol=1e-3,
    random_state=42,
    verbose=True
)

model.fit(X_scaled, lengths)

# =========================
# PREDICT STATES
# =========================
hidden_states = model.predict(X_scaled)

# =========================
# ALIGN BACK TO DATA (CORRECT)
# =========================
df_model = df.loc[all_indices].copy()
df_model["state"] = hidden_states

# =========================
# STATE MEANS (REAL SCALE)
# =========================
state_means = scaler.inverse_transform(model.means_)
state_means_df = pd.DataFrame(state_means, columns=features)

print("\n================ STATE MEANS (REAL SCALE) ================\n")
print(state_means_df)

# =========================
# DF RATE BY STATE
# =========================
print("\n================ DF RATE BY STATE ================\n")
df_rate = df_model.groupby("state")["is_double"].mean()
print(df_rate)

# =========================
# TRANSITION MATRIX
# =========================
print("\n================ TRANSITION MATRIX ================\n")
print(model.transmat_)

# =========================
# FEATURE MEANS BY STATE
# =========================
print("\n================ FEATURE MEANS BY STATE ================\n")
print(df_model.groupby("state")[features].mean())

# =========================
# VISUALIZATION 1: STATE + DF SPIKES
# =========================
example_match = df_model["match_id"].iloc[0]

match_df = df_model[df_model["match_id"] == example_match]
match_df = match_df.sort_values("point_number")

plt.figure(figsize=(14, 5))

plt.plot(match_df["point_number"], match_df["state"], label="Hidden State")

df_spikes = match_df[np.isclose(match_df["is_double"], 1)]

plt.scatter(
    df_spikes["point_number"],
    df_spikes["state"],
    marker="x",
    s=120,
    label="Double Fault"
)

plt.title(f"HMM States + DF Spikes\n{example_match}")
plt.xlabel("Point Number")
plt.ylabel("State")
plt.legend()
plt.show()

# =========================
# VISUALIZATION 2: DF RATE PER STATE
# =========================
plt.figure()
df_rate.sort_index().plot(kind="bar")
plt.title("Double Fault Rate by State")
plt.xlabel("State")
plt.ylabel("DF Probability")
plt.show()

# =========================
# VISUALIZATION 3: STATE BEFORE DF
# =========================
prev_states = []

for (match_id, player_id), group in df_model.groupby(["match_id", "server_player_id"]):
    group = group.sort_values("point_number").reset_index(drop=True)

    for i in range(1, len(group)):
        if np.isclose(group.loc[i, "is_double"], 1):
            prev_states.append(group.loc[i - 1, "state"])

prev_states = pd.Series(prev_states)

plt.figure()
prev_states.value_counts().sort_index().plot(kind="bar")
plt.title("State BEFORE Double Fault")
plt.xlabel("State")
plt.ylabel("Count")
plt.show()

print("\nState before DF distribution:")
print(prev_states.value_counts(normalize=True))