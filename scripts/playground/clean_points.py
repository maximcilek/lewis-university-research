import pathlib
import sys
import json
import logging
sys.path.append(str(pathlib.Path(__file__).resolve().parent.parent.parent))
import tennisabstractscraper.models.data_objects as data_objects

DATA_DIR = pathlib.Path(__file__).resolve().parent.parent.parent / "data"
METADATA_DIR = DATA_DIR / "canonical/tennisabstract/_meta"

def build_dict(seq, key):
    return {d[key]: dict(d, index=i) for i, d in enumerate(seq)}


if __name__ == "__main__":
    charting_points = data_objects.DataObjectFactory.create(DATA_DIR / "prod/charting_points.jsonl")
    PLAYERS = data_objects.JsonlDataObject(DATA_DIR / "prod/players.jsonl").data
    PLAYERS_BY_ID = build_dict(PLAYERS, "player_id")

    CHARTING_MATCHES = data_objects.JsonlDataObject(DATA_DIR / "prod/charting_matches.jsonl").data
    CHARTING_MATCHES_BY_ID = build_dict(CHARTING_MATCHES, "match_id")
    
    
    points_by_match = {}
    double_faults = {}
    df = 0
    up = []
    c = 0
    dupes = 0
    for _, points_batch in enumerate(charting_points):
        for p in points_batch:
            match_id = p.get("match_id")
            charting_match = CHARTING_MATCHES_BY_ID.get(match_id)
            if not charting_match:
                print(f"[FATAL] - Skipping, no charting match found: {match_id}")
                continue
            
            server_player_number = p.get("server_player_number")
            returner_player_number = 1 if server_player_number == 2 else 2
            result = {
                "match_id": match_id,
                "match_date": charting_match.get("match_date"),
                "surface": charting_match.get("surface"),
                "match_duration": charting_match.get("match_duration"),
                "level": charting_match.get("level"),
                "server_player_id": charting_match.get(p.get(f"player_{server_player_number}_id")),
                "returner_player_id": charting_match.get(p.get(f"player_{returner_player_number}_id")),
                "server_player_seed": charting_match.get(p.get(f"player_{server_player_number}_seed")),
                "server_player_entry": charting_match.get(p.get(f"player_{server_player_number}_entry")),
                "server_player_rank": charting_match.get(p.get(f"player_{server_player_number}_rank")),
                "returner_player_seed": charting_match.get(p.get(f"player_{returner_player_number}_seed")),
                "returner_player_entry": charting_match.get(p.get(f"player_{returner_player_number}_entry")),
                "returner_player_rank": charting_match.get(p.get(f"player_{returner_player_number}_rank")),
                "point_number": p.get("point_number"),
                "server_sets": p.get(f"set_{server_player_number}"),
                "returner_sets": p.get(f"set_{returner_player_number}"),
                "server_games": p.get(f"game_{server_player_number}"),
                "returner_games": p.get(f"game_{returner_player_number}"),
                "game_score": p.get("game_score"),
                "game_number": p.get("game_number"),
                "is_tiebreaker_set": p.get("is_tiebreaker_set"),
                "tb_point_number": p.get("tb_point_number"),
                "tb_point": p.get("tb_point_number"),
                "first_serve_rally": p.get("first_serve_rally"),
                "second_serve_rally": p.get("second_serve_rally"),
                "point_winner": p.get("point_winner"),
                "is_server_winner": p.get("is_server_winner"), # DEPRACATED
                "first_serve_in_play": p.get("first_serve_in_play"),
                "second_serve_in_play": p.get("second_serve_in_play"),
                "rally": p.get("rally"),
                "is_ace": p.get("is_ace"),
                "is_unret": p.get("is_unret"),
                "is_rally_winner": p.get("is_rally_winner"),
                "is_forced__error": p.get("is_forced__error"),
                "is_unforced__error": p.get("is_unforced__error"),
                "is_double": p.get("is_double"),
                "rally_length": p.get("rally_length"),
                "gender": p.get("gender")
            }
            print(json.dumps(result, indent=4))
            quit()