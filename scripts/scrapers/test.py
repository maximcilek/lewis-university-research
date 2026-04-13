import json
import logging
import pathlib
import sys
import re
sys.path.append(str(pathlib.Path(__file__).resolve().parent.parent.parent))

import tennisabstractscraper.models.data_objects as data_objects
import tennisabstractscraper.models.tennisabstract_data as tennisabstract_data

DATA_DIR = pathlib.Path(__file__).resolve().parent.parent.parent / "data" # /canonical/tennisabstract"
METADATA_DIR = DATA_DIR / "_meta"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
LOGGER = logging.getLogger(__name__)

def load_tennisabstract_player_urls(fp):
    players = {}
    with open(fp, "r", encoding="utf-8") as f:
        for url in f:
            url = url.strip()
            if not url:
                continue
            player_id = url.split("?p=")[1].strip()
            gender = "M" if "wplayer-classic" not in url.lower() else "F"
            players[player_id] = {"player_id": player_id, "gender": gender, "profile_url": url}
    return players

if __name__ == "__main__":
    LOGGER.info("Loading TennisAbstract Data")
    # players = data_objects.JsonlDataObject("/home/mcilek/Github/maximcilek/lewis-university-research/data/dev/tennisabstract/players_all.jsonl")
    # for p in players:
    #   print(p)
    #   quit()
    # quit()
    
    points1 = data_objects.CsvDataObjectStream("/home/mcilek/Github/maximcilek/lewis-university-research/data/raw/tennisabstract/tennis_MatchChartingProject-master/charting-m-points-2010s.csv")
    points2 = data_objects.CsvDataObjectStream("/home/mcilek/Github/maximcilek/lewis-university-research/data/raw/tennisabstract/tennis_MatchChartingProject-master/charting-m-points-2020s.csv")
    points3 = data_objects.CsvDataObjectStream("/home/mcilek/Github/maximcilek/lewis-university-research/data/raw/tennisabstract/tennis_MatchChartingProject-master/charting-m-points-to-2009.csv")
    points4 = data_objects.CsvDataObjectStream("/home/mcilek/Github/maximcilek/lewis-university-research/data/raw/tennisabstract/tennis_MatchChartingProject-master/charting-w-points-2010s.csv")
    points5 = data_objects.CsvDataObjectStream("/home/mcilek/Github/maximcilek/lewis-university-research/data/raw/tennisabstract/tennis_MatchChartingProject-master/charting-w-points-2020s.csv")
    points6 = data_objects.CsvDataObjectStream("/home/mcilek/Github/maximcilek/lewis-university-research/data/raw/tennisabstract/tennis_MatchChartingProject-master/charting-w-points-to-2009.csv")
    # print(players.data[0])
    points = 0
    cids = []
    for f in [points1, points2, points3, points4, points5, points6]:
        for points_batch in f:
          for p in points_batch:
            points += 1
            # print(p)
            if p.get("match_id") not in cids:
                cids.append(p.get("match_id"))
              # quit()
            #if p["TbSet"] and p["match_id"] == "20191124-M-Davis_Cup_Finals-F-Rafael_Nadal-Denis_Shapovalov":
            #    print(p)
            #if p["TbSet"] and int(p["Gm1"]) == 6:
            #  print(f"Tied Games: {p}")
            #  quit()
    print(len(cids))
    quit()

    charted_matches = data_objects.JsonlDataObject(DATA_DIR / "dev/tennisabstract/charting_matches.jsonl").data
    PLAYERS_DATA = load_tennisabstract_player_urls(DATA_DIR / "raw/tennisabstract/scraper/charting_players_urls.txt")

    players = []
    missing = []
    for m in charted_matches:
      if m["player_1_id"] not in players:
        players.append(m["player_1_id"])

      if m["player_2_id"] not in players:
        players.append(m["player_2_id"])

      if m["player_1_id"] not in PLAYERS_DATA:
        missing.append(m["player_1_id"])
        print(f"Player 1 ID not in PLAYERS: {m}")
      if m["player_2_id"] not in PLAYERS_DATA:
        missing.append(m["player_2_id"])
        print(f"Player 2 ID not in PLAYERS: {m}")

    print(f"Unique Players: {len(players)}")
    print(f"Missing ({len(missing)}): {missing}")
    #for p in PLAYERS_DATA:
    #  if p["player_id"] not in 
    """
    with open(DATA_DIR / "raw/tennisabstract/scraper/charted_matches/charting_matches.jsonl", "w") as f:
      for m in charted_matches:
        new_match = {
          "match_id": m["match_id"],
          "match_date": m["match_date"],
          "gender": m["gender"],
          "tournament_name": m["tournament_name"],
          "round": m["round"],
          "match_score": m["match_score"],
          "winner": "1" if m["player_1"]["won"] else ("2" if m["player_2"]["won"] else None),
          "player_1_id": m["player_1"].get("profile_url").split("?p=")[1].strip(),
          "player_2_id": m["player_2"].get("profile_url").split("?p=")[1].strip(),
          "player_1_fullname": m["player_1"].get("display_name"),
          "player_2_fullname": m["player_2"].get("display_name"),
          "player_1_profile_url": m["player_1"].get("profile_url"),
          "player_2_profile_url": m["player_2"].get("profile_url")
        }
        if any(v is None or (isinstance(v, str) and v.strip() == "") for v in new_match.values()):
            LOGGER.fatal("Missing Value, require non-empty values: %s", v)
            continue
        f.write(json.dumps(new_match) + "\n")
      """

    print(f"Finished Editing All Matches")

        # f.write(json.dumps(new_match) + "\n")


      # canonical_match_score = re.sub(r"\s+", " ", re.sub(r"\([^)]*\)", "", m["match_score"])).strip().replace("-", "_").replace(" ", ".") if m["match_score"] else "noscore"
      # guid = f"{m['match_date']}-{m['tournament_name']}-{m['round']}-{new_match['player_1_fullname']}-{new_match['player_2_fullname']}-{canonical_match_score}".replace(" ", "_")
      # guid2 = f"{m['match_date']}-{new_match['gender']}-{m['tournament_name']}-{m['round']}-{new_match['player_1_fullname']}-{new_match['player_2_fullname']}".replace(" ", "_")
      # print(guid)
      # print(guid2 == new_match["match_id"])
      # quit()

      #m["player_1_id"] = m["player_1"].get("profile_url").split("?p=")[1].strip()
      #print(charted_matches[0])
    

"""
    charting_points_file_path = DATA_DIR / "charting_points.csv"
    rally_codes_file_path = METADATA_DIR / "rally_codes.json"
    # charting_points_file_path = DATA_DIR / "players.parquet"

    tennisabstract_points = tennisabstract_data.TennisAbstractPointsData(str(charting_points_file_path), str(rally_codes_file_path))
    tennisabstract_points.load_points()
    # print(type(tennisabstract_points.data))    


for batch_num, batch in enumerate(tennisabstract_points, 1):
    # col1 = batch.column('fullname')
    LOGGER.info("Batch #%s (%.2f MB) - %s rows %s columns", batch_num, batch.nbytes / (1024 * 1024), batch.num_rows, batch.num_columns)
    LOGGER.debug("Column(s): %s", json.dumps({col_name: str(batch.schema.types[i]) for i, col_name in enumerate(batch.column_names)}))
    LOGGER.debug("Schema Metadata: %s", batch.schema.metadata)
    results = [row for row in batch.to_pylist()]
"""