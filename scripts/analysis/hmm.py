import pandas as pd
import pathlib
import numpy as np
from collections import defaultdict
import json
# import sys
# sys.path.append(str(pathlib.Path(__file__).resolve().parent.parent.parent))

import pyarrow.parquet as pq
from sklearn.preprocessing import StandardScaler, RobustScaler
import matplotlib.pyplot as plt
import seaborn as sns
from statsmodels.tsa.stattools import acf
from statsmodels.graphics.tsaplots import plot_acf
from hmmlearn.hmm import GaussianHMM, GMMHMM

pd.set_option("display.max_columns", None)
pd.set_option("display.width", 200)
pd.set_option("display.max_colwidth", None)

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

def compute_serve_rally_counts(df):
    df_new = df.copy()

    def is_serve_in(series):
        """
        Vectorized version:
        Returns:
            1 if serve is in
            0 if serve is out
            NaN if undefined
        """
        cond_valid = series.notna() & (series.str.len() > 1)
        second_char = series.str[1]
        is_in = (~second_char.isin(list("wdnxgeVPQRS"))).astype(float)
        is_in = is_in.where(cond_valid, other=np.nan)
        return is_in

    # Clean rally patterns
    df_new["first_clean"] = (df["first_serve_rally"].fillna("").str.replace(r"\)\*", "0*", regex=True).str.replace(r"&\*", "0*", regex=True).str.replace(r"\?", "0", regex=True))
    df_new["second_clean"] = (df["second_serve_rally"].fillna("").str.replace(r"\)\*", "0*", regex=True).str.replace(r"&\*", "0*", regex=True).str.replace(r"\?", "0", regex=True))

    # remove lets ("c")
    df_new["first_no_lets"] = df_new["first_clean"].str.replace("c", "", regex=False)
    df_new["second_no_lets"] = df_new["second_clean"].str.replace("c", "", regex=False)

    # Serve in/out
    df_new["first_in"] = is_serve_in(df_new["first_no_lets"])
    df_new["second_in"] = is_serve_in(df_new["second_no_lets"])

    # Rally detection
    df_new["is_rally_first"] = np.where(df_new["first_in"] == 0, 0, (df_new["first_no_lets"].str.len() > 2).astype(int))
    df_new["is_rally_second"] = np.where(df_new["second_in"] == 0, 0, (df_new["second_no_lets"].str.len() > 2).astype(int))

    # Extract serve outcomes
    df_new["serve1"] = np.where(df_new["is_rally_first"] == 0, df_new["first_no_lets"], df_new["first_no_lets"].str[0])
    df_new["serve2"] = np.where(df_new["is_rally_second"] == 0, df_new["second_no_lets"], df_new["second_no_lets"].str[0])
    df_new["rally_part"] = np.where(df_new["is_rally_first"] == 1, df_new["first_no_lets"].str[1:], np.where(df_new["is_rally_second"] == 1, df_new["second_no_lets"].str[1:], None))

    # Outcome flags (vectorized)
    df_new["is_rally_winner"] = df_new["rally_part"].str.contains(r"\*", na=False)
    df_new["is_forced_error"] = df_new["rally_part"].str.contains(r"#", na=False)
    df_new["is_unforced_error"] = df_new["rally_part"].str.contains(r"@", na=False)

    # double fault
    df_new["is_double"] = ((df_new["first_in"] == 0) & (df_new["second_in"] == 0)).astype(float)
    df_new["rally_no_spec"] = df_new["rally_part"].str.replace(r"[-=@#*;+]", "", regex=True)
    df_new["rally_no_error"] = df_new["rally_no_spec"].str.replace(r"[dwxen]", "", regex=True)
    df_new["rally_no_direction"] = df_new["rally_no_error"].str.replace(r"[123789]", "", regex=True)
    df_new["rally_len"] = df_new["rally_no_direction"].str.len().fillna(0)
    rally_counts = []
    rally_parts = []
    is_doubles = []
    for i, row in df_new.iterrows():
        w = row.get("serve1", "")
        y = row.get("rally_part", "")
        ai = row.get("rally_len", np.nan)  # THIS is critical (previous value)
        is_double = bool(row.get("is_double", False))
        rally_parts.append(y)
        is_doubles.append(is_double)
        # 1. blank serve1 server sequence
        if pd.isna(w) or w == "":
            rally_counts.append(np.nan)
            continue
        # 2. terminal rally
        if isinstance(y, str) and y.endswith(("@", "#")):
            rally_counts.append(ai)
            continue
        # 3. double fault
        if is_double:
            rally_counts.append(0)
            continue
        # 4. default
        if pd.isna(ai):
            rally_counts.append(np.nan)
        else:
            rally_counts.append(ai + 1)
    df["rally_count"] = rally_counts
    df["rally_count"] = df["rally_count"].fillna(0)
    df["rally"] = rally_parts
    df["rally"] = df["rally"].fillna("")
    df["is_double"] = is_doubles
    df["first_serve_in_play"] = df_new["first_in"]
    df["second_serve_in_play"] = df_new["second_in"]
    df["first_no_lets"] = df_new["first_no_lets"]
    df["second_no_lets"] = df_new["second_no_lets"]
    return df

