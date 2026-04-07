import os
import re
import pathlib
import json
import gzip
from bs4 import BeautifulSoup

PLAYER_ATTRIBUTES = ["nameparam", "fullname", "lastname", "country", "dob", "dob_approx", "death_date", "hand", "backhand",
                     "ht", "lastdate", "atp_id", "wta_id", "itf_id", "fc_id", "dc_id", "twitter", "wiki_id", "elo_rank", "elo_rating"] 

MATCH_BASE_ATTRIBUTES = ["date","tourn","surf","level","wl","rank","seed","entry","round", "score","max","opp","orank","oseed","oentry","ohand","obday", "oht","ocountry","oactive", "time"]
MATCH_ATTRIBUTES = ['date', 'tourn', 'surf', 'level', 'wl', 'rank', 'seed', 'entry', 'round', 'score', 'max', 'opp', 'orank', 'oseed', 'oentry', 'ohand', 
'obday', 'oht', 'ocountry', 'oactive', 'time', 'aces', 'dfs', 'pts', 'firsts', 'fwon', 'swon', 'games', 'saved', 'chances', 'oaces',
'odfs', 'opts', 'ofirsts', 'ofwon', 'oswon', 'ogames', 'osaved', 'ochances', 'obackhand', 'chartlink', 'pslink', 'whserver', 'matchid', 'wh', 'roundnum', 'matchnum']

data_directory = pathlib.Path(__file__).resolve().parent.parent.parent / "data" / "raw" / "tennisabstract" / "players"

def parse_html_js_value(var_name, html):
    match = re.search(
        rf"var\s+{var_name}\s*=\s*(.*?);",
        html,
        re.DOTALL
    )
    
    if not match:
        return None

    value = match.group(1).strip()

    # -----------------------
    # STRING
    # -----------------------
    if value.startswith(("'", '"')):
        return value.strip('"\'')
    
    # -----------------------
    # NULL
    # -----------------------
    if value == "null":
        return None

    # -----------------------
    # NUMBER (int / float)
    # -----------------------
    try:
        if "." in value:
            return float(value)
        return int(value)
    except ValueError:
        pass

    # -----------------------
    # FALLBACK (raw string)
    # -----------------------
    return value

def parse_js_vars(text, var_names):
    data = {}

    for var_name in var_names:

        # Match ANY JS var assignment robustly
        match = re.search(
            rf'var\s+{var_name}\s*=\s*(.*?);',
            text,
            re.DOTALL
        )

        if not match:
            data[var_name] = None
            continue

        value = match.group(1).strip()

        try:
            # -----------------------
            # STRING (possibly JSON)
            # -----------------------
            if value.startswith(("'", '"')):
                value = value.strip('"\'')
                
                # Try parsing JSON inside string
                if value.startswith("["):
                    try:
                        data[var_name] = json.loads(value)
                    except:
                        data[var_name] = ast.literal_eval(value)
                else:
                    data[var_name] = value

            # -----------------------
            # ARRAY
            # -----------------------
            elif value.startswith("["):
                try:
                    data[var_name] = json.loads(value.replace("'", '"'))
                except:
                    data[var_name] = ast.literal_eval(value)

            # -----------------------
            # NULL / EMPTY
            # -----------------------
            elif value in ("null", ""):
                data[var_name] = None

            # -----------------------
            # NUMBER
            # -----------------------
            else:
                try:
                    data[var_name] = int(value)
                except:
                    data[var_name] = float(value)

        except Exception:
            data[var_name] = None

    return data

def parse_html_js_array(var_name, html):
    match = re.search(rf"var {var_name}\s*=\s*(\[[\s\S]*?\]);", html)
    if not match:
        return None
    return json.loads(match.group(1))

