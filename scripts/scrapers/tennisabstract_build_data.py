import os
import re
import pathlib
import json
import logging
import math
import gzip
import dataclasses
import typing
from bs4 import BeautifulSoup
from dateutil.relativedelta import relativedelta
from datetime import datetime
import sys
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

ALL_MATCHES = {}
CHARTING_MATCHES = []

### UTILS/HELPERS ###
def normalize_string(s):
    return re.sub(r"\s+", " ", str(s)).strip().lower()

def build_dict(seq, key):
    return dict((d[key], dict(d, index=index)) for (index, d) in enumerate(seq))

def javascript_variable_exists(text: str, var_name: str) -> bool:
    return re.search(rf'\b(var|let|const)\s+{re.escape(var_name)}\s*=', text) is not None

def extract_javascript_variables(text: str, variable_names: list[str]) -> dict:
    data = {}
    for var_name in variable_names:
        match = re.search(rf'\b(var|let|const)\s+{re.escape(var_name)}\s*=\s*(.*?);', text, re.DOTALL)
        if not match:
            data[var_name] = None
            continue
        value = match.group(2).strip()
        # ARRAY DETECTION (ONLY HERE)
        if value.startswith("[") and value.endswith("]"):
            data[var_name] = extract_html_javascript_array(text, var_name)
            continue
        # STRING CLEANUP
        if (len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"')):
            inner = value[1:-1]
            data[var_name] = None if inner == "" else inner
            continue
        # DEFAULT
        data[var_name] = value
    return data

def extract_html_javascript_array(text, variable_name):
    match = re.search(rf"var {re.escape(variable_name)}\s*=\s*(\[[\s\S]*?\]);", text)
    if not match:
        LOGGER.debug("HTML JavaScript array (%s) not found: %s", variable_name, text)
        return None
    try:
        return json.loads(match.group(1)) # normalized = raw.replace("'", '"')
    except Exception as e:
        LOGGER.exception("Failed to extract HTML JavaScript array: %s", e)
        raise


### TENNISABSTRACT GLOBAL FUNCTIONS ###
def load_tennisabstract_player_index(fp):
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

@dataclasses.dataclass
class TennisAbstractMatch:
    _player: dict = dataclasses.field(default=None, init=True, repr=False)
    _raw: list[str] = dataclasses.field(default=None, init=True, repr=False)
    _clean: list[str] = dataclasses.field(default=None, init=False, repr=False)
    _guid: str = dataclasses.field(default=None, init=False, repr=False)

    @property
    def player(self) -> dict: return self._player
    @property
    def raw(self) -> list[str]: return self._raw
    @property
    def guid(self) -> str: return self._guid
    @property
    def clean(self) -> list[str]: return self._clean
    
    def __post_init__(self):
        self._clean = self.raw[:len(MATCH_BASE_ATTRIBUTES)]
        self.clean.append(self.get_charting_id())
        self._guid = self._make_match_guid()
        self.clean.append(self.guid)
    
    def to_dict(self): return dict(zip(MATCH_BASE_ATTRIBUTES, self.clean))
    def get_tournament_start_date(self): return self.clean[MATCH_BASE_ATTRIBUTES.index("tournament_start_date")]
    def get_tournament_name(self): return self.clean[MATCH_BASE_ATTRIBUTES.index("tournament_name")]
    def get_surface(self): return self.clean[MATCH_BASE_ATTRIBUTES.index("surface")]
    def get_level(self): return self.clean[MATCH_BASE_ATTRIBUTES.index("level")]
    def get_win_loss_result(self): return self.clean[MATCH_BASE_ATTRIBUTES.index("wl")]
    def get_player_rank(self): return self.clean[MATCH_BASE_ATTRIBUTES.index("rank")]
    def get_player_seed(self): return self.clean[MATCH_BASE_ATTRIBUTES.index("seed")]
    def get_player_entry(self): return self.clean[MATCH_BASE_ATTRIBUTES.index("entry")]
    def get_tournament_round(self): return self.clean[MATCH_BASE_ATTRIBUTES.index("round")]
    def get_match_score(self): return re.sub(r"\s+", " ", re.sub(r"\([^)]*\)", "", self.clean[MATCH_BASE_ATTRIBUTES.index("score")])).strip().replace("-", "_").replace(" ", ".") if self.clean[MATCH_BASE_ATTRIBUTES.index("score")] else "noscore"
    def get_match_best_of(self): return self.clean[MATCH_BASE_ATTRIBUTES.index("best_of")]
    def get_opponent_fullname(self): return self.clean[MATCH_BASE_ATTRIBUTES.index("opponent_fullname")]
    def get_opponent_rank(self): return self.clean[MATCH_BASE_ATTRIBUTES.index("orank")]
    def get_opponent_seed(self): return self.clean[MATCH_BASE_ATTRIBUTES.index("oseed")]
    def get_opponent_entry(self): return self.clean[MATCH_BASE_ATTRIBUTES.index("oentry")]
    def get_opponent_hand(self): return self.clean[MATCH_BASE_ATTRIBUTES.index("ohand")]
    def get_opponent_odob(self): return self.clean[MATCH_BASE_ATTRIBUTES.index("odob")]
    def get_opponent_ht(self): return self.clean[MATCH_BASE_ATTRIBUTES.index("oht")]
    def get_opponent_country(self): return self.clean[MATCH_BASE_ATTRIBUTES.index("ocountry")]
    def get_opponent_active_status(self): return self.clean[MATCH_BASE_ATTRIBUTES.index("oactive")]
    def get_match_duration(self): return self.clean[MATCH_BASE_ATTRIBUTES.index("time")]
    def get_player_fullname(self): return self.player.get("fullname")

    def _make_match_guid(self, sort_players=True):
        tournament_start_date = self.get_tournament_start_date()
        tournament = self.get_tournament_name()
        tournament_round = self.get_tournament_round()
        score = self.get_match_score()
        player = self.get_player_fullname()
        opponent = self.get_opponent_fullname()
        if sort_players and self.get_win_loss_result() != "W":
            winner, loser = opponent, player
            return f"{tournament_start_date}-{tournament}-{tournament_round}-{opponent}-{player}-{score}".replace(" ", "_")
        return f"{tournament_start_date}-{tournament}-{tournament_round}-{player}-{opponent}-{score}".replace(" ", "_")

    def get_charting_id(self):
        if len(self.raw) in [25, 27, 28, 30, 44]:
            match_id = self.raw[-4]
        elif len(self.raw) == 39:
            return None
        elif len(self.raw) == 42:
            match_id = self.raw[-2]
        elif len(self.raw) == 45:
            match_id = self.raw[-5]
        elif len(self.raw) == 47:
            match_id = self.raw[-7]
        elif len(self.raw) == 48:
            match_id = self.raw[-8]
        else:
            raise ValueError(f"Unexpected match length (len = {len(self.raw)}): {self.raw}")
        return match_id.replace(".html", "")

@dataclasses.dataclass
class TennisAbstractPlayer:
    # _player_directory: os.DirEntry = dataclasses.field(default=None, init=True, repr=False)
    _player_directory: pathlib.Path = dataclasses.field(default=None, init=True, repr=False)
    _fullname: str = dataclasses.field(default=None, init=True, repr=False)

    _player: dict = dataclasses.field(default=None, init=False, repr=False)
    _contains_all_matches: bool = dataclasses.field(default=False, init=False, repr=False)
    _player_id: str = dataclasses.field(default=None, init=False, repr=False)
    _nameparam: str = dataclasses.field(default=None, init=False, repr=False)
    _lastname: str = dataclasses.field(default=None, init=False, repr=False)
    _country: str = dataclasses.field(default=None, init=False, repr=False)
    _dob: str = dataclasses.field(default=None, init=False, repr=False)
    _hand: str = dataclasses.field(default=None, init=False, repr=False)
    _backhand: str = dataclasses.field(default=None, init=False, repr=False)
    _ht: str = dataclasses.field(default=None, init=False, repr=False)
    _atp_id: str = dataclasses.field(default=None, init=False, repr=False)
    _wta_id: str = dataclasses.field(default=None, init=False, repr=False)
    _itf_id: str = dataclasses.field(default=None, init=False, repr=False)
    _fc_id: str = dataclasses.field(default=None, init=False, repr=False)
    _dc_id: str = dataclasses.field(default=None, init=False, repr=False)
    _twitter: str = dataclasses.field(default=None, init=False, repr=False)
    _wiki_id: str = dataclasses.field(default=None, init=False, repr=False)
    _matches: list[T] = dataclasses.field(default=None, init=False, repr=False)

    def __post_init__(self):
        self._player = {
            "player_id": self.player_id,
            "fullname": self.fullname,
        }

    def __str__(self):
        return (f"{type(self).__name__}(" f"player_id={self.player_id!r}, " f"fullname={self.fullname!r}, " f"nameparam={self.nameparam!r}, " f"lastname={self.lastname!r}, " f"country={self.country!r}, " f"dob={self.dob!r}, " f"hand={self.hand!r}, " f"backhand={self.backhand!r}, " f"ht={self.ht!r})")

    @property
    # def player_directory(self) -> os.DirEntry: return self._player_directory
    def player_directory(self) -> pathlib.Path: return self._player_directory
    @property
    def player(self) -> dict: return self._player
    @property
    def contains_all_matches(self) -> bool: return self._contains_all_matches
    
    # Player Properties
    @property
    def player_id(self) -> str:
        if self._player_id is None and self._player_directory is not None:
            self._player_id = self.player_directory.name
        return self._player_id
    @property
    def fullname(self) -> str: return self._fullname
    @property
    def nameparam(self) -> str: return self._nameparam
    @property
    def lastname(self) -> str: return self._lastname
    @property
    def country(self) -> str: return self._country
    @property
    def dob(self) -> str: return self._dob
    @property
    def hand(self) -> str: return self._hand
    @property
    def backhand(self) -> str: return self._backhand
    @property
    def ht(self) -> str: return self._ht
    @property
    def atp_id(self) -> str: return self._atp_id
    @property
    def wta_id(self) -> str: return self._wta_id
    @property
    def itf_id(self) -> str: return self._itf_id
    @property
    def fc_id(self) -> str: return self._fc_id
    @property
    def dc_id(self) -> str: return self._dc_id
    @property
    def twitter(self) -> str: return self._twitter
    @property
    def wiki_id(self) -> str: return self._wiki_id
    @property
    def matches(self) -> list[dict]:
        #if self._matches is None:
        #    self._matches = self._clean_player_matches()
        return self._matches

    def _load_into_class(self):
        for k, v in self.player.items():
            if v is None:
                continue
            if isinstance(v, str) and not v.strip():
                continue
            if isinstance(v, (list, dict)) and not v:
                continue

            if k == "nameparam":
                self._nameparam = v
            elif k == "lastname":
                self._lastname = v
            elif k == "country":
                self._country = v
            elif k == "dob":
                self._dob = v
            elif k == "hand":
                self._hand = v
            elif k == "backhand":
                self._backhand = v
            elif k == "ht":
                self._ht = v
            elif k == "atp_id":
                self._atp_id = v
            elif k == "wta_id":
                self._wta_id = v
            elif k == "itf_id":
                self._itf_id = v
            elif k == "fc_id":
                self._fc_id = v
            elif k == "dc_id":
                self._dc_id = v
            elif k == "twitter":
                self._twitter = v
            elif k == "wiki_id":
                self._wiki_id = v

    def _load_player_matches(self):
        if "matches" in self.player and isinstance(self.player.get("matches"), list) and len(self.player.get("matches")) > 0:
            self._matches = []
            duplicates = []
            seen = set()
            for m in self.player.get("matches", []):
                if not isinstance(m, list):
                    continue
                key = tuple(m)
                if key in seen:
                    duplicates.append(m)
                else:
                    match_obj = TennisAbstractMatch(self.player, m)
                    seen.add(key)
                    self.matches.append(match_obj)

    def scrape_directory(self):
        for file in pathlib.Path(self.player_directory).iterdir():
            try:
                obj = data_objects.DataObjectFactory.create(file)
                text = obj.data
            except Exception as e:
                LOGGER.exception("Failed to load file: %s", e)
                raise
            self.extract_javascript_properties(text)
            self.extract_javascript_matches_from_file(file, text)
        self._load_into_class()
        self._load_player_matches()

    def extract_javascript_properties(self, text: str):
        props = extract_javascript_variables(text, PLAYER_ATTRIBUTES)
        if not all(v is None or (isinstance(v, str) and v.strip() == "") for v in props.values()):
            for k, v in props.items():
                if k not in self.player:
                    self.player[k] = v
                else:
                    if self.player[k] in [None, [], {}, ""] and v not in [None, [], {}, ""]:
                        self.player[k] = v

    def extract_javascript_matches_from_file(self, file, text):
        if file.suffix == ".html":
            if "// test" in text or not javascript_variable_exists(text, "matchmx"):
                LOGGER.debug("HTML is test page: %s", self.player_id)
                return
            self.player["matches"] = extract_html_javascript_array(text, "matchmx")
            self._contains_all_matches = True
        
        if (file.suffix == ".js" or file.name.endswith(".js.gz")) and not self.contains_all_matches:
            # JavaScript File
            if "career" in file.name:
                matches = extract_html_javascript_array(text, "morematchmx")
            else:
                matches = extract_html_javascript_array(text, "matchmx")

            if matches is not None:
                if "matches" in self.player:
                    self.player["matches"].extend(matches)
                else:
                    self.player["matches"] = matches
        #else:
        #    LOGGER.error("Unexpected file type in player directory, expected html or javascript but got: %s", file)



### ALL PLAYERS ###
@dataclasses.dataclass
class TennisAbstractPlayers: 
    _raw_data_directory: os.DirEntry = dataclasses.field(default=None, init=True, repr=False)
    _charting_matches_file_path: os.DirEntry = dataclasses.field(default=None, init=True, repr=False)

    _charted_matches: dict = dataclasses.field(default=None, init=False, repr=False)
    _players: dict = dataclasses.field(default=None, init=False, repr=False)
    _player_matches: dict = dataclasses.field(default=None, init=False, repr=False)

    def __post_init__(self):
        charted_matches = data_objects.JsonlDataObject(self._charting_matches_file_path).data
        self._charted_matches = build_dict(charted_matches, "match_id")

    @property
    def raw_data_directory(self) -> os.DirEntry: return self._raw_data_directory

    @property
    def charted_matches(self) -> dict:
        if self._charted_matches is None:
            return None
        return self._charted_matches

    @property
    def players(self) -> dict:
        if self._players is None:
            return None
        return self._players
    
    @property
    def player_matches(self) -> dict:
        if self._player_matches is None:
            return None
        return self._player_matches

    def find_player_full_name(self, name):
        for _, v in self.charted_matches.items():
            if name == v["player_1_id"]:
                return v.get("player_1_fullname", None)
            elif name == v["player_2_id"]:
                return v.get("player_2_fullname", None)
        LOGGER.warning("No charted matches with player named %s", name)

    def scrape_player_directories(self):
        self._players = {}
        count = 0
        with os.scandir(self.raw_data_directory) as it:
            for entry in it:
                if not entry.is_dir():
                    continue

                player_obj = TennisAbstractPlayer(entry, self.find_player_full_name(entry.name))
                player_obj.scrape_directory()
                if player_obj and player_obj.player_id and player_obj.player_id not in self.players:
                    self.players[player_obj.player_id] = player_obj
                else:
                    LOGGER.fatal("Player object failed to be added to list: %s", player_obj)
                LOGGER.debug(f"{player_obj}")
                count += 1                
                if count % 30 == 0:
                    LOGGER.info(f"Completed {(count / 2204) * 100:.2f}%")
            print(f"Saved Players: {len(self.players)}")

    


def update_player_matches_with_optimal(players):
    for player in players:
        if player.matches:
            for i, m in enumerate(player.matches):
                if m[-1] in ALL_MATCHES and not ALL_MATCHES[m[-1]] == m:
                    optimal_match = ALL_MATCHES[m[-1]]
                    optimal_match.pop()
                    player.matches[i] = optimal_match
        else:
            LOGGER.warning("Player has no matches: %s", player.player_fullname)
    return players

def merge_dict_lists_fill(list1, list2, key):
    def is_empty(val):
        return val is None or val == ""

    dict1 = {item[key]: item for item in list1}
    dict2 = {item[key]: item for item in list2}

    all_keys = set(dict1) | set(dict2)
    merged = []

    for k in all_keys:
        item1 = dict1.get(k, {})
        item2 = dict2.get(k, {})

        merged_item = {}

        # combine all fields from both dicts
        fields = set(item1) | set(item2)

        for field in fields:
            v1 = item1.get(field)
            v2 = item2.get(field)

            if not is_empty(v1) and not is_empty(v2):
                merged_item[field] = v1  # prefer list1
            elif not is_empty(v1):
                merged_item[field] = v1
            else:
                merged_item[field] = v2

        merged.append(merged_item)

    return merged

if __name__ == "__main__":
    
    # PLAYER_INDEX = load_tennisabstract_player_index(DATA_DIR / "raw/tennisabstract/scraper/charting_players_urls.txt")
    PLAYER_ATTRIBUTES = data_objects.DataObjectFactory.create(DATA_DIR / "raw/tennisabstract/scraper/js_player_attributes.json").data
    MATCH_BASE_ATTRIBUTES = data_objects.DataObjectFactory.create(DATA_DIR / "raw/tennisabstract/scraper/js_match_attributes.json").data
# 
    output_file = DATA_DIR / "dev/tennisabstract/players.jsonl"

    players_object = TennisAbstractPlayers(PLAYERS_DIR, DATA_DIR / "dev/tennisabstract/charting_matches.jsonl")
    players_object.scrape_player_directories()
    quit()

    # print(f"Charted Matches: {len(charted_matches)}")
    # with open(DATA_DIR / "dev/tennisabstract/charted_matches.jsonl", "w", encoding="utf-8") as f:
    #     for match in charted_matches:
    #         f.write(json.dumps(match, ensure_ascii=False) + "\n")



"""
def compare_dict_lists(list1, list2, key):
    dict1 = {item[key]: item for item in list1}
    dict2 = {item[key]: item for item in list2}

    keys1 = set(dict1.keys())
    keys2 = set(dict2.keys())

    return {
        "unique_combined": len(list({**dict1, **dict2}.values())),  # merged (list2 overrides on conflict)
        "duplicates": len([dict1[k] for k in keys1 & keys2]),
        "only_in_list1": len([dict1[k] for k in keys1 - keys2]),
        "only_in_list2": len([dict2[k] for k in keys2 - keys1]),
        "in_both": len(keys1 & keys2),
    }
"""

"""
# Used to combine the GitHub CSV charting matches to scraped charting matches.

charted_matches = merge_raw_charting_matches()

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
"""