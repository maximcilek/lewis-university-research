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
    # players["gender"] = players["gender"].map({"M": 1, "F": 0}).fillna(-1)
    players["ht"] = pd.to_numeric(players["ht"], errors="coerce").astype("Int64")
    # players['hand'] = players['hand'].fillna('U')  # Unknown
    # players['hand'] = players['hand'].map({'R': 1, 'L': 0, 'U': -1})
    
    # print(f"Unique Backhands: {players['backhand'].unique()}") # ['2', '', '1', nan]
    players['backhand'] = players['backhand'].replace(['', None, pd.NA], '-1') # Fill missing or empty backhand
    players['backhand'] = players['backhand'].replace({'R': 1, 'L': 0, 'U': -1}) # Map letters to integers
    players['backhand'] = pd.to_numeric(players['backhand'], errors='coerce').fillna(-1).astype(int) # Convert everything to numeric, coercing errors (anything not convertable becomes NaN)
    players.set_index("url_parameter_name", inplace=True)
    return players

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns


def analyze_players(players):
    # --- Basic Info ---
    print("Missing values per column:")
    print(players.isna().sum())

    # --- Feature Engineering ---
    players['age'] = (pd.Timestamp('today') - players['dob']).dt.days // 365

    # --- Styling ---
    sns.set_style("whitegrid")

    # --- Layout using GridSpec ---
    fig = plt.figure(figsize=(20, 14))
    gs = fig.add_gridspec(3, 3, hspace=0.3, wspace=0.3)

    # Top row
    ax_gender = fig.add_subplot(gs[0, 0])
    ax_hand = fig.add_subplot(gs[0, 1])

    # Middle row
    ax_male_age = fig.add_subplot(gs[1, 0])
    ax_female_age = fig.add_subplot(gs[1, 1])

    # Right column (full height for countries)
    ax_country = fig.add_subplot(gs[:, 2])

    # --- Gender Distribution ---
    sns.countplot(
        data=players,
        x='gender',
        order=players['gender'].value_counts().index,
        ax=ax_gender,
        palette=['skyblue', 'pink']
    )
    ax_gender.set_title("Gender Distribution")
    ax_gender.set_xlabel("Gender")
    ax_gender.set_ylabel("Count")

    # --- Hand Distribution by Gender ---
    sns.countplot(
        data=players,
        x='hand',
        hue='gender',
        ax=ax_hand,
        palette=['pink', 'skyblue']
    )
    ax_hand.set_title("Hand Distribution by Gender")
    ax_hand.set_xlabel("Hand")
    ax_hand.set_ylabel("Count")

    # --- Country Distribution (Top 20) ---
    top_countries = players['country'].value_counts().index[:20]

    sns.countplot(
        data=players,
        y='country',
        hue='gender',
        order=top_countries,
        ax=ax_country,
        palette=['pink', 'skyblue']
    )

    ax_country.set_title("Top 20 Countries by Gender")
    ax_country.set_xlabel("Count")
    ax_country.set_ylabel("")  # remove clutter
    ax_country.tick_params(axis='y', labelsize=9)

    # --- Age Distributions ---
    male_data = players[players['gender'] == 'M']['age'].dropna()
    female_data = players[players['gender'] == 'F']['age'].dropna()

    sns.histplot(male_data, bins=20, kde=True, ax=ax_male_age, color='skyblue')
    ax_male_age.set_title("Male Players - Age Distribution")
    ax_male_age.set_xlabel("Age")
    ax_male_age.set_ylabel("Count")

    sns.histplot(female_data, bins=20, kde=True, ax=ax_female_age, color='pink')
    ax_female_age.set_title("Female Players - Age Distribution")
    ax_female_age.set_xlabel("Age")
    ax_female_age.set_ylabel("Count")

    # --- Final Layout ---
    plt.tight_layout()
    plt.show()
    quit()

def load_matches_df(matches):
    matches = pd.json_normalize(tennisabstract_data.charting_matches)
    matches = matches.drop(columns=["player_1.display_name", "player_2.display_name"])
    for match_col in ["match_date"]:
        matches[match_col] = pd.to_datetime(matches[match_col].replace(["", "0", 0], pd.NA), format="%Y%m%d", errors="coerce")
    matches["player_1_id"] = matches["player_1.profile_url"].apply(lambda x: x.split("?p=")[1])
    matches["player_2_id"] = matches["player_2.profile_url"].apply(lambda x: x.split("?p=")[1])
    matches = matches.drop(columns=["player_1.profile_url", "player_2.profile_url"])
    return matches

