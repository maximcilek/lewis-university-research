from datetime import datetime
import sys, pathlib, logging, typing, json
sys.path.append(str(pathlib.Path(__file__).resolve().parent.parent.parent))
import tennisabstractscraper.models.data_objects as data_objects
import tennisabstractscraper.models.tennisabstract_data as tennisabstract_data

# LOGGER
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
LOGGER = logging.getLogger(__name__)

# ENV VARIABLES
DATA_DIR = pathlib.Path(__file__).resolve().parent.parent.parent / "data"
PLAYERS_DIR = DATA_DIR / "raw/tennisabstract/players"

# Generic Type Placeholder
T = typing.TypeVar("T")

# GLOBAL VARIABLES
PLAYER_INDEX = None
PLAYER_ATTRIBUTES = None
MATCH_BASE_ATTRIBUTES = None
def build_dict(seq, key):
    return dict((d[key], dict(d, index=index)) for (index, d) in enumerate(seq))


def merge_raw_charting_matches():
    charted_matches_raw = data_objects.CsvDataObject(DATA_DIR / "raw/tennisabstract/tennis_MatchChartingProject-master/charting-m-matches.csv").data + data_objects.CsvDataObject(DATA_DIR / "raw/tennisabstract/tennis_MatchChartingProject-master/charting-w-matches.csv").data
    charted_matches = data_objects.JsonlDataObject(DATA_DIR / "raw/tennisabstract/scraper/charting_matches.jsonl").data
    
    charted_matches_by_id = build_dict(charted_matches, "match_id")
    charted_matches_raw_by_id = build_dict(charted_matches_raw, "match_id")
    all_match_ids = set(charted_matches_by_id) | set(charted_matches_raw_by_id)
    
    matches = []
    match_ids = []
    for match_id in all_match_ids:
        scraped = charted_matches_by_id.get(match_id)
        raw = charted_matches_raw_by_id.get(match_id)
        if scraped:
            if raw:
                scraped["player_1_hand"] = raw.get("Pl 1 hand")
                scraped["player_2_hand"] = raw.get("Pl 2 hand")
                scraped["start_time"] = raw.get("Time")
                scraped["court"] = raw.get("Court")
                scraped["umpire"] = raw.get("Umpire")
                scraped["best_of"] = raw.get("Best of")
                scraped["start_time"] = raw.get("Time")
                scraped["surface"] = raw.get("Surface")
                scraped["is_final_tiebreaker"] = raw.get("Final TB?")
                scraped["charted_by"] = raw.get("Charted by")
            matches.append(scraped)
        elif raw:
            match_id_parts = match_id.split("-")
            gender = match_id_parts[1].strip()
            player_1_id = match_id_parts[-1].replace("_", "")
            player_2_id = match_id_parts[-2].replace("_", "")

            if gender == "W":
                profile_base_url = f"https://www.tennisabstract.com/cgi-bin/wplayer-classic.cgi?p="
            else:
                profile_base_url = f"https://www.tennisabstract.com/cgi-bin/player-classic.cgi?p="
            # if match_id not in match_ids:
            matches.append({
                "match_id": match_id,
                "match_date": raw.get("Date"),
                "gender": gender,
                "tournament_name": raw.get("Tournament"),
                "round": raw.get("Round"),
                "match_score": None,
                "winner": None,
                "player_1_id": player_1_id,
                "player_2_id": player_2_id,
                "player_1_fullname": raw.get("Player 1").strip(),
                "player_2_fullname": raw.get("Player 2").strip(),
                "player_1_profile_url": f"{profile_base_url}{player_1_id}",
                "player_2_profile_url": f"{profile_base_url}{player_2_id}",
                "player_1_hand": raw.get("Pl 1 hand"),
                "player_2_hand": raw.get("Pl 2 hand"),
                "start_time": raw.get("Time"),
                "surface": raw.get("Surface"),
                "court": raw.get("Court"),
                "umpire": raw.get("Umpire"),
                "best_of": raw.get("Best of"),
                "is_final_tiebreaker": raw.get("Final TB?"),
                "charted_by": raw.get("Charted by")
            })
    LOGGER.info(f"Successfully found {len(matches)} charted matches ({len(charted_matches_by_id)} Charted, {len(charted_matches_raw_by_id)} Raw)")    
    with open(DATA_DIR / "dev/tennisabstract/charting_matches.jsonl", "w", encoding="utf-8") as f:
        for m in matches:
            f.write(json.dumps(m, ensure_ascii=False) + "\n")