def plot_distribution(df, col_name):
    col = df[col_name]

    mu = col.mean()
    sigma = col.std()

    x = np.linspace(col.min(), col.max(), 500)

    plt.hist(col, bins=50, density=True, alpha=0.6)
    plt.axvline(mu, linestyle="--", label="mean")
    plt.axvline(mu + sigma, linestyle=":", label="+1 std")
    plt.axvline(mu - sigma, linestyle=":", label="-1 std")

    plt.title("df_distance distribution")
    plt.legend()
    plt.show()

def skewness(df):
    """
    | Skew  | Meaning                            |
    | ----- | ---------------------------------- |
    | < 0.5 | symmetric                          |
    | 0.5-1 | moderate                           |
    | 1-2   | noticeable but fine                |
    | > 2   | problematic for Gaussian emissions |
    """
    skew = df.skew()
    print("\n--------------------------------------")
    print("Skew")
    print("--------------------------------------")
    print(skew)
    return skew

def variance(df):
    variance = scaled_features.var()
    print("\n--------------------------------------")
    print("Variance")
    print("--------------------------------------")
    print(f"{variance}")
    return variance

def tail_mass_z(df: pd.DataFrame, cols, threshold=3.0):
    """
    Computes fraction and count of values where |z| > threshold per feature.
    
    Assumes df is already standardized (mean ~0, std ~1).

    | Tail mass | Interpretation                |
    | --------- | ----------------------------- |
    | < 0.1%    | very clean Gaussian           |
    | 0.1%-1%   | acceptable / mild heavy tails |
    | 1%-3%     | questionable                  |
    | > 3%      | poor Gaussian fit             |
    """
    abs_z = df[cols].abs()
    tail_counts = (abs_z > threshold).sum()
    tail_fraction = tail_counts / len(df)
    result = pd.DataFrame({"tail_count": tail_counts, "tail_fraction": tail_fraction})
    output = result.sort_values("tail_fraction", ascending=False)

    print("\n--------------------------------------")
    print(f"Tail Mass (|z| > {threshold})")
    print("--------------------------------------")
    print(output)
    return output

def print_tail_outliers(df: pd.DataFrame, cols=None, std_target=3):
    """
    | threshold | expected mass outside |
    | --------- | --------------------- |
    | ±2 std    | ~5%                   |
    | ±3 std    | ~0.27%                |
    """
    if cols is None:
        cols = df.select_dtypes(include=[np.number]).columns
    results = {}
    for col in cols:
        x = df[col].dropna()
        mean = x.mean()
        std = x.std()
        if std == 0 or np.isnan(std):
            continue
        z = (x - mean) / std
        tail_mask = z.abs() > std_target
        count = tail_mask.sum()
        fraction = count / len(x)
        results[col] = {"tail_count": int(count), "tail_fraction": float(fraction)}
    result_df = pd.DataFrame(results).T.sort_values("tail_fraction", ascending=False)
    print("\n--------------------------------------")
    print(f"Tail Outliers (|z| > {std_target})")
    print("--------------------------------------")
    print(result_df)
    return result_df

def covariance(df):
    print("\n--------------------------------------")
    print(f"Covariance")
    print("--------------------------------------")
    df_np = df.to_numpy(dtype=np.float64)
    df_np = np.nan_to_num(df_np)
    cov = np.cov(df_np, rowvar=False)
    print(cov)
    return cov

def correlation_matrix(df: pd.DataFrame, cols, plot=True):
    """
    Computes correlation matrix and optionally plots heatmap.
    | Range   | Meaning                |
    | ------- | ---------------------- |
    | 0-0.3   | weak                   |
    | 0.3-0.6 | moderate               |
    | > 0.8   | problematic redundancy |
    """
    corr = df[cols].corr()

    if plot:
        fig, ax = plt.subplots(figsize=(12, 8))

        sns.heatmap(
            corr,
            annot=True,
            fmt=".5f",
            cmap="vlag",
            center=0,
            vmin=-1,
            vmax=1,
            ax=ax
        )

        ax.set_title("Feature Correlation Matrix")

        # Make background transparent
        fig.patch.set_alpha(0)
        ax.set_facecolor("none")

        plt.tight_layout()

        save_path = "/home/mcilek/Github/maximcilek/lewis-university-research/data/analysis/Final/correlation_matrix.png"
        plt.savefig(
            save_path,
            dpi=300,
            bbox_inches="tight",
            transparent=True
        )

        plt.show()
        plt.close(fig)

    print("\n--------------------------------------")
    print("Correlation Matrix")
    print("--------------------------------------")
    print(corr)

    return corr