"""
def plot_shot_timeline(df, target_point):
    import pandas as pd
    import matplotlib.pyplot as plt

    # --- Filter to ONE point ---
    df_point = df[df['point_number'].astype(int) == target_point]

    if df_point.empty:
        print(f"No data found for point {target_point}")
        return

    rows = []

    for _, row in df_point.iterrows():
        shots = row['shots']

        if not isinstance(shots, list):
            continue

        for shot_idx, shot in enumerate(shots):
            for d in shot.get('details', []):
                rows.append({
                    'shot_num': shot_idx + 1,
                    'shot_type': d.get('description', 'Unknown'),
                })

    shots_df = pd.DataFrame(rows)

    if shots_df.empty:
        print("No shot data available")
        return

    # --- Plot ---
    plt.figure(figsize=(10, 4))

    # Convert shot_type to ordered categorical positions
    shots_df['shot_type'] = shots_df['shot_type'].astype(str)

    # Create numeric mapping for clean spacing
    shot_order = {v: i for i, v in enumerate(shots_df['shot_type'].unique())}
    shots_df['y'] = shots_df['shot_type'].map(shot_order)

    plt.scatter(
        shots_df['shot_num'],
        shots_df['y'],
        s=100
    )

    # Label each point with shot number
    for _, row in shots_df.iterrows():
        plt.text(
            row['shot_num'],
            row['y'],
            str(row['shot_num']),
            ha='center',
            va='center',
            fontsize=8,
            color='white'
        )

    # Y-axis labels
    plt.yticks(list(shot_order.values()), list(shot_order.keys()))

    plt.title(f"Shot Sequence for Point {target_point}")
    plt.xlabel("Shot Number")
    plt.ylabel("Shot Type")

    plt.grid(axis='x', linestyle='--', alpha=0.3)
    plt.tight_layout()
    plt.show()

def plot_shot_timeline(df, match_id=None, target_point=None):
    import pandas as pd
    import matplotlib.pyplot as plt

    # --- Filter by match if specified ---
    if match_id is not None:
        df = df[df['match_id'] == match_id]

    # --- Sort by match/set/game/point for correct rally sequence ---
    df = df.sort_values(by=['match_id','set_1','game_number','point_number']).reset_index(drop=True)

    # --- Filter to a single point if specified ---
    if target_point is not None:
        df = df[df['point_number'].astype(int) == target_point]

    if df.empty:
        print("No data available for the specified point/match.")
        return

    rows = []
    for _, row in df.iterrows():
        shots = row['shots']
        server = row['server_player_number']

        if not isinstance(shots, list):
            continue

        for shot_idx, shot in enumerate(shots):
            details = shot.get('details', [])
            for d in details:
                rows.append({
                    'point_num': int(row['point_number']),
                    'shot_num': shot_idx + 1,
                    'shot_type': d.get('description','Unknown'),
                    'server': server
                })

    shots_df = pd.DataFrame(rows)
    if shots_df.empty:
        print("No shot data available after flattening.")
        return

    # --- Ensure shots are sorted by rally sequence ---
    shots_df = shots_df.sort_values(by=['point_num','shot_num']).reset_index(drop=True)

    # --- Assign player_turn alternating starting with server ---
    player_turns = []
    current_point = None
    counter = 0
    for _, row in shots_df.iterrows():
        if row['point_num'] != current_point:
            current_point = row['point_num']
            counter = 0
        player_turns.append('Server' if counter % 2 == 0 else 'Returner')
        counter += 1
    shots_df['player_turn'] = player_turns

    # --- Map shot_type to numeric y for plotting ---
    shots_df['shot_type'] = shots_df['shot_type'].astype(str)
    shot_order = {v:i for i,v in enumerate(shots_df['shot_type'].unique())}
    shots_df['y'] = shots_df['shot_type'].map(shot_order)

    # --- Colors ---
    colors = {'Server':'skyblue', 'Returner':'salmon'}

    # --- Plot ---
    plt.figure(figsize=(12,6))
    for turn in ['Server','Returner']:
        subset = shots_df[shots_df['player_turn']==turn]
        plt.scatter(
            subset['shot_num'],
            subset['y'],
            s=100,
            color=colors[turn],
            label=turn,
            alpha=0.8
        )
        for _, row in subset.iterrows():
            plt.text(
                row['shot_num'],
                row['y'],
                str(row['shot_num']),
                ha='center',
                va='center',
                fontsize=8,
                color='white'
            )

    plt.yticks(list(shot_order.values()), list(shot_order.keys()))
    plt.xticks(range(1, shots_df['shot_num'].max()+1))
    plt.xlabel("Shot Number in Rally")
    plt.ylabel("Shot Type")
    title = "Shot Sequence"
    if match_id: title += f" - Match {match_id}"
    if target_point: title += f" - Point {target_point}"
    plt.title(title + " (Server vs Returner)")
    plt.grid(axis='x', linestyle='--', alpha=0.3)
    plt.legend()
    plt.tight_layout()
    plt.show()
    
def plot_first_point_rally(df):
    import pandas as pd
    import matplotlib.pyplot as plt

    # --- Pick first match ---
    first_match = df['match_id'].iloc[0]
    df_match = df[df['match_id'] == first_match]

    # --- Sort by set, game, point for proper rally order ---
    df_match = df_match.sort_values(by=['set_1', 'game_number', 'point_number']).reset_index(drop=True)

    # --- Pick first point ---
    first_point = int(df_match['point_number'].iloc[0])
    df_point = df_match[df_match['point_number'].astype(int) == first_point]

    if df_point.empty:
        print("No shots found for the first point of this match.")
        return

    # --- Flatten shots ---
    rows = []
    for _, row in df_point.iterrows():
        shots = row['shots']
        server = row['server_player_number']

        if not isinstance(shots, list):
            continue

        for shot_idx, shot in enumerate(shots):
            details = shot.get('details', [])
            for d in details:
                rows.append({
                    'shot_num': shot_idx + 1,
                    'shot_type': d.get('description', 'Unknown')
                })

    shots_df = pd.DataFrame(rows)
    if shots_df.empty:
        print("No shot details available for this point.")
        return

    # --- Ensure shots are in rally order ---
    shots_df = shots_df.sort_values(by='shot_num').reset_index(drop=True)

    # --- Assign player_turn alternating starting with server ---
    player_turns = ['Server' if i % 2 == 0 else 'Returner' for i in range(len(shots_df))]
    shots_df['player_turn'] = player_turns

    # --- Map shot_type to numeric y for plotting ---
    shots_df['shot_type'] = shots_df['shot_type'].astype(str)
    shot_order = {v: i for i, v in enumerate(shots_df['shot_type'].unique())}
    shots_df['y'] = shots_df['shot_type'].map(shot_order)

    # --- Colors ---
    colors = {'Server':'skyblue', 'Returner':'salmon'}

    # --- Plot ---
    plt.figure(figsize=(12,6))
    for turn in ['Server','Returner']:
        subset = shots_df[shots_df['player_turn'] == turn]
        plt.scatter(
            subset['shot_num'],
            subset['y'],
            s=100,
            color=colors[turn],
            label=turn,
            alpha=0.8
        )
        for _, row in subset.iterrows():
            plt.text(
                row['shot_num'],
                row['y'],
                str(row['shot_num']),
                ha='center',
                va='center',
                fontsize=8,
                color='white'
            )

    plt.yticks(list(shot_order.values()), list(shot_order.keys()))
    plt.xticks(range(1, shots_df['shot_num'].max() + 1))
    plt.xlabel("Shot Number in Rally")
    plt.ylabel("Shot Type")
    plt.title(f"Rally Visualization - Match {first_match}, Point {first_point} (Server vs Returner)")
    plt.grid(axis='x', linestyle='--', alpha=0.3)
    plt.legend()
    plt.tight_layout()
    plt.show()
"""


