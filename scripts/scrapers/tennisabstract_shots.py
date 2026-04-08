

import csv
import json, re

input_csv = "/home/mcilek/Github/maximcilek/lewis-university-research/data/canonical/tennisabstract/charting_points.csv"
output_json = "/home/mcilek/Github/maximcilek/lewis-university-research/data/canonical/tennisabstract/charting_shots.jsonl"
codes_dict = {
    "set_tiebreak_codes": [
        { "code": "0", "description": "Advantage Set" },
        { "code": "S", "description": "10-point Super-Tiebreak" },
        { "code": "W", "description": "8-all Tiebreak" },
        { "code": "V", "description": "No Tiebreakers" },
        { "code": "A", "description": "6-all 10-point Super-Tiebreak" },
        { "code": "T", "description": "12-all Tiebreak" },
        { "code": "N", "description": "NextGen Finals Format" }
    ],
    "point_penalty_codes": [
        { "code": "P", "description": "server" },
        { "code": "Q", "description": "returner" }
    ],
    "point_winner_codes": [
        { "code": "S", "description": "server" },
        { "code": "R", "description": "returner" }
    ],
    "point_miscellaneous_codes": [
        { "code": "C", "description": "failed_challenge" }
    ],
    "serve_direction": [
        { "code": "4", "description": "wide" },
        { "code": "5", "description": "body" },
        { "code": "6", "description": "T" },
        { "code": "0", "description": "unknown" }
    ],
    "serve_fault_type_codes": [
        { "code": "n", "description": "net" },
        { "code": "w", "description": "wide" },
        { "code": "d", "description": "deep" },
        { "code": "x", "description": "wide_and_deep" },
        { "code": "g", "description": "foot_faults" },
        { "code": "e", "description": "unknown" },
        { "code": "!", "description": "shank" },
        { "code": "V", "description": "time_violation" },
        { "code": "c", "description": "let" },
        { "code": "+", "description": "serve_and_volley_attempt" }
    ],
    "serve_outcomes": [
        { "code": "*", "description": "ace", "return_attempt": False },
        { "code": "#", "description": "unreturnable", "return_attempt": False },
        { "code": "#", "description": "forced_return_error", "return_attempt": True },
        { "code": "@", "description": "unforced_return_error", "return_attempt": True }
    ],
    "serve_return_depths": [
        { "code": "7", "description": "service_box" },
        { "code": "8", "description": "midcourt" },
        { "code": "9", "description": "deep" },
        { "code": "0", "description": "unknown" }
    ],
    "rally_shot_type_codes": [
        { "code": "f", "description": "forehand" },
        { "code": "b", "description": "backhand" },
        { "code": "r", "description": "forehand_slice" },
        { "code": "s", "description": "backhand_slice" },
        { "code": "v", "description": "forehand_volley" },
        { "code": "z", "description": "backhand_volley" },
        { "code": "o", "description": "overhead" },
        { "code": "p", "description": "backhand_overhead" },
        { "code": "u", "description": "forehand_drop" },
        { "code": "y", "description": "backhand_drop" },
        { "code": "l", "description": "forehand_lob" },
        { "code": "m", "description": "backhand_lob" },
        { "code": "h", "description": "forehand_half_volley" },
        { "code": "i", "description": "backhand_half_volley" },
        { "code": "j", "description": "forehand_swing_volley" },
        { "code": "k", "description": "backhand_swing_volley" },
        { "code": "t", "description": "trick_shot" },
        { "code": "q", "description": "unknown" }
    ],
    "rally_shot_direction_codes": [
        { "code": "1", "description": "to_forehand_side" },
        { "code": "2", "description": "middle" },
        { "code": "3", "description": "to_backhand_side" },
        { "code": "0", "description": "unknown" }
    ],
    "rally_end_winner_codes": [
        { "code": "*", "description": "winner" }
    ],
    "rally_end_error_codes": [
        { "code": "n", "description": "net" },
        { "code": "w", "description": "wide" },
        { "code": "d", "description": "deep" },
        { "code": "x", "description": "wide_and_deep" },
        { "code": "!", "description": "shank" },
        { "code": "e", "description": "unknown" }
    ],
    "court_position_codes": [
        { "code": "+", "description": "approach_shot" },
        { "code": "-", "description": "net" },
        { "code": "=", "description": "baseline" },
        { "code": ";", "description": "net_cord" },
        { "code": "^", "description": "drop_shot" }
    ]
}
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


countShots = 0
count = 0
with open(input_csv, mode='r', newline='', encoding='utf-8') as csv_file, \
    open(output_json, "w", encoding="utf-8") as outfile:
    reader = csv.DictReader(csv_file)
    for row in reader:
        if (count % 1000) == 0:
            print(f"{(count / 1755188)*100}%")
        results = []
        if ("first_serve_rally" in row and row["first_serve_rally"] not in [None, {}, [], ""]):
            shots = split_rally_pattern(row["first_serve_rally"])
            for s in shots:
                s["serve_num"] = 1
            if shots is not None:
                results.extend(shots)     
            results.extend(shots)
        if ("second_serve_rally" in row and row["second_serve_rally"] not in [None, {}, [], ""]):
            shots = split_rally_pattern(row["second_serve_rally"])
            for s in shots:
                s["serve_num"] = 2
            if shots is not None:
                results.extend(shots)
        """
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
        """
        row["double_fault"] = is_double_fault(results)
        row["shots"] = results
        row["game_score_1"], row["game_score_2"] = row["game_score"].split("-")
        del row["game_score"]
        outfile.write(json.dumps(row) + "\n")
        countShots += len(results)
        count += 1
# Now `data` is a list of dicts (JSON-like)
print(f"Loaded {countShots} rows.")

# 5b28b28b39b28b18f29b39b38b38s37f-39*
# 4b39b29f28b28f18f29f28b38b38b38s39f38m2d#
# 5f29f38b28f28f39b29b37b18f19f38s38f39w@