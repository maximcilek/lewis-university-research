# main.py
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))

import logging
import json
import itertools
import tennisabstractscraper.models as models

import pandas as pd
import pyarrow.parquet as pq
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
LOGGER = logging.getLogger(__name__)

def build_matches_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    df_matches = df.explode("matches").dropna(subset=["matches"])

    matches_df = pd.json_normalize(df_matches["matches"])
    df_matches = df_matches.reset_index(drop=True).join(matches_df)

    # Convert match date
    df_matches['date'] = pd.to_datetime(df_matches['date'], format='%Y%m%d', errors='coerce')

    # Extract year
    df_matches['year'] = df_matches['date'].dt.year

    return df_matches.dropna(subset=['year', 'gender'])

def aggregate_matches_by_year_gender(df_matches: pd.DataFrame) -> pd.DataFrame:
    return (
        df_matches
        .groupby(['gender', 'year'])
        .size()
        .reset_index(name='match_count')
        .sort_values('year')
    )

def plot_matches_over_time(agg: pd.DataFrame, output_path: str):
    fig, axes = plt.subplots(1, 2, figsize=(14,6), sharey=True)

    # Male
    male = agg[agg['gender'] == 'M']
    axes[0].plot(male['year'], male['match_count'])
    axes[0].set_title("Male Matches Over Time")
    axes[0].set_xlabel("Year")
    axes[0].set_ylabel("Number of Matches")

    # Female
    female = agg[agg['gender'] == 'F']
    axes[1].plot(female['year'], female['match_count'])
    axes[1].set_title("Female Matches Over Time")
    axes[1].set_xlabel("Year")

    plt.tight_layout()
    plt.savefig(output_path)
    LOGGER.info("Saved plot to %s", output_path)



def clean_date(series):
    return pd.to_datetime(
        series.replace(["", "0", 0], pd.NA),
        format="%Y%m%d",
        errors="coerce"
    )

def load_players_df(players):
    players = pd.DataFrame(players)
    # leave matches out for now and focus on charted matches
    players = players.drop(columns=["nameparam", "twitter", "wiki_id", "dob_approx", "lastdate", "death_date", "elo_rank", "elo_rating", "atp_id", "wta_id", "itf_id", "fc_id", "dc_id", "matches"])
    for player_col in ["dob"]:
        players[player_col] = pd.to_datetime(players[player_col].replace(["", "0", 0], pd.NA), format="%Y%m%d", errors="coerce")
    players["gender"] = players["gender"].map({"M": 1, "F": 0}).fillna(-1)
    players["ht"] = pd.to_numeric(players["ht"], errors="coerce").astype("Int64")
    players['hand'] = players['hand'].fillna('U')  # Unknown
    players['hand'] = players['hand'].map({'R': 1, 'L': 0, 'U': -1})
    players['backhand'] = players['backhand'].replace(['', None, pd.NA], '-1')
    players.set_index("url_parameter_name", inplace=True)
    return players

def load_matches_df(matches):
    matches = pd.json_normalize(tennisabstract_data.charting_matches)
    matches = matches.drop(columns=["player_1.display_name", "player_2.display_name"])
    for match_col in ["match_date"]:
        matches[match_col] = pd.to_datetime(matches[match_col].replace(["", "0", 0], pd.NA), format="%Y%m%d", errors="coerce")
    matches["player_1_id"] = matches["player_1.profile_url"].apply(lambda x: x.split("?p=")[1])
    matches["player_2_id"] = matches["player_2.profile_url"].apply(lambda x: x.split("?p=")[1])
    matches = matches.drop(columns=["player_1.profile_url", "player_2.profile_url"])

# round_dict = {"R16": 9, "W": 14, "F": 13, "RR": 8, "R64": 6, "R128": 5, "QF": 10, "SF": 11, "R32": 7, 'Q1': 1, 'Q2': 2, 'Q3': 3, 'Q4': 4, "": 0, "BR": 12}
# hand_dict = {'1': 'Left', '2': 'Right', '': 'Unknown'}
if __name__ == "__main__":
    LOGGER.info("Loading TennisAbstract Data")

    tennisabstract_data = models.tennisabstract_data.TennisAbstractData(
        "data/canonical/tennisabstract/players.parquet",
        "data/canonical/tennisabstract/charting_matches.parquet",
        "data/canonical/tennisabstract/charting_shots.parquet"
    )

    players = load_players_df(tennisabstract_data.players)
    matches = load_matches_df(tennisabstract_data.charting_matches)

    parquet_file = pq.ParquetFile(tennisabstract_data.charting_points_file_path)
    total_points = parquet_file.metadata.num_rows

    chunk_size = 10_000
    chunk = []

    for i, point in enumerate(tennisabstract_data.charting_points, 1):
        chunk.append(point)

        # Log progress every chunk
        if i % chunk_size == 0 or i == total_points:
            percent = (i / total_points) * 100
            LOGGER.info("Processed %d / %d points (%.2f%%)", i, total_points, percent)
            df_chunk = pd.DataFrame(chunk)
            # Do analysis on this chunk
            print(df_chunk.head())
            chunk = []

    # Process remaining rows
    if chunk:
        df_chunk = pd.DataFrame(chunk)
        LOGGER.info("Processed remaining %d points", len(chunk))
        print(df_chunk.head())
    
    quit()

    #players = pd.DataFrame(tennisabstract_data.players)
    #matches = pd.DataFrame(tennisabstract_data.charting_matches)
    #points = pd.DataFrame(tennisabstract_data.charting_points)

    print(players.info())
    print("---------------------------------")
    print(matches.info())
    print("---------------------------------")
    # print(points.info())

    # df_matches = build_matches_dataframe(df_matches)
    # agg = aggregate_matches_by_year_gender(df_matches)
    # plot_matches_over_time(agg, "matches_over_time.png")
















"""
    # Check for missing gender after mapping
    missing_gender_count = df['gender'].isnull().sum()
    if missing_gender_count > 0:
        LOGGER.warning("Gender missing for %d players, defaulting to 'M'", missing_gender_count)
        df['gender'] = df['gender'].fillna('M')

    # Clean gender column
    df['gender'] = df['gender'].str.upper().str.strip()
    df = df[df['gender'].isin(['M','F'])]

    # -------------------
    # Calculate age
    # -------------------
    df['dob'] = pd.to_datetime(df['dob'], format='%Y%m%d', errors='coerce')
    today = pd.to_datetime("today")
    df['age'] = (today - df['dob']).dt.days // 365
    df = df.dropna(subset=['age', 'gender'])

    LOGGER.info("Players by gender after URL mapping:\n%s", df['gender'].value_counts())

    # -------------------
    # Plot distribution
    # -------------------
    fig, axes = plt.subplots(1, 2, figsize=(14,6), sharey=True)

    # Male plot
    sns.histplot(
        data=df[df['gender'] == 'M'],
        x='age',
        binwidth=5,
        ax=axes[0],
        hue="gender",
        palette={'M': 'skyblue'}
    )
    axes[0].set_title("Male Players Age Distribution")
    axes[0].set_xlabel("Age")

    # Female plot
    sns.histplot(
        data=df[df['gender'] == 'F'],
        x='age',
        binwidth=5,
        ax=axes[1],
        hue="gender",
        palette={'F': 'pink'}
    )
    axes[1].set_title("Female Players Age Distribution")
    axes[1].set_xlabel("Age")

    plt.tight_layout()
    plt.savefig("player_age_distribution.png")
    LOGGER.info("Saved split gender distribution to player_age_distribution_split.png")
"""