# round_dict = {"R16": 9, "W": 14, "F": 13, "RR": 8, "R64": 6, "R128": 5, "QF": 10, "SF": 11, "R32": 7, 'Q1': 1, 'Q2': 2, 'Q3': 3, 'Q4': 4, "": 0, "BR": 12}
# hand_dict = {'1': 'Left', '2': 'Right', '': 'Unknown'}

def build_dict(seq, key):
    return dict((d[key], dict(d, index=index)) for (index, d) in enumerate(seq))

if __name__ == "__main__":
    LOGGER.info("Loading TennisAbstract Data")

    tennisabstract_data = models.tennisabstract_data.TennisAbstractData(
        "data/canonical/tennisabstract/players.parquet",
        "data/canonical/tennisabstract/charting_matches.parquet",
        "data/canonical/tennisabstract/charting_points.csv"
    )

    all_players = []
    for players_batch in tennisabstract_data.players:
        for p in players_batch.to_pylist():
            p["player_id"] = p.get("url_parameter_name")
            del p["url_parameter_name"]
            del p["elo_rank"]
            del p["elo_rating"]
            del p["dob_approx"]
            del p["lastdate"]
            if p["nameparam"] in [None, ""]:
                p["nameparam"] = p["player_id"]
            
            all_players.append(p)
    print(f"Players: {len(all_players)} ({type(all_players)}) - {(all_players[0].keys())}")
    players_by_id = build_dict(all_players, key="player_id")




    all_matches = []
    for match in tennisabstract_data.charting_matches:
        match_batch = match.to_pylist()
        for m in match_batch:
            player1 = m.get("player_1")
            player2 = m.get("player_2")
            del m["player_1"]
            del m["player_2"]
            m["player_1_id"] = player1.get("profile_url").split("?p=")[1]
            m["player_2_id"] = player2.get("profile_url").split("?p=")[1]
            if player1.get("won"):
                m["winner"] = 1
            elif player2.get("won"):
                m["winner"] = 2
            else:
                m["winner"] = None

            print(players_by_id.get(m.get("player_1_id")))
            print(players_by_id.get(m.get("player_2_id")))
            print(m)
            quit()

            all_matches.append(m)

    print(f"Matches: {len(all_matches)} ({type(all_matches)}) - {type(all_matches[0])}")
    LOGGER.debug(f"Match: {all_matches[0]}")
    matches_by_id = build_dict(all_matches, key="match_id")
    # print(matches_by_id.get("20260322-W-Miami-R32-Iva_Jovic-Talia_Gibson"))
    





    # parquet_file = pq.ParquetFile(tennisabstract_data.charting_points_file_path)
    # total_points = parquet_file.metadata.num_rows
    # chunk_size = 10_000
    # chunk = []
    # for i, point in enumerate(tennisabstract_data.charting_points, 1):
    #     print(point)
    #     quit()
        # # feature engineering per chunk
        # # normalize numerical values
        # # convert categorical → embeddings or one-hot
        # Pad sequences to the longest match or truncate.
        # Batch sequences for training.
        
        
        
    
    quit()

    #players = pd.DataFrame(tennisabstract_data.players)
    #matches = pd.DataFrame(tennisabstract_data.charting_matches)
    #points = pd.DataFrame(tennisabstract_data.charting_points)

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

