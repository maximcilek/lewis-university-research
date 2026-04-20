import pandas as pd
import numpy as np

from scipy import stats
import statsmodels.api as sm
import statsmodels.formula.api as smf
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, roc_auc_score
import pathlib
import sys

sys.path.append(str(pathlib.Path(__file__).resolve().parent.parent.parent))

DATA_DIR = pathlib.Path(__file__).resolve().parent.parent.parent / "data"

print("==================================")
print("LOADING DATA")
print("==================================")

chunks = []
for chunk in pd.read_json(DATA_DIR / "prod/charting_points_clean.jsonl",
                          lines=True,
                          chunksize=10000):
    chunks.append(chunk)

df = pd.concat(chunks, ignore_index=True)

# -------------------------
# TARGET SETUP
# -------------------------
TARGET = "is_server_winner"

df = df.replace([np.inf, -np.inf], np.nan)
df = df[df[TARGET].notna()].copy()

# FORCE NUMERIC CLEANING (CRITICAL FIX)
df = df.apply(pd.to_numeric, errors="ignore")

# =========================
# FEATURES
# =========================
features = [
    "game_pressure",
    "set_pressure",
    "match_pressure",
    "server_point_diff",
    "rally_count",

    "is_ace",
    "is_forced_error",
    "is_unforced_error",
    "is_unret",

    "tb_point",
    "is_tiebreaker_set",
]

features = [f for f in features if f in df.columns]

# =========================
# CLEAN MODEL DATA
# =========================
df_model = df[features + [TARGET]].copy()

# FORCE EVERYTHING NUMERIC (CRITICAL)
df_model = df_model.apply(pd.to_numeric, errors="coerce")

# DROP MISSING AFTER CONVERSION
df_model = df_model.dropna()

X = df_model[features].copy()
y = df_model[TARGET].astype(float)

# =========================
# REMOVE ZERO-VARIANCE FEATURES
# =========================
from sklearn.feature_selection import VarianceThreshold

vt = VarianceThreshold(threshold=0.0)
vt.fit(X)

kept = X.columns[vt.get_support()]
X = X[kept]

# =========================
# REMOVE PERFECT MULTICOLLINEARITY
# =========================
corr_matrix = X.corr().abs()
upper = corr_matrix.where(np.triu(np.ones(corr_matrix.shape), k=1).astype(bool))

to_drop = [col for col in upper.columns if any(upper[col] > 0.999)]
X = X.drop(columns=to_drop)

# =========================
# CORRELATION
# =========================
print("\n================ CORRELATION ================\n")
corr = df_model[X.columns.tolist() + [TARGET]].corr()[TARGET].sort_values(ascending=False)
print(corr)

# =========================
# T-TESTS
# =========================
print("\n================ T-TESTS ================\n")

for col in X.columns:
    win = df_model[df_model[TARGET] == 1][col].dropna()
    lose = df_model[df_model[TARGET] == 0][col].dropna()

    if len(win) > 0 and len(lose) > 0:
        t_stat, p_val = stats.ttest_ind(win, lose, equal_var=False)
        print(f"{col}: t={t_stat:.4f}, p={p_val:.6f}")

# =========================
# LOGISTIC REGRESSION (FIXED)
# =========================
print("\n================ LOGISTIC REGRESSION ================\n")

X_sm = sm.add_constant(X, has_constant="add")

logit_model = sm.Logit(y, X_sm).fit(maxiter=200)
print(logit_model.summary())

# =========================
# RANDOM FOREST
# =========================
print("\n================ RANDOM FOREST ================\n")

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)

rf = RandomForestClassifier(n_estimators=100, random_state=42)
rf.fit(X_train, y_train)

y_pred = rf.predict(X_test)
y_prob = rf.predict_proba(X_test)[:, 1]

print("Accuracy:", accuracy_score(y_test, y_pred))
print("ROC-AUC:", roc_auc_score(y_test, y_prob))

importances = pd.Series(rf.feature_importances_, index=X.columns)
print("\nFeature Importances:")
print(importances.sort_values(ascending=False))

# =========================
# INTERACTION EFFECT
# =========================

if "df_ratio_last_5_serves" in df.columns and "game_pressure" in df.columns:

    df_int = df.copy()
    df_int["df_ratio_last_5_serves"] = pd.to_numeric(df_int["df_ratio_last_5_serves"], errors="coerce")
    df_int["game_pressure"] = pd.to_numeric(df_int["game_pressure"], errors="coerce")

    df_int["df_pressure_interaction"] = (
        df_int["df_ratio_last_5_serves"] * df_int["game_pressure"]
    )

    formula = """
    is_server_winner ~ df_ratio_last_5_serves
                      + game_pressure
                      + df_pressure_interaction
    """

    interaction_model = smf.logit(formula, data=df_int.dropna()).fit()
    print(interaction_model.summary())

# =========================
# GROUPED MEANS
# =========================
print("\n================ GROUPED MEANS ================\n")

for col in ["df_ratio_last_5_serves", "df_distance"]:
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors="coerce")
        print(f"\n{col}:")
        print(df.groupby(TARGET)[col].mean())

# =========================
# SANITY CHECKS
# =========================
print("\n================ SANITY CHECKS ================\n")

print("\nTarget distribution:")
print(df[TARGET].value_counts(normalize=True))

print("\nMissing values:")
print(df.isnull().mean().sort_values(ascending=False).head(15))