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

def clean_column_name(col_name):
    col_name = str(col_name).strip()            # remove leading/trailing spaces
    col_name = col_name.lower()                 # lowercase
    col_name = re.sub(r"[^\w]", "_", col_name) # replace non-alphanumeric with underscore
    col_name = re.sub(r"_+", "_", col_name)    # collapse multiple underscores
    col_name = col_name.strip("_")             # remove leading/trailing underscores
    return col_name

def is_real_match_row(row):
    """
    A real match row must have:
    - Two player names
    - Names longer than 2 characters
    - At least two tokens (first + last name)
    """
    try:
        p1 = str(row.get("player_1", "")).strip()
        p2 = str(row.get("player_2", "")).strip()
    except Exception:
        return False

    if not p1 or not p2:
        return False

    if len(p1) <= 2 or len(p2) <= 2:
        return False

    if len(p1.split()) < 2 or len(p2.split()) < 2:
        return False
    
    if type(row.get("umpire")) is int:
        return False
    
    if row.get("surface") not in ["Clay", "Hard", "Grass"]:
        return False

    return True


def clean_tennis_matches(path, output_directory):
    file_path = Path(path)
    if not file_path.exists():
        print(f"[ERROR] - Directory does not exist: {file_path}")
        return

    if not file_path.is_file():
        print(f"[FATAL] - File path is not a file: {path}")
        quit()

    try:
        df = pd.read_csv(file_path, encoding=get_file_encoding_type(file_path), on_bad_lines="error", sep=None, engine="python")
    except Exception as e:
        print(f"[FATAL] - Failed to load {file_path.name}: {e}")
        quit()

    print(f"Successfully loaded dataframe: {file_path.name} {df.shape}")
    df.columns = [clean_column_name(c) for c in df.columns]

    # ---------------------------
    # FILTER BAD / HEADER ROWS
    # ---------------------------
    before = df.copy()
    df = df[df.apply(is_real_match_row, axis=1)].copy()  # keep only real match rows
    after = df.copy()
    removed_rows = before.loc[~before.index.isin(after.index)]
    print(f"[INFO] - Removed {len(removed_rows)} non-match rows")
    print("[INFO] - Removed rows:")
    print(removed_rows)
    print(f"[INFO] - Remaining match rows: {len(after)}")
    for _, r in removed_rows.iterrows():
        print(r)


    # ---------------------------
    # BUILD PLAYER TABLE
    # ---------------------------
    player_rows = []
    for _, row in df.iterrows():
        gender = get_gender_from_match_id(row["match_id"])
        for side in [1, 2]:
            display_name = str(row[f"player_{side}"]).strip()
            canonical_name = normalize_name(display_name)
            if not canonical_name:
                print("[FATAL] - Failed to canonicalize name:", display_name)
                quit()
            player_rows.append({"display_name": display_name, "canonical_name": canonical_name, "handedness": row.get(f"pl_{side}_hand"), "date": row.get("date"), "gender": gender})

    players_df = pd.DataFrame(player_rows)

    players = (players_df.groupby("canonical_name", as_index=False).agg(display_name=("display_name", "first"), handedness=("handedness", "first"), gender=("gender", "first"), first_seen=("date", "min"), last_seen=("date", "max")))

    players["player_id"] = players["canonical_name"].apply(generate_player_id)

    players = players[
        ["player_id", "canonical_name", "display_name",
         "handedness", "gender", "first_seen", "last_seen"]
    ]

    # ---------------------------
    # BUILD ID LOOKUP
    # ---------------------------
    id_lookup = dict(zip(players["canonical_name"], players["player_id"]))

    def map_player(name):
        return id_lookup.get(normalize_name(name))

    # ---------------------------
    # REWRITE MATCHES
    # ---------------------------
    df["player1_id"] = df["player_1"].apply(map_player)
    df["player2_id"] = df["player_2"].apply(map_player)

    df_clean = df.drop(
        columns=["player_1", "player_2", "pl_1_hand", "pl_2_hand"],
        errors="ignore"
    )

    # Reorder columns
    front_cols = ["match_id", "player1_id", "player2_id"]
    remaining = [c for c in df_clean.columns if c not in front_cols]
    df_clean = df_clean[front_cols + remaining]

    # ---------------------------
    # SAVE OUTPUTS
    # ---------------------------
    output_directory = Path(output_directory)
    (output_directory / "players").mkdir(parents=True, exist_ok=True)
    (output_directory / "matches").mkdir(parents=True, exist_ok=True)

    players_output_path = output_directory / "players" / "players.csv"
    matches_output_path = output_directory / "matches" / "matches.csv"

    players.to_csv(players_output_path, index=False)
    df_clean.to_csv(matches_output_path, index=False)

    # ---------------------------
    # SUMMARY
    # ---------------------------
    print("\n----------- SUMMARY -------------")
    print("Status: SUCCESS")
    print("Total players:", len(players))
    print("Total matches:", len(df_clean))
    print("Players written to:", players_output_path)
    print("Matches written to:", matches_output_path)


def clean_tennis_points(data_directory, output_directory):
    data_directory = Path(data_directory)
    if not data_directory.exists():
        print(f"[ERROR] - Directory does not exist: {data_directory}")
        return

    rename_map = {"gm#": "game_num", "1st": "first_srv", "2nd": "second_srv", "svr": "server", "tbset": "tb_set"}
    enforced_data_type = {"TbSet": "boolean"}
    total_points = 0
    for file_path in data_directory.rglob("*.csv"):
        if not file_path.is_file():
            print(f"[FATAL] - File path is not a file: {data_directory}")
            quit()
        try:
            df = pd.read_csv(file_path, encoding=get_file_encoding_type(file_path), on_bad_lines="error", dtype=enforced_data_type)
        except Exception as e:
            print(f"[FATAL] - Failed to load {file_path.name}: {e}")
            quit()
        shape = df.shape
        print(f"Successfully loaded dataframe: {file_path.name} ({shape[0]}x{shape[1]})")
        df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
        df.rename(columns=rename_map, inplace=True)
        print(df.head())
        print(f"Column Names: {df.columns.to_list()}")
        total_points += shape[0]

        print(f"\n\n----------- SAVING -------------")
        output_path = output_directory / "points" / file_path.name
        df.to_csv(output_path, index=False)
        print(f"Points ({file_path.name}) written to: {output_path}")

    print(f"Total Number of Points: {total_points}") # 1,755,187 Point Records 01/29/2026


if __name__ == "__main__":
    root = find_repo_root()
    data_directory = root / "data" / "raw"
    output_data_directory = root / "data" / "canonical"
    matches_file = data_directory / "matches" / "matches.csv"
    points_directory = data_directory / "points"

    print(f"[INFO] - Repository Root: {root}")
    print(f"[INFO] - Data Directory: {data_directory}")
    clean_tennis_matches(matches_file, output_data_directory)
    # clean_tennis_points(points_directory, output_data_directory)