"""
chunk.append(point)
        # Log progress every chunk
        if i % chunk_size == 0 or i == total_points:
            percent = (i / total_points) * 100
            LOGGER.info("Processed %d / %d points (%.2f%%)", i, total_points, percent)
            df_chunk = pd.DataFrame(chunk)
            # Do analysis on this chunk
            #print(df_chunk.info())
            #print(df_chunk.head())

            # Assuming df_chunk is your DataFrame chunk

            # Explode shots per point
            df_exploded = df_chunk.explode('shots').reset_index(drop=True)

            # Normalize shots dictionaries
            shots_flat = pd.json_normalize(df_exploded['shots'])

            # Explode details within each shot
            df_details_exploded = shots_flat.explode('details').reset_index(drop=True)

            # Normalize the details dictionaries
            details_flat = pd.json_normalize(df_details_exploded['details'])

            # Combine with shot-level info (point_number, shot_num, player_turn, etc.)
            df_flat = pd.concat([df_details_exploded.drop(columns=['details']), details_flat], axis=1)
            df_final = pd.concat([df_exploded, df_flat], axis=1)
            print(df_flat.info())
            print(df_flat.head())
            print(df_final.info())
            print(df_final.head())
            # Now aggregate descriptions **per point_number and shot_num**
            df_agg = df_final.groupby(
                ['match_id', 'point_number', 'shot_num', 'player_turn'],
                as_index=False
            ).agg({
                'code': lambda x: ' '.join(dict.fromkeys(x))  # removes duplicates, keeps order
            })

            print(df_agg.info())
            print(df_agg.head(30))
            # plot_first_point_rally(df_chunk)
            quit()
            chunk = []
    # Process remaining rows
    if chunk:
        df_chunk = pd.DataFrame(chunk)
        LOGGER.info("Processed remaining %d points", len(chunk))
        print(df_chunk.head())
"""