all_players = []
bad_players = []
with os.scandir(data_directory) as it:
    for entry in it:
        if entry.is_dir():
            subdir_path = pathlib.Path(entry.path)  # convert to Path
            player = {"url_parameter_name": entry.name}
            for file in subdir_path.iterdir():
                if file.is_file() and file.name == "html-profile.html":
                    with file.open("r", encoding="utf-8") as f:
                        text = f.read()
                    if "// test" in text or parse_html_js_value('fullname', text) == None:
                        continue
                    player["html"] = parse_js_vars(text, PLAYER_ATTRIBUTES) # update_player(player, player_data, replace=True)
                    player["html"]["html_matches"] = parse_html_js_array("matchmx", text)
                elif file.is_file() and "profile.gz" in file.name:
                    with gzip.open(file, "rt", encoding="utf-8") as f:
                        data = f.read()
                    if file.name == "js-profile.gz":
                        player["js"] = parse_js_vars(data, PLAYER_ATTRIBUTES)
                        player["js"]["matches"] = parse_html_js_array('matchmx', data)
                    elif file.name == "js-career-profile.gz":
                        player["jscareer"] = {"matches": parse_html_js_array("morematchmx", data)}
            
            if "js" in player and "matches" in player["js"] and player["js"]["matches"] is not None \
            and "jscareer" in player and "matches" in player["jscareer"] and player["jscareer"]["matches"] is not None:
                js_matches = player["js"]["matches"] + player["jscareer"]["matches"]
                player['js']['matches'] = js_matches
                del player["jscareer"]

            if "html" in player and "js" not in player:
                data = player['html'] 
                data["url_parameter_name"] = player.get("url_parameter_name")
                data["matches"] = player["html"]["html_matches"]
                del data["html_matches"]
                all_players.append(data)
            elif "html" not in player and "js" in player:
                data = player['js']
                data["url_parameter_name"] = player.get("url_parameter_name")
                all_players.append(data)
            elif "html" in player and "js" in player:
                for k, v in player["js"].items():
                    if v not in (None, "", [], {}) and k in player['html'] and player['html'][k] in (None, [], "", {}):
                        player['html'][k] = v
                    else:
                        continue
                data = {k: v for k, v in player["html"].items() if k not in ["html_matches"]}
                data["matches"] = player['html']["html_matches"]
                data["url_parameter_name"] = player.get("url_parameter_name")
                all_players.append(data)
            else:
                bad_players.append(player)

print(f"Bad Players ({len(bad_players)}): {[i for i in bad_players]}")

def load_urls(fp):
    """
    Reads a file with player URLs and returns a dictionary
    mapping player identifier to gender ("M" or "F").
    """
    urls = {}
    with open(fp, "r", encoding="utf-8") as f:
        for url in f:
            url = url.strip()
            if url:
                # Extract player id from URL
                player_id = url.split("?p=")[1].strip()
                # Assign gender based on URL pattern
                gender = "M" if "wplayer-classic" not in url.lower() else "F"
                urls[player_id] = gender
    return urls

gender_map_urls = load_urls("/home/mcilek/Github/maximcilek/lewis-university-research/data/raw/tennisabstract/players/charting_players_urls.txt")
base_dir = pathlib.Path("/home/mcilek/Github/maximcilek/lewis-university-research/data/canonical/tennisabstract")
output_file = base_dir / "players.jsonl"
# Ensure parent directory exists
output_file.parent.mkdir(parents=True, exist_ok=True)
with output_file.open("w", encoding="utf-8") as f:
    for p in all_players:
        mapped_matches = [dict(zip(MATCH_BASE_ATTRIBUTES, m)) for m in p.get("matches", [])]
        p["matches"] = mapped_matches
        p["gender"] = gender_map_urls[p.get("url_parameter_name")]

        # Write one JSON object per line
        f.write(json.dumps(p, ensure_ascii=False) + "\n")
    
    for p in bad_players:
        p["gender"] = gender_map_urls[p.get("url_parameter_name")]
        f.write(json.dumps(p, ensure_ascii=False) + "\n")

print(f"Saved {len(all_players)} players to {output_file.resolve()}")














