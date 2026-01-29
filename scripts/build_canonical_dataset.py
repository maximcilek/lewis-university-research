import pandas as pd
from pathlib import Path
import csv
import hashlib
import unicodedata
import re

def find_repo_root(start_path=None):
    """
    Walk upward until a .git directory is found.
    Returns the repo root as a Path.
    """
    current = Path(start_path or __file__).resolve()
    for parent in [current] + list(current.parents):
        if (parent / ".git").exists():
            return parent
    raise RuntimeError("Not inside a Git repository")

def get_file_encoding_type(file_path):
    """
    Tries common text encodings and returns the first one that successfully
    reads the CSV header.
    """
    file_path = Path(file_path).resolve()
    encodings = ["utf-8", "cp1252", "latin-1"]

    for enc in encodings:
        try:
            with open(file_path, newline="", encoding=enc) as f:
                reader = csv.reader(f)
                next(reader)  # Try reading header
            return enc
        except UnicodeDecodeError:
            continue

    raise UnicodeDecodeError(
        "utf-8",
        b"",
        0,
        1,
        f"Could not determine encoding for file: {file_path}"
    )

def normalize_name(name: str) -> str:
    if pd.isna(name):
        return None
    name = str(name).strip()
    # Remove accents
    name = unicodedata.normalize("NFKD", name)
    name = "".join(c for c in name if not unicodedata.combining(c))
    name = name.lower()
    # Remove punctuation except spaces
    name = re.sub(r"[^a-z\s]", " ", name)
    # Collapse whitespace
    name = re.sub(r"\s+", " ", name).strip()
    return name

def generate_player_id(canonical_name: str) -> str:
    h = hashlib.sha1(canonical_name.encode("utf-8")).hexdigest()
    return f"p_{h[:8]}"

# Add a helper to get gender from match_id
def get_gender_from_match_id(match_id: str) -> str:
    """
    Returns 'M' for men or 'W' for women based on the match_id convention.
    Example match_id: '20251221-M-NextGen_Finals-F-Alexander_Blockx-Learner_Tien'
    """
    try:
        # Split by '-' and take the second token
        gender_token = match_id.split("-")[1]
        if gender_token in ("M", "W"):
            return gender_token
    except Exception:
        pass
    return None  # fallback if parsing fails


def clean_matches(path, output_directory):
    file_path = Path(path)
    if not file_path.exists():
        print(f"[ERROR] - Directory does not exist: {file_path}")
        return
    
    # for file_path in matches_directory.rglob("*"):
    if not file_path.is_file():
        print(f"[FATAL] - File path is not a file: {path}")
        quit()
    
    try:
        df = pd.read_csv(file_path, encoding=get_file_encoding_type(file_path), on_bad_lines="error")
    except Exception as e:
        print(f"[FATAL] - Failed to load {file_path.name}: {e}")
        quit()
    shape = df.shape
    print(f"Successfully loaded dataframe: {file_path.name} ({shape[0]}x{shape[1]})")
    print(df.head())
    df.columns = [c.strip() for c in df.columns]
    print(f"Column Names: {df.columns.to_list()}")

    player_rows = []

    for idx, row in df.iterrows():
        gender = get_gender_from_match_id(row["match_id"])
        for side in [1, 2]:
            name_col = f"Player {side}"
            hand_col = f"Pl {side} hand"
            display_name = row[name_col]
            canonical_name = normalize_name(display_name)

            if not canonical_name:
                print(f"[FATAL] - Player name is not canonical: {row}")
                quit() # continue
            player_rows.append({"display_name": display_name, "canonical_name": canonical_name, "handedness": row.get(hand_col), "date": row.get("Date"), "gender": gender})

    players_df = pd.DataFrame(player_rows)

    # Aggregate into unique players
    players = (players_df.groupby("canonical_name", as_index=False).agg(display_name=("display_name", "first"), handedness=("handedness", "first"), gender=("gender", "first"), first_seen=("date", "min"), last_seen=("date", "max")))
    players["player_id"] = players["canonical_name"].apply(generate_player_id)
    players = players[["player_id", "canonical_name", "display_name", "handedness", "gender", "first_seen", "last_seen"]]
    # Build lookup
    id_lookup = dict(zip(players["canonical_name"], players["player_id"]))
    
    # Rewrite matches
    def map_player(name):
        return id_lookup.get(normalize_name(name))

    df["player1_id"] = df["Player 1"].apply(map_player)
    df["player2_id"] = df["Player 2"].apply(map_player)
    df_clean = df.drop(columns=["Player 1", "Player 2", "Pl 1 hand", "Pl 2 hand"])

    # Reorder columns
    front_cols = ["match_id", "player1_id", "player2_id"]
    remaining = [c for c in df_clean.columns if c not in front_cols]
    df_clean = df_clean[front_cols + remaining]

    print(f"\n----------- CLEAN DF {df_clean.shape} -------------")
    print(df_clean.head())
    print(f"\nColumn Names: {df_clean.columns.to_list()}")

    print(f"\n\n----------- SAVING -------------")
    players_output_path = output_directory / "players.csv"
    matches_output_path = output_directory / "matches.csv"
    players.to_csv(players_output_path, index=False)
    df_clean.to_csv(matches_output_path, index=False)
    print(f"Players written to: {players_output_path}")
    print(f"Matches written to: {matches_output_path}")

    print(f"\n\n----------- SUMMARY -------------")
    print(f"Status: SUCCESS")
    print(f"Total players: {len(players)}")
    print(f"Total matches: {len(df_clean)}")

if __name__ == "__main__":
    root = find_repo_root()
    data_directory = root / "data" / "raw"
    output_data_directory = root / "data" / "canonical"
    matches_file = data_directory / "matches" / "matches.csv"
    # points_file = data_directory / "points" / "m-points-2010s.csv"

    print(f"[INFO] - Repository Root: {root}")
    print(f"[INFO] - Data Directory: {data_directory}")
    clean_matches(matches_file, output_data_directory)