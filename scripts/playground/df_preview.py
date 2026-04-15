import pandas as pd
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
print(df.info())
print(df.head(10))

print(df.__dir__())
c = df.isna().mean().sort_values(ascending=False)
print(c)

d = df.describe(percentiles=[0.01, 0.05, 0.95, 0.99]).T
print(d)

cols = [
    "rally_count",
    "match_pressure",
    "set_pressure",
    "game_pressure",
    "server_point_diff",
]
for col in ["surface", "level", "server_hand", "returner_hand"]:
    print(col, df[col].value_counts(dropna=False))


"""

df_sorted = df.sort_values(["match_id", "point_number"])

bad_sequences = (
    df_sorted.groupby(["match_id", "point_number"])
    .diff()
    .dropna() != 1
).sum()

print("Broken sequences:", bad_sequences)

dups = df.duplicated(subset=["match_id", "point_number", "game_score"])
print(f"Duplicates: {dups}")
# for col in cols:
#     df[col].hist(bins=50)
#     plt.title(col)
#     plt.show()

print(f"{(df["server_point_diff"].abs() > 10).sum()} Score Consistency (If large, corrupted scoring)")

missing_points = df[
    (df["first_serve_in_play"] == 0) &
    (df["second_serve_in_play"].isna())
].shape

print(f"Missing Points: {missing_points}")

impossible_scenario_check = df[
    (df["is_double"] == 1) &
    (df["first_serve_in_play"] == 1)
]
print(f"Impossible Scenario: {impossible_scenario_check}")

# Class Imbalanace
is_ace = df["is_ace"].value_counts(normalize=True)
is_unforced_error = df["is_unforced_error"].value_counts(normalize=True)
print(f"Is Ace Class Imbalance: {is_ace}")
print(f"Is Unforced Error Class Imbalance: {is_unforced_error}")

has_single_value_column = df.nunique().sort_values()
print(f"Has Single Value Col: {has_single_value_column}")

temporal_leakage = df.groupby("is_server_winner")["rally_count"].mean()
print(f"Temporal Leakage: {temporal_leakage}")

def validate_df(df):
    print("=== Missing ===")
    print(df.isna().mean().sort_values(ascending=False).head(10))

    print("\n=== Constant Columns ===")
    print(df.nunique()[df.nunique() <= 1])

    print("\n=== Duplicates ===")
    print(df.duplicated().sum())

    print("\n=== Sequence Issues ===")
    seq_breaks = (
        df.sort_values(["match_id", "point_number"])
        .groupby("match_id")["point_number"]
        .diff()
        .dropna() != 1
    ).sum()
    print("Broken sequences:", seq_breaks)


print("\n\n====================================================")
print("VALIDATING DATA FRAME")
print("====================================================")
validate_df(df)
"""