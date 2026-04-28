import pandas as pd
from datetime import datetime
import matplotlib.pyplot as plt
from pathlib import Path
import pathlib
import sys
sys.path.append(str(pathlib.Path(__file__).resolve().parent.parent.parent))

import pyarrow.parquet as pq



DATA_DIR = pathlib.Path(__file__).resolve().parent.parent.parent / "data/prod"
INPUT_FILE = "/home/mcilek/Desktop/TennisAbstract-Old/charting_matches.jsonl"
OUTPUT_FILE = DATA_DIR / "charting-matches.parquet"

df = pd.read_json(INPUT_FILE, lines=True)
df["best_of"] = pd.to_numeric(df["best_of"], errors="coerce")
df["is_final_tiebreaker"] = (
    df["is_final_tiebreaker"]
    .map(lambda x: str(x).lower() if pd.notnull(x) else None)
    .map({
        "1": True,
        "0": False,
        "true": True,
        "false": False,
        "yes": True,
        "no": False
    })
    .astype("boolean")
)

# print(df.info())
# print("--------------------------------------------")
# print(df.head(20))


#parquet_file = pq.ParquetFile(INPUT_FILE)

#chunks = []

#for batch in parquet_file.iter_batches(batch_size=10000):
#    chunk = batch.to_pandas()
#    chunks.append(chunk)

#df = pd.concat(chunks, ignore_index=True)
df.to_parquet(OUTPUT_FILE, index=False)

print(df.info())

"""

print("==================================")


chunks = []
for chunk in pd.read_json(DATA_DIR / "prod/charting_matches.jsonl", lines=True, chunksize=10000):
    chunks.append(chunk)



df = pd.concat(chunks, ignore_index=True)
print(df.info())


cols_to_keep = [
    "match_id",
    "match_date",
    "tournament_name",
    "level",
    "round",
    "gender",
    "surface",
    "best_of",
    "score",
    "match_score",
    "winner",
    "player_1_id",
    "player_2_id",
    "player_1_rank",
    "player_2_rank",
    "player_1_seed",
    "player_2_seed",
    "player_1_entry",
    "player_2_entry",
    "start_time",
    "court",
    "umpire",
    "is_final_tiebreaker"
]
df["best_of"] = pd.to_numeric(df["best_of"], errors="coerce").astype("Int64")
df["player_1_seed"] = df["player_1_seed"].astype("string")
df["player_2_seed"] = df["player_2_seed"].astype("string")
df["is_final_tiebreaker"] = (
    df["is_final_tiebreaker"]
    .map(lambda x: str(x).lower() if pd.notnull(x) else None)
    .map({
        "1": True,
        "0": False,
        "true": True,
        "false": False,
        "yes": True,
        "no": False
    })
    .astype("boolean")
)
matches = df[cols_to_keep].copy()
matches.to_parquet("/home/mcilek/Github/maximcilek/lewis-university-research/data/dev/tennisabstract/class/matches.parquet", index=False)


cols_to_keep = [
    "player_id",
    "fullname",
    "nameparam",
    "lastname",
    "country",
    "dob",
    "hand",
    "backhand",
    "ht",
    "atp_id",
    "wta_id",
    "itf_id",
    "fc_id",
    "dc_id",
    "twitter",
    "wiki_id"
]
players = df[cols_to_keep].copy()
players.to_parquet("/home/mcilek/Github/maximcilek/lewis-university-research/data/dev/tennisabstract/class/players.parquet", index=False)


df["is_double"] = df["is_double"].fillna(-1)
df["second_serve_in_play"] = df["second_serve_in_play"].fillna(-1)
df["game_number"] = pd.to_numeric(df["game_number"], errors="coerce")
df["second_serve_rally"] = df["second_serve_rally"].astype(str)

cols_to_keep = [
    "match_id",
    "point_number", "game_score", "game_number", "is_tiebreaker_set",
    "tb_point_number", "tb_point", "server_player_number",
    "first_serve_rally", "second_serve_rally",
    "point_winner_player_number", "point_winner", "is_server_winner",
    "first_serve_in_play", "second_serve_in_play", "rally",
    "is_ace", "is_unret", "is_rally_winner", "is_forced_error", "is_unforced_error",
    "is_double", "gender", "best_of",
    "server_player_id", "server_player_rank",
    "returner_player_id", "returner_player_rank",
    "server_sets", "server_games", "server_points",
    "returner_sets", "returner_games", "returner_points",
    "server_set_diff", "match_pressure", "server_game_diff",
    "set_pressure", "server_point_diff", "game_pressure",
    "rally_count",
    "df_ratio_last_5_serves", "df_ratio_last_10_serves",
    "df_ratio_last_15_serves", "df_ratio_last_20_serves",
    "df_distance", "df_distance_log", "df_recent_df"
]

points = df[cols_to_keep].copy()
points.to_parquet("/home/mcilek/Github/maximcilek/lewis-university-research/data/dev/tennisabstract/class/points.parquet", index=False)


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