def merge_player_matches_with_charting_matches():
    charting_matches = data_objects.JsonlDataObject(DATA_DIR / "analysis/charting_matches.jsonl").data
    charting_matches_by_id = build_dict(charting_matches, "match_id")
    all_players = data_objects.JsonlDataObject(DATA_DIR / "dev/tennisabstract/players_all.jsonl").data
    updated = []
    with open(DATA_DIR / "dev/tennisabstract/charting_matches.jsonl", "w", encoding="utf-8") as f:
        for player_json in all_players:
            if "matches" in player_json and len(player_json.get("matches", [])) > 0:
                for match_id, match_json in player_json.get("matches", {}).items():
                    if match_json.get("charting_id") not in [None, ""] and match_json.get("charting_id") not in updated:
                        charting_match = charting_matches_by_id.get(match_json.get('charting_id'))
                        if charting_match is None:
                            """if match_json.get('charting_id') not in updated:
                                match_json["match_id"] = match_json.get("charting_id")
                                for k in ['player_2_rank', 'player_2_hand', 'umpire', 'charting_id', 'player_2_entry', 'best_of', 'start_time', 'match_score', 'player_2_seed', 'winner', 'round', 'time', 'player_1_entry', 'player_1_seed', 'is_final_tiebreaker', 'surface', 'player_2_fullname', 'match_date', 'tournament_start_date', 'player_1_id', 'gender', 'match_id', 'player_2_profile_url', 'court', 'tournament_name', 'player_1_rank', 'player_1_fullname', 'player_1_profile_url', 'level', 'score', 'player_2_id', 'charted_by', 'player_1_hand']:
                                    if k not in match_json:
                                        match_json[k] = None
                                updated.append(match_json.get('charting_id'))
                                del match_json["charting_id"]
                                f.write(json.dumps(match_json, ensure_ascii=False) + "\n")"""
                            continue
                      
                        for k in ['player_2_rank', 'player_2_hand', 'umpire', 'charting_id', 'player_2_entry', 'best_of', 'start_time', 'match_score', 'player_2_seed', 'winner', 'round', 'time', 'player_1_entry', 'player_1_seed', 'is_final_tiebreaker', 'surface', 'player_2_fullname', 'match_date', 'tournament_start_date', 'player_1_id', 'gender', 'match_id', 'player_2_profile_url', 'court', 'tournament_name', 'player_1_rank', 'player_1_fullname', 'player_1_profile_url', 'level', 'score', 'player_2_id', 'charted_by', 'player_1_hand']:
                            if k not in charting_match:
                              
                              if k in match_json and match_json.get(k) not in [None, ""] and charting_match.get(k) in [None, ""]:
                                  charting_match[k] = match_json.get(k)
                              else:
                                  charting_match[k] = None
                        # del charting_match["index"]
                        del charting_match["charting_id"]
                        del charting_match["player_1_hand"]
                        del charting_match["player_2_hand"]
                        del charting_match["index"]
                        f.write(json.dumps(charting_match, ensure_ascii=False) + "\n")
                        updated.append(match_json.get("charting_id"))
    
    LOGGER.info("%d Matches and %d Players", len(charting_matches), len(all_players))

# charted_matches = merge_raw_charting_matches()
merge_player_matches_with_charting_matches()