def eigen_values(cov):
    eigvals = np.linalg.eigvals(cov)
    eigvals = np.sort(eigvals)[::-1]
    print("\n--------------------------------------")
    print(f"Eigen Values")
    print("--------------------------------------")
    print(f"Values: {eigvals}")
    print("Explained ratio:", eigvals / eigvals.sum())
    print("Top-1 dominance:", eigvals[0] / eigvals.sum())
    print("Condition number:", eigvals[0] / eigvals[-1])
    return eigvals

def print_lag_acf(df, cols, lag=1, dropna=True, precision=5):
    """
    Prints lag-k autocorrelation for each column in a clean format.
    """

    print("\n--------------------------------------")
    print(f"Lag-{lag} Autocorrelation")
    print("--------------------------------------")

    for col in cols:
        series = df[col]

        if dropna:
            series = series.dropna()

        # skip invalid series
        if len(series) <= lag + 1 or series.nunique() <= 1:
            print(f"{col:<20} lag{lag} ~ NaN (insufficient variation)")
            continue

        try:
            r = acf(series, nlags=lag, fft=True, missing="drop")[lag]
            print(f"{col:<20} lag{lag} ~ {r:.{precision}f}")
        except Exception as e:
            print(f"{col:<20} lag{lag} ~ error ({e})")

def print_multi_lag_acf(df, cols, lags=(1, 5)):
    print("\n--------------------------------------")
    print("Lag Autocorrelation Summary")
    print("--------------------------------------")

    for col in cols:
        series = df[col].dropna()

        if len(series) < max(lags) + 1:
            print(f"{col:<20} insufficient data")
            continue

        try:
            acf_vals = acf(series, nlags=max(lags), fft=True, missing="drop")
            out = " | ".join([f"lag{l}={acf_vals[l]:.2f}" for l in lags])
            print(f"{col:<20} {out}")
        except Exception as e:
            print(f"{col:<20} error ({e})")


def hmm(df):

    hmm_cols = ["first_serve_in_play", "match_pressure", "set_pressure", "game_pressure", "server_point_diff", "df_distance"]

    # ONLY numeric feature matrix
    X = df[hmm_cols].values

    # sequence lengths (uses metadata only)
    lengths = df.groupby("match_id").size().values

    model = GaussianHMM(
        n_components=5,
        covariance_type="diag", # "full",
        n_iter=200,
        random_state=42,
        tol=1e-3,
        verbose=True
    )

    model.fit(X, lengths)

    df["hidden_state"] = model.predict(X, lengths)

    print(df.groupby("hidden_state")[hmm_cols].mean())
    print(model.transmat_)

    return df

def gmm_hmm(df, n_states=5, n_mix=2, n_iter=200):
    """
    Fit a Gaussian Mixture Hidden Markov Model to tennis point data.
    """

    hmm_cols = [
        "first_serve_in_play",
        "match_pressure",
        "set_pressure",
        "game_pressure",
        "server_point_diff",
        "df_distance",
        "df_distance_missing"
    ]

    # -------------------------
    # Build feature matrix
    # -------------------------
    X = df[hmm_cols].values

    # Sequence lengths per match (critical for HMM correctness)
    lengths = df.groupby("match_id").size().values

    # -------------------------
    # Model
    # -------------------------
    model = GMMHMM(
        n_components=n_states,     # hidden states
        n_mix=n_mix,               # Gaussian mixtures per state
        covariance_type="diag",    # stable for high-dim features
        n_iter=n_iter,
        random_state=42,
        verbose=True,
        tol=1e-3
    )

    print("\n======================================")
    print("Fitting GMMHMM...")
    print("======================================")

    model.fit(X, lengths)

    # -------------------------
    # Decode hidden states
    # -------------------------
    hidden_states = model.predict(X, lengths)
    df = df.copy()
    df["hidden_state"] = hidden_states

    # -------------------------
    # State summaries
    # -------------------------
    print("\n======================================")
    print("State Means (Emissions)")
    print("======================================")
    print(df.groupby("hidden_state")[hmm_cols].mean())

    print("\n======================================")
    print("Transition Matrix")
    print("======================================")
    print(model.transmat_)

    return df, model

def iterate_matches(df):
    """
    Iterates through dataframe grouped by match_id,
    with each match sorted by point_number.
    """
    for match_id, match_df in df.groupby("match_id", sort=False):
        match_df = match_df.sort_values("point_number")
        yield match_id, match_df

