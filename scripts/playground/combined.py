import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from hmmlearn.hmm import GaussianHMM
import seaborn as sns
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
df["is_double"] = df["is_double"].fillna(0).astype(int)

# optional sampling for speed
# df = df.sample(200_000, random_state=42).reset_index(drop=True)

# =========================
# FEATURE SET (HMM: NO OUTCOME LEAKAGE)
# =========================
hmm_features = [
    "game_pressure",
    "set_pressure",
    "match_pressure",
    "rally_count"
]

df = df.dropna(subset=hmm_features + ["is_double"])

# BUILD SEQUENCES
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

        
print(len(sequences), "sequences used")
print("avg length:", np.mean(lengths))
X_all = np.vstack(sequences)

# SCALE
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X_all)

results = []
for k in range(2, 6):
    hmm = GaussianHMM(n_components=k, covariance_type="diag", n_iter=200, random_state=42)
    hmm.fit(X_scaled, lengths)
    
    logL = hmm.score(X_scaled, lengths)
    
    n_params = k * len(hmm_features) * 2  # rough estimate
    bic = -2 * logL + n_params * np.log(len(X_scaled))
    
    results.append((k, logL, bic))

for r in results:
    print(f"States={r[0]} | LogL={r[1]:.2f} | BIC={r[2]:.2f}")
quit()


# =========================
# HMM (LAYER 1: CONTEXT STATES)
# =========================
hmm = GaussianHMM(
    n_components=6,
    covariance_type="diag",
    n_iter=200,
    random_state=42,
    verbose=True
)

hmm.fit(X_scaled, lengths)

hidden_states = hmm.predict(X_scaled)

# map back to df
flat_index = np.array(index_map)[:len(hidden_states)]
df_model = df.loc[flat_index].copy()
df_model["state"] = hidden_states

# =========================
# STATE INTERPRETATION
# =========================
state_means_scaled = hmm.means_
state_means = scaler.inverse_transform(state_means_scaled)

state_df = pd.DataFrame(state_means, columns=hmm_features)
state_df["state"] = range(len(state_df))

print("\n================ HMM STATE PROFILES ================\n")
print(state_df)

# =========================
# DF RATE BY STATE
# =========================
df_rate = df_model.groupby("state")["is_double"].mean()

print("\n================ DF RATE BY STATE ================\n")
print(df_rate.sort_values(ascending=False))

# =========================
# =========================
# LAYER 2: LOGISTIC REGRESSION PER STATE
# =========================
# =========================

print("\n================ LOGISTIC REGRESSION PER STATE ================\n")

logit_models = {}
state_risk_summary = []

for s in sorted(df_model["state"].unique()):
    d = df_model[df_model["state"] == s]

    X = d[hmm_features]
    y = d["is_double"]

    if y.sum() < 5:
        continue

    logit = LogisticRegression(max_iter=200)
    logit.fit(X, y)

    prob = y.mean()

    state_risk_summary.append({
        "state": s,
        "empirical_df_rate": prob
    })

    logit_models[s] = logit

state_risk_df = pd.DataFrame(state_risk_summary)
print(state_risk_df)

# =========================
# VISUALIZATION 1: STATE TIMELINE
# =========================

# Combine context + risk
state_summary = state_df.merge(
    state_risk_df,
    on="state",
    how="left"
)

print("\n================ FINAL INTERPRETATION =================\n")

for _, row in state_summary.iterrows():
    print(f"State {int(row['state'])}:")
    print(f"  Game pressure: {row['game_pressure']:.3f}")
    print(f"  Set pressure: {row['set_pressure']:.3f}")
    print(f"  Match pressure: {row['match_pressure']:.3f}")
    print(f"  DF rate: {row['empirical_df_rate']:.4f}")
    print()

# fig, axes = plt.subplots(1, len(state_summary), figsize=(16, 4), sharey=True)
fig, axes = plt.subplots(2, 2, figsize=(10, 8), sharey=True)
axes = axes.flatten()
for i, ax in enumerate(axes):
    if i >= len(state_summary):
        ax.axis("off")
        continue

    row = state_summary.iloc[i]

    features_plot = ["game_pressure", "set_pressure", "match_pressure"]
    values = [row[f] for f in features_plot]

    # color based on DF risk
    risk = row["empirical_df_rate"]
    color = plt.cm.Reds(risk * 5)

    ax.bar(features_plot, values, color=color)

    ax.set_title(f"State {int(row['state'])}")

    # DF rate label
    ax.text(
        0.5, 1.10,
        f"DF Rate: {risk:.3f}",
        transform=ax.transAxes,
        ha="center",
        fontsize=11,
        fontweight="bold"
    )

    ax.set_ylim(0, 1)

    # Only bottom row shows x labels
    if i < 2:
        ax.set_xticklabels([])
        ax.set_xlabel("")
    else:
        ax.tick_params(axis='x', rotation=30)

# Only left column gets y-labels
axes[0].set_ylabel("Feature Value")
axes[2].set_ylabel("Feature Value")

plt.suptitle("Serving Context States and Double Fault Risk", fontsize=14)
plt.tight_layout()
plt.show()

