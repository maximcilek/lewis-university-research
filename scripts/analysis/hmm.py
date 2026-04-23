import pandas as pd
import pathlib
import numpy as np
from collections import defaultdict
# import sys
# sys.path.append(str(pathlib.Path(__file__).resolve().parent.parent.parent))

import pyarrow.parquet as pq
from sklearn.preprocessing import StandardScaler, RobustScaler
import matplotlib.pyplot as plt
import seaborn as sns
from statsmodels.tsa.stattools import acf
from statsmodels.graphics.tsaplots import plot_acf
from hmmlearn.hmm import GaussianHMM, GMMHMM

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

def build_serve_features(df):
    df = df.copy()

    srv1 = df["first_serve_rally"].astype("string").str.strip().str.replace("c", "", regex=False)
    srv2 = df["second_serve_rally"].astype("string").str.strip().str.replace("c", "", regex=False)

    srv1_is_empty = srv1.isna() | (srv1 == "")
    srv2_is_empty = srv2.isna() | (srv2 == "")

    srv1_is_generic = srv1.isin(["R", "S"])
    srv1_is_penalty = srv1.isin(["P", "Q"])
    srv1_is_fault = srv1.str.contains(r"\*?\d*[gnedVxw]$", na=False)
    srv1_is_let = srv1.str.contains(r"\*?\d*c$", na=False)
    srv1_is_valid = ~(srv1_is_empty | srv1_is_generic | srv1_is_penalty | srv1_is_fault | srv1_is_let)

    srv2_is_generic = srv2.isin(["R", "S"])
    srv2_is_penalty = srv2.isin(["P", "Q"])
    srv2_is_fault = srv2.str.contains(r"\*?\d*[gnedVxw]$", na=False)
    srv2_is_let = srv2.str.contains(r"\*?\d*c$", na=False)
    srv2_is_valid = ~(srv2_is_empty | srv2_is_generic | srv2_is_penalty | srv2_is_fault | srv2_is_let)

    df["first_serve_rally_status"] = np.select(
        [srv1_is_generic, srv1_is_penalty, srv1_is_fault, srv1_is_let, srv1_is_empty, srv1_is_valid],
        ["generic", "penalty", "fault", "let", "unknown", "valid"],
        default="unknown"
    )

    df["second_serve_rally_status"] = np.select(
        [ srv2_is_generic, srv2_is_penalty, srv2_is_fault, srv2_is_let, srv2_is_empty, srv2_is_valid],
        ["generic", "penalty", "fault", "let", "unknown", "valid"],
        default="unknown"
    )

    df["serve_info_missing"] = df["first_serve_in_play"].isna().astype(int)

    df["first_serve_in_play_clean"] = np.select(
        [
            df["first_serve_rally_status"].isin(["generic", "fault", "penalty", "let"]),
            df["first_serve_rally_status"].eq("unknown"),
            df["first_serve_rally_status"].eq("valid")
        ],
        [
            0,                                  # confirmed non-in-play or invalid structured event
            np.nan,                             # truly unknown
            df["first_serve_in_play"]           # trusted signal
        ],
        default=np.nan
    )

    df["second_serve_in_play_clean"] = np.select(
        [
            df["second_serve_rally_status"].isin(["generic", "fault", "penalty", "let"]),
            df["second_serve_rally_status"].eq("unknown"),
            df["second_serve_rally_status"].eq("valid")
        ],
        [
            0,                                  # confirmed non-in-play or invalid structured event
            np.nan,                             # truly unknown
            df["second_serve_in_play"]           # trusted signal
        ],
        default=np.nan
    )

    print(df["first_serve_rally_status"].value_counts(dropna=False))
    print(df["first_serve_in_play"].value_counts(dropna=False))
    print(df["first_serve_in_play_clean"].value_counts(dropna=False))
    quit()
    return df


if __name__ == "__main__":

    # =========================
    # LOAD DATA
    # =========================
    DATA_DIR = pathlib.Path(__file__).resolve().parent.parent.parent / "data"
    parquet_file = pq.ParquetFile(DATA_DIR / "prod/charting-points.parquet")
    df = load_parquet(parquet_file)
    df = df[df["match_date"] > "2000-01-01"]
    if "match_id" in df.columns and "point_number" in df.columns:
        df = df.sort_values(["match_id", "point_number"])

    df = df[df["match_id"] != "20241127-M-Maia_CH-R32-Pedro_Araujo-Alex_Marti_Pujolras"]

    #print(df["first_serve_rally"].value_counts(dropna=False))
    #print(df["first_serve_in_play"].value_counts(dropna=False))

    df = build_serve_features(df)

    # print(df.head())
    quit()
    """
    # Set Pressure
    total_games = df["server_games"] + df["returner_games"]
    time_pressure_games = np.minimum(total_games / 13, 1.0)
    closeness_games = np.maximum(1 - (np.abs(df["server_game_diff"]) / 6), 0)
    df["set_pressure"] = 0.5 * time_pressure_games + 0.5 * closeness_games
    """

    # Features
    cols_to_keep = ["first_serve_in_play", "match_pressure", "set_pressure", "game_pressure", "server_point_diff", "df_distance",
    "is_server_winner", "is_unret", "rally_count"]
    point_outcomes = [
        "is_forced_error",
        "is_unforced_error",
        "is_double",
        "is_rally_winner",
        "is_ace"
    ]

    # count how many True per row
    true_counts = df[point_outcomes].sum(axis=1)

    # valid rows: 0 or 1 True
    valid_mask = true_counts <= 1

    print(f"Valid rows: {valid_mask.sum()}")
    print(f"Invalid rows (multiple outcomes): {(~valid_mask).sum()}")
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
(E) Missing value / segmentation check

You didn’t explicitly validate:

NaNs per feature after scaling
segment imbalance (players, matches, surfaces)

This matters because HMMs are sensitive to:

uneven transition distributions across matches

(F) Scale stability check (very important in sports data)

Even though standardized:

Check:

does scaling leak across matches?

Better practice:
👉 scale within match, not globally

Otherwise:

match pressure becomes “cross-match comparable”
which can distort state learning

"""