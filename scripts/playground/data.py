import pandas as pd
import numpy as np

from scipy import stats
import statsmodels.api as sm
import statsmodels.formula.api as smf
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, roc_auc_score
from datetime import datetime
import matplotlib.pyplot as plt
from pathlib import Path
import pathlib
import sys
sys.path.append(str(pathlib.Path(__file__).resolve().parent.parent.parent))

DATA_DIR = pathlib.Path(__file__).resolve().parent.parent.parent / "data"
METADATA_DIR = DATA_DIR / "canonical/tennisabstract/_meta"

# df = pd.read_json(DATA_DIR / "prod/charting_points_clean.jsonl", lines=True)

# print(df.info())
# print("--------------------------------------------")
# print(df.head(20))


print("==================================")


chunks = []
for chunk in pd.read_json(DATA_DIR / "prod/charting_points_clean.jsonl", lines=True, chunksize=10000):
    chunks.append(chunk)
df = pd.concat(chunks, ignore_index=True)
df["is_double"] = df["is_double"].fillna(-1)
df["second_serve_in_play"] = df["second_serve_in_play"].fillna(-1)

# =========================
# LOAD YOUR DATA
# =========================
# Replace this with your actual load
# df = pd.read_parquet("your_file.parquet")
# df = pd.read_csv("your_file.csv")

# Example placeholder:
df = df.copy()  # assume already loaded

TARGET = "is_server_winner"

# =========================
# BASIC CLEANING
# =========================
df = df.replace([np.inf, -np.inf], np.nan)

# Keep only rows with target
df = df[df[TARGET].notna()]

# =========================
# NUMERIC COLUMNS
# =========================
numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()

# =========================
# 1. CORRELATION
# =========================
print("\n================ CORRELATION ================\n")

corr = df[numeric_cols].corr()[TARGET].sort_values(ascending=False)
print(corr)

# =========================
# 2. T-TESTS (WIN vs LOSS)
# =========================
print("\n================ T-TESTS ================\n")

features_to_test = [
    "game_pressure",
    "set_pressure",
    "match_pressure",
    "df_ratio_last_5_serves",
    "df_distance"
]

for col in features_to_test:
    if col not in df.columns:
        continue

    win = df[df[TARGET] == 1][col].dropna()
    lose = df[df[TARGET] == 0][col].dropna()

    if len(win) > 0 and len(lose) > 0:
        t_stat, p_val = stats.ttest_ind(win, lose, equal_var=False)
        print(f"{col}: t={t_stat:.4f}, p={p_val:.6f}")

# =========================
# 3. LOGISTIC REGRESSION
# =========================
print("\n================ LOGISTIC REGRESSION ================\n")

features = [
    "server_point_diff",
    "game_pressure",
    "set_pressure",
    "match_pressure",
    "df_ratio_last_5_serves",
    "df_distance"
]

features = [f for f in features if f in df.columns]

df_model = df[features + [TARGET]].dropna()

X = df_model[features]
y = df_model[TARGET]

X = sm.add_constant(X)

logit_model = sm.Logit(y, X).fit()
print(logit_model.summary())

# =========================
# 4. RANDOM FOREST IMPORTANCE
# =========================
print("\n================ RANDOM FOREST ================\n")

X = df_model[features]
y = df_model[TARGET]

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)

rf = RandomForestClassifier(n_estimators=100, random_state=42)
rf.fit(X_train, y_train)

y_pred = rf.predict(X_test)
y_prob = rf.predict_proba(X_test)[:, 1]

print("Accuracy:", accuracy_score(y_test, y_pred))
print("ROC-AUC:", roc_auc_score(y_test, y_prob))

importances = pd.Series(rf.feature_importances_, index=features)
print("\nFeature Importances:")
print(importances.sort_values(ascending=False))

# =========================
# 5. INTERACTION EFFECT
# =========================
print("\n================ INTERACTION EFFECT ================\n")

if "df_ratio_last_5_serves" in df.columns and "game_pressure" in df.columns:
    df["df_pressure_interaction"] = (
        df["df_ratio_last_5_serves"] * df["game_pressure"]
    )

    formula = "is_server_winner ~ df_ratio_last_5_serves + game_pressure + df_pressure_interaction"

    interaction_model = smf.logit(formula, data=df).fit()
    print(interaction_model.summary())

# =========================
# 6. GROUPED MEANS (INTERPRETABILITY)
# =========================
print("\n================ GROUPED MEANS ================\n")

for col in ["df_ratio_last_5_serves", "df_distance"]:
    if col in df.columns:
        print(f"\n{col}:")
        print(df.groupby(TARGET)[col].mean())

# =========================
# 7. SANITY CHECKS
# =========================
print("\n================ SANITY CHECKS ================\n")

print("\nTarget distribution:")
print(df[TARGET].value_counts(normalize=True))

print("\nMissing values:")
print(df.isnull().mean().sort_values(ascending=False).head(15))