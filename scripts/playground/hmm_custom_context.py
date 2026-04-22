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
from sklearn.metrics import mutual_info_score

def load_parquet(fp):
    chunks = []
    for batch in parquet_file.iter_batches(batch_size=10000):
        chunk = batch.to_pandas()
        chunks.append(chunk)
    return pd.concat(chunks, ignore_index=True)

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
        plt.figure(figsize=(12, 8))
        sns.heatmap(corr, annot=True, fmt=".8f", cmap="coolwarm", center=0)
        plt.title("Feature Correlation Matrix")
        plt.tight_layout()
        plt.show()
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

def autocorr_lag(df, cols, lag=1):
    return df[cols].apply(lambda x: safe_autocorr(x, lag=lag))

def safe_autocorr(series, lag):
    s = series.dropna().astype(float)

    # must have enough raw values
    if len(s) <= lag + 1:
        return np.nan

    # create lagged alignment explicitly (THIS is the fix)
    x = s.iloc[:-lag]
    y = s.iloc[lag:]

    # remove misalignment NaNs (safety)
    mask = x.notna() & y.notna()
    x = x[mask]
    y = y[mask]

    if len(x) < 10:
        print("small lag sample:", lag, series.name)

    # need enough paired points
    if len(x) < 3:
        return np.nan

    # constant check AFTER lagging (critical fix)
    if x.nunique() <= 1 or y.nunique() <= 1:
        return 0.0

    # final variance safety
    if x.std() == 0 or y.std() == 0:
        return 0.0

    try:
        return np.corrcoef(x, y)[0, 1]
    except Exception:
        return np.nan

def temporal_sanity_check(df, cols, group_col="match_id", time_col="point_number", lag1=1, lag5=5):

    lag1_acc = defaultdict(list)
    lag5_acc = defaultdict(list)

    # ensure only valid columns exist
    cols = [c for c in cols if c in df.columns]

    # 🚨 GLOBAL SORT (important fix)
    df = df.sort_values([group_col, time_col])

    for _, g in df.groupby(group_col):

        # must be sorted already, but enforce anyway
        g = g.sort_values(time_col)

        if len(g) <= lag5 + 1:
            continue

        # KEEP ONLY STABLE COLUMNS PER GROUP
        valid_cols = []
        for c in cols:
            x = g[c]

            # drop useless signals
            if x.isna().mean() > 0.5:
                continue
            if x.nunique(dropna=True) <= 1:
                continue
            if x.std(skipna=True) == 0 or np.isnan(x.std(skipna=True)):
                continue

            valid_cols.append(c)

        if not valid_cols:
            continue

        res1 = autocorr_lag(g, valid_cols, lag1)
        res5 = autocorr_lag(g, valid_cols, lag5)

        for k, v in res1.items():
            if not np.isnan(v):
                lag1_acc[k].append(v)

        for k, v in res5.items():
            if not np.isnan(v):
                lag5_acc[k].append(v)

    lag1_corr = pd.Series({k: np.nanmean(v) if len(v) > 0 else np.nan for k, v in lag1_acc.items()})
    lag5_corr = pd.Series({k: np.nanmean(v) if len(v) > 0 else np.nan for k, v in lag5_acc.items()})

    return pd.DataFrame({
        "lag1_autocorr": lag1_corr,
        "lag5_autocorr": lag5_corr
    }).sort_values("lag1_autocorr", ascending=False)

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

def context_r2(df, feature):
    overall_mean = df[feature].mean()

    between = df.groupby("context_state")[feature].mean()
    counts = df["context_state"].value_counts()

    ss_between = ((between - overall_mean)**2 * counts).sum()
    ss_total = ((df[feature] - overall_mean)**2).sum()

    return ss_between / ss_total
def mi_with_feature(df, feature):
    return mutual_info_score(df["context_state"], pd.qcut(df[feature], 20, duplicates="drop"))

if __name__ == "__main__":

    # =========================
    # LOAD DATA
    # =========================
    DATA_DIR = pathlib.Path(__file__).resolve().parent.parent.parent / "data"
    parquet_file = pq.ParquetFile(DATA_DIR / "dev/tennisabstract/charting-points.parquet")
    df = load_parquet(parquet_file)
    df = df[df["match_date"] > "2000-01-01"]
    df["first_serve_in_play"] = df["first_serve_in_play"].fillna(-1)

    df["df_distance"] = df["df_distance"].fillna(500)
    if "match_id" in df.columns and "point_number" in df.columns:
        df = df.sort_values(["match_id", "point_number"])
    
    # Set Pressure
    total_games = df["server_games"] + df["returner_games"]
    time_pressure_games = np.minimum(total_games / 13, 1.0)
    closeness_games = np.maximum(1 - (np.abs(df["server_game_diff"]) / 6), 0)
    df["set_pressure"] = 0.5 * time_pressure_games + 0.5 * closeness_games

    context_cols = [
        "surface",
        "gender",
        "best_of",
        "server_hand",
        "returner_hand",
        "server_player_rank_bin",
        "returner_player_rank_bin"
    ]
    df["server_rank_bin"] = pd.cut(
        df["server_player_rank"],
        bins=[0, 10, 50, 100, 250, 1000],
        labels=["top10", "top50", "top100", "mid", "low"]
    )

    df["context_state"] = (
        df["surface"].astype(str) + "_" +
        df["gender"].astype(str) + "_" +
        df["best_of"].astype(str) + "_" +
        df["level"].astype(str) + "_" +
        df["server_hand"].astype(str) + "_" +
        df["returner_hand"].astype(str)
    )
    p = df["context_state"].value_counts(normalize=True)
    effective_states = 1 / (p**2).sum()
    #print(effective_states)
    print(f"Context State(s): {effective_states}")
    print(f"Context State Description(s):\n{df['context_state'].value_counts().describe()}")
    print(f"\n\nHow much data each state actually has: {df.groupby('context_state').size().sort_values()}")

    cols_to_keep = [
        "first_serve_in_play",
        "match_pressure",
        "set_pressure",
        "game_pressure",
        "server_point_diff",
        "df_distance"
    ]
    print(f"\nDoes context actually change the dynamics?\n{df.groupby('context_state')[cols_to_keep].mean()}")

    print(f"\n\nVariance explained by context (strong diagnostic)")
    for c in cols_to_keep:
        print(c, context_r2(df, c))

    print(f"\n\nTransition diversity (important for HMM validity): {pd.crosstab(df['context_state'].shift(), df['context_state'])}")
    
    print(f"\n\nMutual information (best single score)")
    for c in cols_to_keep:
        print(c, mi_with_feature(df, c))
    quit()


    # Features
    cols_to_keep = [
        "first_serve_in_play",
        "match_pressure",
        "set_pressure",
        "game_pressure",
        "server_point_diff",
        "df_distance"
    ]
    features = df[cols_to_keep].copy()
    
    # Standard Scaling
    mean = features.mean(axis=0)
    std = features.std(axis=0)
    X = (features - mean) / std
    scaled_features = pd.DataFrame(X, columns=cols_to_keep)

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

    # plot_acf(scaled_features)
    # for c in cols_to_keep:
    #     acf = plot_acf(scaled_features[c].dropna(), lags=50, bartlett_confint=True) # alpha=0.05)
    #     plt.title(f"ACF - {c}")
    #     plt.show()

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