"""
state_summary = df_model.groupby("state").agg(
    df_rate=("is_double", "mean"),
    freq=("state", "count"),
    game_pressure=("game_pressure", "mean")
)

state_summary["freq"] = state_summary["freq"] / state_summary["freq"].sum()

plt.figure(figsize=(7,6))

scatter = plt.scatter(
    state_summary["freq"],
    state_summary["df_rate"],
    s=state_summary["game_pressure"] * 1000,  # bubble size
)

for i in state_summary.index:
    plt.text(
        state_summary.loc[i, "freq"],
        state_summary.loc[i, "df_rate"],
        f"State {i}",
        fontsize=10
    )

plt.xlabel("How Often State Occurs")
plt.ylabel("Double Fault Risk")
plt.title("Serving States: Frequency vs Risk vs Pressure")
plt.show()
"""


#plot_df = state_df.copy()
#plot_df["df_rate"] = df_model.groupby("state")["is_double"].mean().values

#plot_df = plot_df.set_index("state")

#plt.figure(figsize=(10, 5))
#sns.heatmap(plot_df, annot=True, cmap="coolwarm", fmt=".2f")

#plt.title("Hidden State Profiles + Double Fault Risk")
#plt.show()

























"""
fig, ax = plt.subplots(figsize=(16, 5))

sample_matches = df_model["match_id"].drop_duplicates().sample(5, random_state=42)

for mid in sample_matches:
    m = df_model[df_model["match_id"] == mid].sort_values("point_number")
    
    ax.plot(
        m["point_number"],
        m["state"],
        color="gray",
        alpha=0.3,
        linewidth=1
    )

# highlight one match in color
example_match = sample_matches.iloc[0]
m = df_model[df_model["match_id"] == example_match].sort_values("point_number")

ax.plot(
    m["point_number"],
    m["state"],
    color="black",
    linewidth=2,
    label="Example Match"
)

df_spikes = m[m["is_double"] == 1]

ax.scatter(
    df_spikes["point_number"],
    df_spikes["state"],
    color="red",
    marker="x",
    s=80,
    label="Double Fault"
)

ax.set_title("Hidden States Across Multiple Matches (Temporal Structure)")
ax.set_xlabel("Point Number")
ax.set_ylabel("State")
ax.legend()
plt.show()
"""

"""
example_match = df_model["match_id"].iloc[0]
match_df = df_model[df_model["match_id"] == example_match].sort_values("point_number")

# =========================
# METRICS
# =========================
df_rate = df_model.groupby("state")["is_double"].mean()

state_empirical = (
    df_model.groupby("state")["is_double"]
    .mean()
    .reset_index()
    .rename(columns={"is_double": "empirical_df_rate"})
)

# =========================
# FIGURE LAYOUT (TOP = TIMELINE, BOTTOM = 2 BAR CHARTS)
# =========================
fig = plt.figure(figsize=(16, 10))
gs = fig.add_gridspec(2, 2, height_ratios=[2, 1])

# =========================
# TOP: TIMELINE (FULL WIDTH)
# =========================
ax0 = fig.add_subplot(gs[0, :])

ax0.plot(
    match_df["point_number"],
    match_df["state"],
    linewidth=2,
    label="Hidden State"
)

df_spikes = match_df[match_df["is_double"] == 1]

ax0.scatter(
    df_spikes["point_number"],
    df_spikes["state"],
    color="red",
    marker="x",
    s=120,
    label="Double Fault"
)

ax0.set_title(f"Hidden Serving States Over Match Time\n{example_match}")
ax0.set_xlabel("Point Number")
ax0.set_ylabel("State")
ax0.legend()

# =========================
# BOTTOM LEFT: MODEL DF RATE
# =========================
ax1 = fig.add_subplot(gs[1, 0])

df_rate.sort_index().plot(
    kind="bar",
    ax=ax1,
    color="steelblue"
)

ax1.set_title("DF Rate by Hidden State (Model-based)")
ax1.set_xlabel("State")
ax1.set_ylabel("DF Probability")

# =========================
# BOTTOM RIGHT: EMPIRICAL DF RATE
# =========================
ax2 = fig.add_subplot(gs[1, 1])

state_empirical.set_index("state")["empirical_df_rate"].plot(
    kind="bar",
    ax=ax2,
    color="darkorange"
)

ax2.set_title("Empirical DF Risk by State")
ax2.set_xlabel("State")
ax2.set_ylabel("Observed DF Rate")

# =========================
# FINAL STYLE
# =========================
plt.tight_layout()
plt.show()

# =========================
# FINAL SUMMARY OUTPUT
# =========================
print("\n================ FINAL INTERPRETATION =================\n")

for i, row in state_df.iterrows():
    print(f"State {int(row['state'])}:")
    print(f"  Pressure level: {row['game_pressure']:.3f}")
    print(f"  Set pressure: {row['set_pressure']:.3f}")
    print(f"  Match pressure: {row['match_pressure']:.3f}")
    print(f"  DF rate: {df_rate.loc[i]:.4f}")
    print()
"""