def build_serve_features(df):
    def is_serve_in(x):
        if x is None or pd.isna(x):
            return np.nan
        x = str(x).strip()
        if len(x) == 0 or x == "":
            return np.nan
        char = x[1] if len(x) > 1 else x
        if char in ["P", "Q", "R", "S"]:
            return np.nan
        elif char in "nwdxge!V":
            return 0
        return 1
    def is_rally(row, num):
        s = row[f"{num}_serve_rally"]
        is_in = row[f"{num}_serve_in_play"]
        no_serve_and_volley = row[f"{num}_no_serve_and_volley"]
        if is_in == 0:
            return 0
        elif is_in == 1:
            if len(no_serve_and_volley) > 2 or no_serve_and_volley[-1] == "C":
                return 1
            return 0
        elif pd.isna(is_in):
            return pd.NA
        else:
            print(f"Unknown ({is_in}): {s1}")
            quit()
    def clean_serve(row, num):
        has_rally = row[f"{num}_serve_has_rally"]
        s = row[f"{num}_serve_rally"]
        if pd.isna(has_rally):
            return pd.NA
        elif has_rally == 0:
            return s
        elif has_rally == 1:
            return s[0]
        else:
            print(f"Unknown Serve Pattern ({has_rally}): {s}")
            quit()
    def get_rally(row):
        first_serve_has_rally = row["first_serve_has_rally"]
        second_serve_has_rally = row["second_serve_has_rally"]
        first_no_serve_and_volley = row["first_no_serve_and_volley"]
        second_no_serve_and_volley = row["second_no_serve_and_volley"]
        if pd.notna(first_serve_has_rally) and first_serve_has_rally == 1:
            return first_no_serve_and_volley[1:]
        if pd.notna(second_serve_has_rally) and second_serve_has_rally == 1:
            return second_no_serve_and_volley[1:] 
        return pd.NA
    def is_ace(row):
        serve1 = row["serve1"]
        serve2 = row["serve2"]
        if pd.notna(serve1) and "*" in serve1:
            return True
        if pd.notna(serve2) and "*" in serve2:
            return True
        if pd.notna(serve1) or pd.notna(serve2):
            return False
        return pd.NA
    def is_unret(row):
        serve1 = row["serve1"]
        serve2 = row["serve2"]
        if pd.notna(serve1) and "#" in serve1:
            return True
        if pd.notna(serve2) and "#" in serve2:
            return True
        if pd.notna(serve1) or pd.notna(serve2):
            return False
        return pd.NA    
    def is_rally_winner(row):
        rally = row["rally"]
        if pd.notna(rally):
            if "*" in rally:
                return True
            return False
        return pd.NA
    def is_forced_error(row):
        rally = row["rally"]
        if pd.notna(rally):
            if "#" in rally:
                return True
            return False
        return pd.NA
    def is_unforced_error(row):
        rally = row["rally"]
        if pd.notna(rally):
            if "@" in rally:
                return True
            return False
        return pd.NA
    def is_double(row):
        first_serve_in = row["first_serve_in_play"]
        second_serve_in = row["second_serve_in_play"]
        if pd.notna(first_serve_in) and pd.notna(second_serve_in):
            if first_serve_in == 0 and second_serve_in == 0:
                return True
            return False        
        return pd.NA
    def rally_no_spec(row):
        rally = row["rally"]
        if pd.notna(rally):
            return rally.replace("-", "").replace("=", "").replace("C", "").replace("@", "").replace("#", "").replace("*", "").replace(";", "").replace("+", "").replace("^", "")
        return pd.NA
    def rally_no_error(row):
        rally = row["rally_no_spec"]
        if pd.notna(rally):
            return rally.replace("d", "").replace("w", "").replace("x", "").replace("e", "").replace("n", "").replace("!", "")
        return pd.NA
    def rally_no_direction(row):
        rally = row["rally_no_error"]
        if pd.notna(rally):
            return rally.replace("1", "").replace("2", "").replace("3", "").replace("7", "").replace("8", "").replace("9", "")
        return pd.NA
    def rally_length(row):
        rally = row["rally_no_direction"]
        if pd.notna(rally):
            return len(rally)
        return pd.NA
    def rally_count(row):
        rally_length = row["rally_length"]
        rally = row["rally"]
        is_double = row["is_double"]
        if pd.notna(rally) and rally[-1] in "#@":
            return rally_length
        if pd.notna(is_double) and is_double == 1:
            return 0
        if pd.notna(rally):
            return rally_length + 1
        return pd.NA

    new_df = df.copy()
    srv1 = df["first_serve_rally"].astype("string").str.strip().str.replace(" ", "").str.replace("D", "d").str.replace("W", "w").str.replace("M", "m").str.replace(")*", "0*").str.replace("&*", "0*").str.replace("?", "0").str.replace(".", "")
    srv1 = srv1.replace("", pd.NA)
    srv2 = df["second_serve_rally"].astype("string").str.strip().str.replace(" ", "").str.replace("D", "d").str.replace("W", "w").str.replace("M", "m").str.replace(".", "")
    srv2 = srv2.replace("", pd.NA)
    new_df["first_serve_rally"] = srv1
    new_df["second_serve_rally"] = srv2
    srv1_no_lets = srv1.str.replace("c", "", regex=False)
    srv2_no_lets = srv2.str.replace("c", "", regex=False)
    first_no_serve_and_volley = srv1_no_lets.where(~srv1_no_lets.str.contains(r"\+"), srv1_no_lets.str.replace(r"\+", "", regex=False))
    second_no_serve_and_volley = srv2_no_lets.where(~srv2_no_lets.str.contains(r"\+"), srv2_no_lets.str.replace(r"\+", "", regex=False))
    new_df["first_no_serve_and_volley"] = first_no_serve_and_volley
    new_df["second_no_serve_and_volley"] = second_no_serve_and_volley
    is_first_in = first_no_serve_and_volley.apply(is_serve_in)
    is_second_in = second_no_serve_and_volley.apply(is_serve_in)
    new_df["first_serve_in_play"] = is_first_in
    new_df["second_serve_in_play"] = is_second_in
    # isRally1st / isRally2nd - If rally occured in either first, second, or neither
    new_df["first_serve_has_rally"] = new_df.apply(lambda row: is_rally(row, "first"), axis=1).astype("Int64")
    new_df["second_serve_has_rally"] = new_df.apply(lambda row: is_rally(row, "second"), axis=1).astype("Int64")
    new_df["serve1"] = new_df.apply(lambda row: clean_serve(row, "first"), axis=1).astype("string")
    new_df["serve2"] = new_df.apply(lambda row: clean_serve(row, "second"), axis=1).astype("string")
    new_df["rally"] = new_df.apply(get_rally, axis=1).astype("string")
    new_df["is_ace"] = new_df.apply(is_ace, axis=1).astype("boolean")
    new_df["is_unret"] = new_df.apply(is_unret, axis=1).astype("boolean")
    new_df["is_rally_winner"] = new_df.apply(is_rally_winner, axis=1).astype("boolean")
    new_df["is_forced_error"] = new_df.apply(is_forced_error, axis=1).astype("boolean")
    new_df["is_unforced_error"] = new_df.apply(is_unforced_error, axis=1).astype("boolean")
    new_df["is_double"] = new_df.apply(is_double, axis=1).astype("boolean")
    new_df["rally_no_spec"] = new_df.apply(rally_no_spec, axis=1).astype("string")
    new_df["rally_no_error"] = new_df.apply(rally_no_error, axis=1).astype("string")
    new_df["rally_no_direction"] = new_df.apply(rally_no_direction, axis=1).astype("string")
    new_df["rally_length"] = new_df.apply(rally_length, axis=1).astype("Int64")
    new_df["rally_count"] = new_df.apply(rally_count, axis=1).astype("Int64")
    # print(new_df["first_serve_has_rally"].value_counts(dropna=False))
    # print(new_df["second_serve_has_rally"].value_counts(dropna=False))
    # print(f"Serve1 NaN: {new_df["serve1"].isna().sum()}")
    # print(f"Serve2 NaN: {new_df["serve2"].isna().sum()}")
    # print(f"Rally NaN: {new_df["rally"].isna().sum()}")
    # print(f"Rally Length NaN: {new_df["rally_length"].isna().sum()}")
    # print(f"Rally Count NaN: {new_df["rally_count"].isna().sum()}")
    # print(new_df["is_ace"].value_counts(dropna=False))
    # print(new_df["is_unret"].value_counts(dropna=False))
    # print(new_df["is_rally_winner"].value_counts(dropna=False))
    # print(new_df["is_double"].value_counts(dropna=False))
    return new_df

    """srv_outcomes = ["point outcome only", "penalty", "fault", "let", "unknown", "valid"]
    df["first_serve_rally_status"] = np.select([srv1_is_generic, srv1_is_penalty, srv1_is_fault, srv1_is_let, srv1_is_empty, srv1_is_valid], rally_outcomes, default="unknown")
    df["second_serve_rally_status"] = np.select([ srv2_outcome_only, srv2_is_penalty, srv2_is_fault, srv2_is_let, srv2_is_empty, srv2_is_valid], rally_outcomes, default="unknown")
    df["serve_info_missing"] = df["first_serve_in_play"].isna().astype(int)
    """

