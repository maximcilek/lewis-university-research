from pathlib import Path
import pandas as pd
import re, csv, re

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

def is_partial_name(name):
    name = name.strip()

    # Matches:
    # G. Granollers
    # G Granollers
    # M.Torro-Flor
    # B Woolcock
    return bool(re.match(r'^[A-Z]\.?\s*\S+', name))

def clean_tennis_matches(matches_directory):
    # Columns
    # 16 - Singles: ['match_id', 'year', 'slam', 'match_num', 'player1', 'player2', 'status', 'winner', 'event_name', 'round', 'court_name', 'court_id', 'player1id', 'player2id', 'nation1', 'nation2']
    # 18 - Mixed/Doubles (e.g., 2021-usopen-matches-doubles.csv): [partner1, partner1]
    # 20 - Mixed/Doubles (e.g., 2021-ausopen-matches-doubles.csv): [nation_partner1, nation_partner1]
    
    matches_directory = Path(matches_directory)
    if not matches_directory.exists():
        print(f"[ERROR] - Directory does not exist: {matches_directory}")
        return
    
    # Loop through CSV files
    yearly_matches = {}
    players_list = []
    total_matches = 0
    year_pattern = re.compile(r"(\d{4})")
    pattern = re.compile(r'\.csv$', re.IGNORECASE)
    for file_path in matches_directory.rglob("*"):
        if not file_path.is_file():
            continue
        
        year_match = year_pattern.search(file_path.name)
        if not year_match:
            print(f"[FATAL] - Could not determine year for file {file_path.name}, skipping.")
            quit()
        year = int(year_match.group(1))

        if "mixed" in file_path.name.lower():
            match_type = "mixed"
        elif "doubles" in file_path.name.lower():
            match_type = "doubles"
        else:
            match_type = "singles"

        try:
            df = pd.read_csv(file_path, encoding=get_file_encoding_type(file_path), on_bad_lines="error")
        except Exception as e:
            print(f"[FATAL] - Failed to load {file_path.name}: {e}")
            quit()

        rows, cols = df.shape
        duplicates = df.duplicated().sum()
        print(f"[INFO] - Loaded {file_path.name} ({rows}x{cols})")
        if duplicates > 0:
            print(f"[ERROR] - {duplicates} duplicates found in {file_path.name}")
            quit()
        
        ### DataFrame Cleaning ###
        # if year not in yearly_matches:
        #     yearly_matches[year] = {"singles": None, "doubles": None, "mixed": None}
        # yearly_matches[year][match_type] = df

        for _, row in df.iterrows():
          match_id = row['match_id']
          total_matches += 1
          if match_type == "singles":
              for i in range(2):
                  players_list.append({
                      'match_id': match_id,
                      'player_name': row[f'player{i + 1}'],
                      'player_id': row[f'player{i+1}id'],
                      'nation': row[f'nation{i+1}'],
                      'position': i+1,
                      'partner_id': None,
                      'partner_name': None,
                      'partner_nation': None
                  })
          else:
              players_list.append({
                  'match_id': match_id,
                  'player_name': row['player1'],
                  'player_id': row['player1id'],
                  'partner_name': row.get('partner1'),
                  'nation': row['nation1'],
                  'partner_nation': row.get('nation_partner1'),
                  'position': 1
              })

              players_list.append({
                  'match_id': match_id,
                  'player_name': row.get('partner1'),
                  'partner_name': row['player1'],
                  'partner_id': row['player1id'],
                  'nation': row.get('nation_partner1'),
                  'partner_nation': row['nation1'],
                  'position': 2
              })

              players_list.append({
                  'match_id': match_id,
                  'player_id': row['player2id'],
                  'player_name': row['player2'],
                  'partner_name': row.get('partner2'),
                  'nation': row['nation2'],
                  'partner_nation': row.get('nation_partner2'),
                  'position': 3
              })

              players_list.append({
                  'match_id': match_id,
                  'player_name': row.get('partner2'),
                  'partner_name': row['player2'],
                  'partner_id': row['player2id'],
                  'nation': row.get('nation_partner2'),
                  'partner_nation': row['nation2'],
                  'position': 4
              })

    print(f"Found {total_matches} Matches")
    print(f"Found {len(players_list)} Players")
    playerFullNames = set()
    playerPartialNames = set()
    playerUniqueNames = set()
    count_nan_names = 0
    for p in players_list:
        name = p.get("player_name")

        if not isinstance(name, str):
            count_nan_names += 1
            continue

        name = name.strip()
        if not name:
            print(f"[FATAL] - Player Name is empty: {p}")
            quit()

        # Single token names go to unique
        if len(name.split()) < 2:
            playerUniqueNames.add(name)
            continue

        if is_partial_name(name):
            playerPartialNames.add(name)
        else:
            playerFullNames.add(name)

    print(f"Player List: {len(players_list)} Players ({count_nan_names} NaN)")
    print(f"Player Full Names: {len(playerFullNames)}")
    print(f"Player Partial Names: {len(playerPartialNames)}")
    print(f"Player Unique Names: {len(playerUniqueNames)}")

    print("\n-----------------------------------------------------------\n")
    playerArrs = {
        "playerFullName": playerFullNames,
        "playerPartialName": playerPartialNames,
        "playerUniqueName": playerUniqueNames
    }
    for k, v in playerArrs.items():
        for cn, n in enumerate(v):
            if cn >= 10:
                break
            print(f"{k}: {n}")    



if __name__ == "__main__":
    root = find_repo_root()
    data_directory = root / "data" / "raw"
    macthes_directory = data_directory / "matches"

    print(f"[INFO] - Repository Root: {root}")
    print(f"[INFO] - Data Directory: {data_directory}")
    clean_tennis_matches(macthes_directory)