"""
  if len(m) == 25 or len(m) == 27 or len(m) == 28 or len(m) == 30:
      mapped_match["matchid"] = m[-1]
      print(m)
      quit()
  elif len(m) == 39:
      print(f"No Match ID: {m}")
  elif len(m) == 42 or len(m) == 44 or len(m) == 45:
      mapped_match["matchid"] = m[-1]
  elif len(m) == 47:
      mapped_match["matchid"] = m[-4]
      mapped_match["charting_url"] = m[-7]
  elif len(m) == 48:
      mapped_match["matchid"] = m[-5]
      mapped_match["charting_url"] = m[-8]

  if len(m) == 42:
      mapped_match["charting_url"] = m[-2]
  elif len(m) == 44:
      mapped_match["charting_url"] = m[-4]
MATCH_ATTRIBUTES = ["date","tourn","surf","level","wl","rank","seed","entry","round", "score","max","opp","orank","oseed","oentry","ohand","obday",
                    "oht","ocountry","oactive","time","aces","dfs","pts","firsts","fwon", "swon",'games',"saved","chances","oaces","odfs","opts","ofirsts",
                    "ofwon","oswon",'ogames',"osaved","ochances","obackhand","chartlink", "pslink","whserver","matchid"]

DOUBLES_MATCH_ATTRIBUTES = ["date","tourn","surf","level","wl","rank","seed","entry","round",
                 "score","max","partner", "partnerlast", "prank", "phand", "pbday", "pht", "pcountry", "pactive",
              "oseed", "oentry", "opp","olast","orank","ohand","obday","oht","ocountry","oactive",
              "opp2","o2last","o2rank","o2hand","o2bday","o2ht","o2country","o2active",
              "time","aces","dfs","pts","firsts","fwon",
                 "swon",'games',"saved","chances","oaces","odfs","opts","ofirsts",
                 "ofwon","oswon",'ogames',"osaved","ochances", "obackhand", "chartlink",
                 "pslink","whserver","matchid","wh","roundnum","matchnum"]

# 25
["date","tourn","surf","level","wl","rank","seed","entry","round", "score","max","opp","orank","oseed","oentry","ohand","obday", "oht","ocountry","oactive"]
['20050926', 'Pelham AL 25K', 'Clay', '25', 'W', '', '', 'WC', 'R32', '6-2 6-4', '3', 'Raquel Kops Jones', '437', '', '', 'U', '22.8008213552', '', 'USA', '0', '', '', '', '', '2005-W-C25-USA-08A-2005-014']
['20080908', 'Rousse 25K', 'Clay', '25', 'W', '176', '1', '', 'R32', '6-2 3-6 6-4', '3', 'Paula Fondevila Castro', '450', '', 'Q', 'U', '24.3148528405', '', 'ESP', '0', '', '', '', '', '2008-W-C25-BUL-01A-2008-001']

# 27/28
["date","tourn","surf","level","wl","rank","seed","entry","round", "score","max","opp","orank","oseed","oentry","ohand","obday", "oht","ocountry","oactive", '', '', '', 'chartlink', 'pslink', 'whserver', 'matchid']
['20250410', 'BJK Cup Qualifiers', '', 'D', 'L', '93', '', '', 'RR', '6-4 6-3', '3', 'Magda Linette', '30', '', '', 'R', '19920212', '171', 'POL', '0', '', '', '', '20250410-W-BJK_Cup_Qualifiers-RR-Magda_Linette-Viktorija_Golubic', '', '', '2025-W-FC-2025-QUA-108']
['20240624', 'W50 Palma del Rio', 'Hard', '50', 'L', '', '', '', 'Q1', '6-3 6-4', '3', 'Radka Zelnickova', '539', '5', '', 'R', '20030613', '', 'SVK', '0', '', '', '', '20240623-W-W50_Palma_Del_Rio-Q1-Radka_Zelnickova-Alice_Ferlito', '', '', '2024-W-ITF-ESP-2024-026-719']

# 44
['20160321', 'Miami', 'Hard', 'P', 'L', '775', '', 'WC', 'R128', '6-1 6-2', '3', 'Shuai Zhang', '68', '', '', 'R', '19890121', '177', 'CHN', '0', '59', '3', '4', '55', '35', '17', '10', '8', '3', '8', '1', '2', '47', '28', '20', '13', '7', '4', '4', '', '', '', '', '2016-M007-228']


MATCH_ATTRIBUTES = ['date', 'tourn', 'surf', 'level', 'wl', 'rank', 'seed', 'entry', 'round', 'score', 'max', 'opp', 'orank', 'oseed', 'oentry', 'ohand', 
'obday', 'oht', 'ocountry', 'oactive', 'time', 'aces', 'dfs', 'pts', 'firsts', 'fwon', 'swon', 'games', 'saved', 'chances', 'oaces',
'odfs', 'opts', 'ofirsts', 'ofwon', 'oswon', 'ogames', 'osaved', 'ochances', 'obackhand', 'chartlink', 'pslink', 'whserver', 'matchid']
['20241227', 'United Cup', 'Hard', 'I', 'L', '32', '', '', 'RR', '6-4 6-3', '3', 'Elena Rybakina', '6', '', '', 'R', '19990617', '184', 'KAZ', '0', '83', 

['aces', 'dfs', 'pts', 'firsts', 'fwon', 'swon', 'games', 'saved', 'chances', 'oaces', 'odfs', 'opts', 'ofirsts', 'ofwon', 'oswon', 'ogames', 'osaved', 'ochances', 'obackhand', 'chartlink', 'pslink', 'whserver', 'matchid']
['2', '6', '58', '33', '21', '11', '9', '5', '8', '7', '1', '63', '40', '29', '13', '10', '3', '4', '', '', '', '', '2025-9900-289']
"""