def add_hazard_df_distance(df):
    hazard_values = []
    for match_id, match_df in iterate_matches(df):
        for idx, row in match_df.iterrows():
            t = row["df_distance"]
            if pd.isna(t):
                hazard = 0.0
            else:
                hazard = 1 / (1 + float(t))
            hazard_values.append((idx, hazard))
    # assign back to original dataframe
    for idx, hazard in hazard_values:
        df.loc[idx, "hazard_df_distance"] = hazard
    return df

def plot_hazard_df_distance(df):
    total_n = len(df["hazard_df_distance"])
    x = df["hazard_df_distance"].dropna().sort_values()
    kept_n = len(x)
    dropped_n = total_n - kept_n

    print(f"Total values: {total_n}")
    print(f"Non-missing values used in CDF: {kept_n}")
    print(f"Dropped missing values: {dropped_n}")

    # cumulative probabilities
    y = np.arange(1, kept_n + 1) / kept_n

    plt.figure(figsize=(8,5))
    plt.plot(x, y)
    plt.xlabel("hazard_df_distance")
    plt.ylabel("Cumulative Probability")
    plt.title("Cumulative Distribution of hazard_df_distance")
    plt.grid(True)
    plt.show()

def bin_rally_length(x):
    if pd.isna(x):
        return -1
    if x <= 1:
        return 1      # serve +1 / ultra short
    elif x <= 4:
        return 2      # short
    elif x <= 8:
        return 3      # medium
    else:
        return 4      # long

