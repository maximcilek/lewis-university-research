

import csv
import json
import re
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data/canonical/tennisabstract"
METADATA_DIR = DATA_DIR / "_meta"

rally_pattern_codes


def load_json_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)

def parse_serve_rallies(row):
    first = row.get("first_serve_rally")
    second = row.get("second_serve_rally")
    result = {"first_serve": None, "second_serve": None, "rally": [], "ending": None, "winner": None}

    # --- Handle special cases ---
    check_list = [c for c in first if c in [i.get("code") for i in codes_dict["point_codes"]]]
    #print([i["code"] for i in codes_dict["point_codes"]])
    #quit()
    if check_list != []:
        print(check_list, first, len(first))
        quit()
    #if any(check_list):
    #    # result["winner"] = interpret_special(first)
    #    print(first)
    #    quit()
        # return result

if __name__ == "__main__":
    input_csv = DATA_DIR / "charting_points.csv"
    output_json = DATA_DIR / "charting_shots.jsonl"


    countShots = 0
    count = 0
    with open(input_csv, mode='r', newline='', encoding='utf-8') as csv_file, \
         open(output_json, "w", encoding="utf-8") as outfile:
        
        reader = csv.DictReader(csv_file)
        for row in reader:
            if (count % 1000) == 0:
                print(f"{(count / 1755188)*100}%")
            results = []
            
            parse_serve_rallies(row)
            count += 1
            
    # Now `data` is a list of dicts (JSON-like)
    print(f"Loaded {countShots} rows.")

# 5b28b28b39b28b18f29b39b38b38s37f-39*
# 4b39b29f28b28f18f29f28b38b38b38s39f38m2d#
# 5f29f38b28f28f39b29b37b18f19f38s38f39w@

"""
def split_rally_pattern(text):

    # Build a code-to-description map
    code_to_desc = {}
    for category in codes_dict.values():
        for entry in category:
            code_to_desc[entry['code']] = entry['description']

    # ---- SPLIT USING FOR LOOP ----
    groups = []
    grp = ""
    for i, ch in enumerate(text):
        grp += ch
        # If next char exists and is alphabet, or last char, close group
        if i + 1 < len(text):
            if text[i+1].isalpha():
                groups.append(grp)
                grp = ""
        else:
            groups.append(grp)

    decoded = []
    player_turn = "server"
    for shotcount, g in enumerate(groups):
        details = []
        for c in g:
            desc = code_to_desc.get(c)
            details.append({"code": c, "description": desc})
        print(details)
        quit()
        decoded.append({"details": details, "shot_num": shotcount+1, "player_turn": player_turn})
        player_turn = 'returner' if player_turn == 'server' else 'server'
    
    return decoded

def is_double_fault(decoded):
    double_fault = False
    server_groups = [s for s in decoded if s["player_turn"] == "server"]
    first_serve_codes = []
    for sg in server_groups[:2]:  # first and second server groups
        first_serve_codes.extend([sh["code"] for sh in sg["details"]])
    if all(c in ["n", "w", "d", "x", "g", "e", "!", "V"] for c in first_serve_codes):
        double_fault = True
        return True
    return False
"""

"""
            # if ("first_serve_rally" in row and row["first_serve_rally"] not in [None, {}, [], ""]):
            #     shots = split_rally_pattern(row["first_serve_rally"])
            #     for s in shots:
            #         s["serve_num"] = 1
            #     if shots is not None:
            #         results.extend(shots)     
            #     results.extend(shots)
            # if ("second_serve_rally" in row and row["second_serve_rally"] not in [None, {}, [], ""]):
            #     shots = split_rally_pattern(row["second_serve_rally"])
            #     for s in shots:
            #         s["serve_num"] = 2
            #     if shots is not None:
            #         results.extend(shots)
            for s in results:
                s["match_id"] = row["match_id"]
                s["point_number"] = row["point_number"]
                s["set_1"] = row["set_1"]
                s["set_2"] = row["set_2"]
                s["game_1"] = row["game_1"]
                s["game_2"] = row["game_2"]
                s["game_score_1"], s["game_score_2"] = row["game_score"].split("-")
                s["game_number"] = row["game_number"]
                s["tiebreaker_set"] = row["tiebreaker_set"]
                s["server_player_number"] = row["server_player_number"]
                s["first_serve_rally"] = row["first_serve_rally"]
                s["second_serve_rally"] = row["second_serve_rally"]
                s["notes"] = row["notes"]
                s["point_winner_player_number"] = row["point_winner_player_number"]
                print(s)

                quit()
            
            row["double_fault"] = is_double_fault(results)
            row["shots"] = results
            row["game_score_1"], row["game_score_2"] = row["game_score"].split("-")
            del row["game_score"]
            outfile.write(json.dumps(row) + "\n")
            countShots += len(results)
            count += 1
"""