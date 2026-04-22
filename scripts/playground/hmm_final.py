import pandas as pd
import pathlib
# import sys
# sys.path.append(str(pathlib.Path(__file__).resolve().parent.parent.parent))

import pyarrow.parquet as pq

def load_parquet(fp):
    chunks = []
    for batch in parquet_file.iter_batches(batch_size=10000):
        chunk = batch.to_pandas()
        chunks.append(chunk)
    return pd.concat(chunks, ignore_index=True)

def get_df_empty_summary(df, show_empty=False):
    summary = pd.DataFrame({
        "nan_count": df.isna().sum(),
        "empty_or_whitespace_count": (
            df.astype("string").apply(lambda col: col.str.strip().eq(""))
        ).sum(),
    })
    summary["total_missing_like"] = (summary["nan_count"] + summary["empty_or_whitespace_count"])
    summary["pct_missing_like"] = summary["total_missing_like"] / len(df)
    if not show_empty:
        summary = summary[summary["total_missing_like"] > 0]
    return (summary.sort_values("total_missing_like", ascending=False))

def print_value_counts(df, cols):
    print("\n======================================")
    print("Printing Column Value Count(s)")
    print("======================================")
    for c in cols:
        print("--------------------------------------------")
        print(f"COLUMN: {c}")
        print("--------------------------------------------")
        print(df[c].value_counts(dropna=False),"\n")

def valid_double_faults_total(df): return ((df["is_double"] == 1).sum() == ((df["first_serve_in_play"] == 0) & (df["second_serve_in_play"] == 0)).sum())

def get_double_fault_probability(df):
    return df["is_double"].mean()

if __name__ == "__main__":

    # =========================
    # LOAD DATA
    # =========================
    DATA_DIR = pathlib.Path(__file__).resolve().parent.parent.parent / "data"
    parquet_file = pq.ParquetFile(DATA_DIR / "prod/charting-points.parquet")
    df = load_parquet(parquet_file).drop(columns=["df_distance_log", "returner_country", "server_country"])
    bad_match_ids = ["20080125-M-Australian_Open-SF-Jo_Wilfried_Tsonga-Rafael_Nadal", "20220330-W-Miami-QF-Iga_Swiatek-Petra_Kvitova"]
    df = df[~df["match_id"].isin(bad_match_ids)]

    df["match_date"] = pd.to_datetime(df["match_date"], format="%Y%m%d")
    df["server_dob"] = pd.to_datetime((df["server_dob"].astype(str).str.replace(r"\.0$", "", regex=True)), format="%Y%m%d", errors="coerce")
    df["returner_dob"] = pd.to_datetime((df["returner_dob"].astype(str).str.replace(r"\.0$", "", regex=True)), format="%Y%m%d", errors="coerce")
    df["df_distance"] = pd.to_numeric(df["df_distance"], errors="coerce").astype("Int64")
    df["game_number"] = pd.to_numeric(df["game_number"], errors="coerce").astype("Int64")
    df["first_serve_in_play"] = pd.to_numeric(df["first_serve_in_play"], errors="coerce").astype("Int64")
    df["second_serve_in_play"] = pd.to_numeric(df["second_serve_in_play"], errors="coerce").astype("Int64")
    df["server_player_rank"] = pd.to_numeric(df["server_player_rank"], errors="coerce").astype("Int64")
    df["returner_player_rank"] = pd.to_numeric(df["returner_player_rank"], errors="coerce").astype("Int64")
    df["server_backhand"] = pd.to_numeric(df["server_backhand"], errors="coerce").astype("Int64")
    df["returner_backhand"] = pd.to_numeric(df["returner_backhand"], errors="coerce").astype("Int64")
    df["server_hand"] = df["server_hand"].fillna("U")
    df["returner_hand"] = df["returner_hand"].fillna("U")
    df["server_backhand"] = df["server_backhand"].fillna(-1)
    df["returner_backhand"] = df["returner_backhand"].fillna(-1)
    df["is_double"] = (
        df["is_double"]
        .replace({
            "1": 1,
            "1.0": 1,
            "0": 0,
            "0.0": 0,
            "true": 1,
            "false": 0,
            "yes": 1,
            "no": 0,
            True: 1,
            False: 0
        })
    )
    df["is_double"] = pd.to_numeric(df["is_double"], errors="coerce").fillna(0).astype(int)
    df["last_serve_double_fault"] = (df["df_recent_df"].map(lambda x: str(x).lower() if pd.notnull(x) else None).map({"1": True, "0": False}).astype("boolean"))
    # df["df_trend"] = df["df_ratio_last_10_serves"] - df["df_ratio_last_20_serves"]
    df = df.drop(columns=["df_recent_df"]) #, "df_ratio_last_5_serves", "df_ratio_last_15_serves"])

    #print("\n======================================")
    #print("DataFrame Empty/NaN Summary")
    #print("======================================")
    #print(get_df_empty_summary(df), "\n")
    # print_value_counts(df, ["server_hand"])
    
    print(f"Validated Double Faults Totals: {valid_double_faults_total(df)}")

    # df["second_serve_in_play"] = df["second_serve_in_play"].fillna(0)
    # df["is_double"] = df["is_double"].fillna(0)

    print(f"Double Fault Probability: {get_double_fault_probability(df)}")
    df.to_parquet("/home/mcilek/Github/maximcilek/lewis-university-research/data/dev/tennisabstract/charting_points.parquet", index=False)