if __name__ == "__main__":

    # =========================
    # LOAD DATA
    # =========================
    DATA_DIR = pathlib.Path(__file__).resolve().parent.parent.parent / "data"
    parquet_file = pq.ParquetFile(DATA_DIR / f"prod/charting-points.parquet")
    df = load_parquet(parquet_file)
    #df = df[df["match_date"] > "2000-01-01"]
    if "match_id" in df.columns and "point_number" in df.columns:
        df = df.sort_values(["match_id", "point_number"])
    
    rmv_match_ids = ["20241127-M-Maia_CH-R32-Pedro_Araujo-Alex_Marti_Pujolras", "20030701-M-Wimbledon-SF-Mark_Philippoussis-Sebastien_Grosjean", "20120113-W-Hobart-SF-Angelique_Kerber-Mona_Barthel"] # , '20040222-M-Rotterdam-F-Juan_Carlos_Ferrero-Lleyton_Hewitt', '20091011-M-Shanghai_Masters-R16-Fernando_Gonzalez-Nikolay_Davydenko', '20101003-M-Kuala_Lumpur-F-Andrey_Golubev-Mikhail_Youzhny', '20110614-W-Eastbourne-R32-Ana_Ivanovic-Julia_Goerges', '20120319-M-Indian_Wells_Masters-F-Roger_Federer-John_Isner', '20130105-M-Brisbane-SF-Kei_Nishikori-Andy_Murray', '20130217-M-Rotterdam-F-Julien_Benneteau-Juan_Martin_Del_Potro', '20130808-M-Canada_Masters-R16-Ernests_Gulbis-Andy_Murray', '20150927-M-Metz-SF-Jo_Wilfried_Tsonga-Philipp_Kohlschreiber', '20151006-M-Beijing-R32-Novak_Djokovic-Simone_Bolelli', '20151101-M-Basel-F-Rafael_Nadal-Roger_Federer', '20170206-M-Davis_Cup_World_Group_R1-RR-Kyle_Edmund-Denis_Shapovalov', '20180122-W-Australian_Open-R16-Su_Wei_Hsieh-Angelique_Kerber', '20180326-W-Miami-R16-Monica_Puig-Danielle_Collins', '20180329-W-Miami-SF-Jelena_Ostapenko-Danielle_Collins', '20190716-M-Amersfoort_CH-R64-Gijs_Brouwer-Holger_Rune', '20210605-M-Roland_Garros-R32-Roger_Federer-Dominik_Koepfer', '20211027-M-Vienna-R32-Reilly_Opelka-Jannik_Sinner', '20220117-W-Australian_Open-R128-Madison_Keys-Sofia_Kenin', '20220721-M-Hamburg-R16-Andrey_Rublev-Francisco_Cerundolo', '20220916-M-Davis_Cup_Finals-RR-Tallon_Griekspoor-Daniel_Evans', '20230104-M-United_Cup-RR-Hubert_Hurkacz-Matteo_Berrettini', '20230605-M-Roland_Garros-R16-Grigor_Dimitrov-Alexander_Zverev', '20230607-M-Roland_Garros-QF-Casper_Ruud-Holger_Rune', '20230703-M-Wimbledon-R128-Emil_Ruusuvuori-Stan_Wawrinka', '20230831-M-US_Open-R64-Hubert_Hurkacz-Jack_Draper', '20230904-M-US_Open-R16-Jannik_Sinner-Alexander_Zverev', '20231015-M-Shanghai_Masters-F-Hubert_Hurkacz-Andrey_Rublev', '20231028-M-Basel-SF-Ugo_Humbert-Hubert_Hurkacz', '20231031-M-Paris_Masters-R64-Hubert_Hurkacz-Sebastian_Korda', '20240210-M-Marseille-SF-Hubert_Hurkacz-Ugo_Humbert', '20240213-M-Rotterdam-R32-Hubert_Hurkacz-Jiri_Lehecka', '20240215-M-Rotterdam-R16-Hubert_Hurkacz-Tallon_Griekspoor', '20240325-M-Miami_Masters-R32-Ben_Shelton-Lorenzo_Musetti', '20240602-M-Roland_Garros-R16-Jannik_Sinner-Corentin_Moutet', '20240701-M-Wimbledon-R128-Alex_Michelsen-Lloyd_Harris', '20250320-M-Miami_Masters-R128-Learner_Tien-Joao_Fonseca', '20250509-W-Rome-R64-Emiliana_Arango-Mirra_Andreeva', '20250512-M-Rome_Masters-R32-Hubert_Hurkacz-Marcos_Giron', '20250513-M-Rome_Masters-R16-Jakub_Mensik-Hubert_Hurkacz', '20250530-W-Roland_Garros-R32-Iga_Swiatek-Jaqueline_Cristian', '20250630-M-Wimbledon-R128-Giovanni_Mpetshi_Perricard-Taylor_Fritz', '20250702-M-Wimbledon-R64-Gabriel_Diallo-Taylor_Fritz', '20250711-M-Wimbledon-SF-Novak_Djokovic-Jannik_Sinner', '20251121-M-Davis_Cup_Finals-RR-Flavio_Cobolli-Zizou_Bergs']
    df = df[~df["match_id"].isin(rmv_match_ids)]
    # df = compute_serve_rally_counts(df)
    df = build_serve_features(df)
    cols_to_keep = ["first_serve_in_play", "second_serve_in_play", "last_serve_double_fault", "rally_length",
                    "server_set_diff", "server_game_diff", "server_point_diff", "is_double", "is_unret", "is_ace", "is_server_winner", "is_rally_winner"
    ]
    
    # df = df[df["first_serve_in_play"].notna()].copy()
    bad_match_ids = df.loc[df["first_serve_in_play"].isna(), "match_id"].unique()
    print("matches to drop:", len(bad_match_ids))
    df = df[~df["match_id"].isin(bad_match_ids)].copy()
    print("remaining rows:", len(df))
    print("remaining matches:", df["match_id"].nunique())

    df["first_serve_in_play"] = (df["first_serve_in_play"].astype("Int64").fillna(-1))
    df["second_serve_in_play"] = (df["second_serve_in_play"].astype("Int64").fillna(-1))
    df["is_double"] = (df["is_double"].astype("Int64").fillna(-1))
    df["is_ace"] = (df["is_ace"].astype("Int64").fillna(-1))
    df["is_unret"] = (df["is_unret"].astype("Int64").fillna(-1))
    df["is_rally_winner"] = (df["is_rally_winner"].astype("Int64").fillna(-1))
    df["rally_length"] = df["rally_length"].apply(bin_rally_length).astype("Int64")
    df["last_serve_double_fault"] = df["last_serve_double_fault"].astype("Int64")
    
    print(df[cols_to_keep].copy().info())
    for c in cols_to_keep:
        print(df[c].value_counts(dropna=False))
        print("------------------------------------------------")
    quit()

    print(df["first_serve_in"].value_counts(dropna=False))
    print(df["second_serve_in"].value_counts(dropna=False))
    print("=======================================")
    print(df["first_serve_has_rally"].value_counts(dropna=False))
    print(df["first_serve_has_rally"].value_counts(dropna=False))
    print("=======================================")
    print(df["first_serve_is_fault"].value_counts(dropna=False))
    print(df["second_serve_is_fault"].value_counts(dropna=False))
    print("=======================================")
    print(df["is_penalty"].value_counts(dropna=False))
    print(df["is_ace"].value_counts(dropna=False))
    print(df["has_second_serve_info"].value_counts(dropna=False))
    print(df["is_rally_winner"].value_counts(dropna=False))
    #print(df["is_forced_error"].value_counts(dropna=False))
    #print(df["is_unforced_error"].value_counts(dropna=False))
    print(df["is_unret"].value_counts(dropna=False))
    print(df["is_error"].value_counts(dropna=False))

    df = df.drop(columns=["first_serve_in_play", "second_serve_in_play"])
    df["is_double"] = (df["is_double"].map(lambda x: str(x).lower() if pd.notnull(x) else None).map({"1": 1, "0": 0, "true": 1, "false": 0, "yes": 1, "no": 0}).astype("int"))
    
    print(get_df_empty_summary(df))
    print(df["is_double"].value_counts(dropna=False))
    print(df["rally_len"].value_counts(dropna=False))
    quit()

    df["is_ace"] = (df["is_ace"].map(lambda x: str(x).lower() if pd.notnull(x) else None).map({"1": 1, "0": 0, "true": 1, "false": 0, "yes": 1, "no": 0}).astype("int"))
    df["is_rally_winner"] = (df["is_rally_winner"].map(lambda x: str(x).lower() if pd.notnull(x) else None).map({"1": 1, "0": 0, "true": 1, "false": 0, "yes": 1, "no": 0}).astype("int"))
    df["is_forced_error"] = (df["is_forced_error"].map(lambda x: str(x).lower() if pd.notnull(x) else None).map({"1": 1, "0": 0, "true": 1, "false": 0, "yes": 1, "no": 0}).astype("int"))
    df["is_unforced_error"] = (df["is_unforced_error"].map(lambda x: str(x).lower() if pd.notnull(x) else None).map({"1": 1, "0": 0, "true": 1, "false": 0, "yes": 1, "no": 0}).astype("int"))
    df["is_unret"] = (df["is_unret"].map(lambda x: str(x).lower() if pd.notnull(x) else None).map({"1": 1, "0": 0, "true": 1, "false": 0, "yes": 1, "no": 0}).astype("int"))
    df['has_df_distance'] = df['df_distance'].notna().astype(int)
    df['df_distance'] = df['df_distance'].notna().astype(int)
    
    #df.to_parquet(DATA_DIR / "dev/charting-points.parquet", engine="pyarrow", index=False)
    df = add_hazard_df_distance(df)
    df['has_second_serve'] = (df['first_serve_rally_status'] != 'valid').astype(int)
    df["first_serve_in_play"] = df["first_serve_in_play"].astype(int)
    df['second_serve_in_play'] = df['second_serve_in_play'].fillna(0).astype(int)

    # Features
    # "point_number", "first_no_lets", "second_no_lets", 
    
    df = df[cols_to_keep + point_outcomes].copy() # ["match_id", "point_number"]
    print(df["second_serve_in_play"].value_counts())
    print(df["has_second_serve"].value_counts())

    #print(df.head(20))
    #print(df.info())
    # plot_hazard_df_distance(df)
    quit()

    features = df[cols_to_keep].copy()
    meta = df[meta_cols]
    
    # Standard Scaling
    mean = features.mean(axis=0)
    std = features.std(axis=0)
    X = (features - mean) / std
    
    scaled_features = pd.DataFrame(X, columns=cols_to_keep)
    scaled_features["df_distance_missing"] = df["df_distance_missing"].values
    scaled_features = scaled_features.clip(-5, 5)


    """
    # Logging Statistics
    print("\n======================================")
    print("Describe Scaled Features")
    print("======================================")
    print(f"{scaled_features.describe().T}\n")
    skew = skewness(scaled_features)
    var = variance(scaled_features)
    tail_mass = tail_mass_z(scaled_features, cols_to_keep)
    tail_outliers = print_tail_outliers(scaled_features, cols_to_keep, std_target=3)
    cov = covariance(scaled_features)
    corr = correlation_matrix(scaled_features, cols_to_keep, plot=False)
    eigvals = eigen_values(cov)
    print_multi_lag_acf(df, cols_to_keep, lags=(1,50))
    """

    scaled_features["match_id"] = meta["match_id"].values
    scaled_features["point_number"] = meta["point_number"].values
    gmm_hmm(scaled_features)
    
    
    """
    # Plot Auto Correlation Function
    for c in cols_to_keep:
        acf = plot_acf(scaled_features[c].dropna(), lags=50, bartlett_confint=True) # alpha=0.05)
        plt.title(f"ACF - {c}")
        plt.show()

    # Plot(s)
    fig, axes = plt.subplots(1, 2, figsize=(12,5))
    df[cols_to_keep].boxplot(ax=axes[0], grid=False)
    scaled_features.boxplot(ax=axes[1], grid=False, return_type="both")
    axes[0].set_title("Before Scaling")
    axes[1].set_title("After Scaling")

    for ax in axes:
        ax.tick_params(axis="x", rotation=45)
    plt.tight_layout()
    plt.show()
    """



    

    #print(acf)
    # print("\n--------------------------------------")
    # print(f"Raw Auto Correlation")
    # print("--------------------------------------")
    # raw_results = temporal_sanity_check(df, cols_to_keep, group_col="match_id", time_col="point_number")
    # print(raw_results)

"""
def build_is_rally_single(serve_no, is_in):
    is_rally = pd.Series(pd.NA, index=serve_no.index, dtype="Int64")

    valid = serve_no.notna()
    in_play = is_in.eq(1)

    long_rally = serve_no.str.len().fillna(0).gt(2)
    ends_with_c = serve_no.str.endswith("C", na=False)

    is_rally.loc[valid & in_play & (long_rally | ends_with_c)] = 1
    is_rally.loc[valid & (is_in.eq(0))] = 0
    is_rally.loc[~valid] = pd.NA

    return is_rally
"""

"""
(E) Missing value / segmentation check

You didn't explicitly validate:

NaNs per feature after scaling
segment imbalance (players, matches, surfaces)

This matters because HMMs are sensitive to:

uneven transition distributions across matches

(F) Scale stability check (very important in sports data)

Even though standardized:

Check:

does scaling leak across matches?

Better practice: scale within match, not globally

Otherwise:

match pressure becomes “cross-match comparable”
which can distort state learning

"""


"""
# Set Pressure
total_games = df["server_games"] + df["returner_games"]
time_pressure_games = np.minimum(total_games / 13, 1.0)
closeness_games = np.maximum(1 - (np.abs(df["server_game_diff"]) / 6), 0)
df["set_pressure"] = 0.5 * time_pressure_games + 0.5 * closeness_games
"""