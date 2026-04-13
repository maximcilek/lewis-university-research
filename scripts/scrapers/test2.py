import pathlib
import json
import dataclasses
from typing import Any
import sys
import re
import logging
import typing
sys.path.append(str(pathlib.Path(__file__).resolve().parent.parent.parent))
import tennisabstractscraper.models.data_objects as data_objects

# LOGGER
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
LOGGER = logging.getLogger(__name__)

# ENV VARIABLES
DATA_DIR = pathlib.Path(__file__).resolve().parent.parent.parent / "data"
PLAYERS_DIR = DATA_DIR / "raw/tennisabstract/players"

# Generic Type Placeholder
T = typing.TypeVar("T")

# GLOBAL
PLAYER_ATTRIBUTES = None
MATCH_BASE_ATTRIBUTES = None

CHARTED_MATCHES = data_objects.JsonlDataObject(DATA_DIR / "dev/tennisabstract/charting_matches.jsonl").data
CHARTED_MATCHES_BY_ID = None
# =========================
# DISK STORE
# =========================

class PlayerStore:
    BASE = pathlib.Path(DATA_DIR / "dev/tennisabstract/players")
    BASE.mkdir(parents=True, exist_ok=True)

    @classmethod
    def path(cls, player_id: str):
        return cls.BASE / f"{player_id}.json"

    @classmethod
    def load(cls, player_id: str) -> dict:
        path = cls.path(player_id)
        if path.exists():
            return json.loads(path.read_text())
        return {}

    @classmethod
    def save(cls, player: "Player"):
        path = cls.path(player.player_id)
        path.write_text(json.dumps(dataclasses.asdict(player), indent=2))


# =========================
# FACTORY (IDENTITY LAYER)
# =========================

class PlayerFactory:
    _cache: dict[str, "Player"] = {}
    @classmethod
    def get(cls, player_id:str):
        if player_id not in cls._cache:
            player = Player(player_id)
            # hydrate from disk if exists
            cached = PlayerStore.load(player_id)
            player.hydrate_profile(cached)
            cls._cache[player_id] = player
        return cls._cache[player_id]
    @classmethod
    def all(cls) -> list["Player"]:
        return list(cls._cache.values())


# =========================
# PLAYER ENTITY
# =========================

@dataclasses.dataclass
class Player:
    player_id: str = dataclasses.field(default=None, init=True, repr=False)
    fullname: str = dataclasses.field(default=None, init=False, repr=False)
    nameparam: str = dataclasses.field(default=None, init=False, repr=False)
    lastname: str = dataclasses.field(default=None, init=False, repr=False)
    country: str = dataclasses.field(default=None, init=False, repr=False)
    dob: str = dataclasses.field(default=None, init=False, repr=False)
    hand: str = dataclasses.field(default=None, init=False, repr=False)
    backhand: str = dataclasses.field(default=None, init=False, repr=False)
    ht: str = dataclasses.field(default=None, init=False, repr=False)
    atp_id: str = dataclasses.field(default=None, init=False, repr=False)
    wta_id: str = dataclasses.field(default=None, init=False, repr=False)
    itf_id: str = dataclasses.field(default=None, init=False, repr=False)
    fc_id: str = dataclasses.field(default=None, init=False, repr=False)
    dc_id: str = dataclasses.field(default=None, init=False, repr=False)
    twitter: str = dataclasses.field(default=None, init=False, repr=False)
    wiki_id: str = dataclasses.field(default=None, init=False, repr=False)
    matches: dict = dataclasses.field(default_factory=dict)

    # PROFILE HYDRATION (strong)
    def hydrate_profile(self, data: dict):
        if not data:
            return
        for k, v in data.items():
            if not hasattr(self, k):
                continue
            current = getattr(self, k)
            if current in [None, ""] and v not in [None, ""]:
                setattr(self, k, v)

    # -------------------------
    # MATCH HYDRATION (weak)
    # -------------------------
    def hydrate_match(self, match_arr: list[str], charting_id):
        result = {}
        tournament_start_date = match_arr[MATCH_BASE_ATTRIBUTES.index("tournament_start_date")]
        tournament_name = match_arr[MATCH_BASE_ATTRIBUTES.index("tournament_name")]
        tournament_round = match_arr[MATCH_BASE_ATTRIBUTES.index("round")]
        player = self.fullname
        opponent_fullname = match_arr[MATCH_BASE_ATTRIBUTES.index("opponent_fullname")]
        score = re.sub(r"\s+", " ", re.sub(r"\([^)]*\)", "", match_arr[MATCH_BASE_ATTRIBUTES.index("score")])).strip().replace("-", "_").replace(" ", ".") if match_arr[MATCH_BASE_ATTRIBUTES.index("score")] else "noscore"
        json_data = dict(zip(MATCH_BASE_ATTRIBUTES, match_arr))
        if match_arr[MATCH_BASE_ATTRIBUTES.index("wl")] == "L":
            # Loser
            winner, loser = opponent_fullname, player
        elif match_arr[MATCH_BASE_ATTRIBUTES.index("wl")] == "W" or match_arr[MATCH_BASE_ATTRIBUTES.index("wl")] == "U":
            # Winner
            winner, loser = player, opponent_fullname
        else:
            LOGGER.fatal("Unexpected match result: %s", json_data)
            quit()
        match_id = f"{tournament_start_date}-{tournament_name}-{tournament_round}-{winner}-{loser}-{score}".replace(" ", "_")
        json_data["charting_id"] = charting_id
        players = sorted([winner, loser])
        if match_arr[MATCH_BASE_ATTRIBUTES.index("wl")] == "W" or match_arr[MATCH_BASE_ATTRIBUTES.index("wl")] == "L":
            json_data["winner"] = players.index(winner) + 1
        else:
            json_data["winner"] = None
        json_data[f"player_{players.index(player) + 1}_fullname"] = player
        json_data[f"player_{players.index(player) + 1}_rank"] = json_data.get("rank")
        json_data[f"player_{players.index(player) + 1}_seed"] = json_data.get("seed")
        json_data[f"player_{players.index(player) + 1}_entry"] = json_data.get("entry")
        json_data[f"player_{players.index(opponent_fullname) + 1}_fullname"] = opponent_fullname
        json_data[f"player_{players.index(opponent_fullname) + 1}_rank"] = json_data.get("orank")
        json_data[f"player_{players.index(opponent_fullname) + 1}_seed"] = json_data.get("oseed")
        json_data[f"player_{players.index(opponent_fullname) + 1}_entry"] = json_data.get("oentry")
        del json_data["wl"]
        del json_data["rank"]
        del json_data["seed"]
        del json_data["entry"]
        del json_data["orank"]
        del json_data["oseed"]
        del json_data["oentry"]
        del json_data["opponent_fullname"]
        del json_data["ohand"]
        del json_data["odob"]
        del json_data["oht"]
        del json_data["ocountry"]
        del json_data["oactive"]
        if match_id not in self.matches:
            self.matches[match_id] = json_data
        else:
            if json_data != self.matches[match_id]:
                if json_data.get("player_1_seed") == self.matches[match_id].get("player_1_entry"):
                    return
                if json_data.get("player_1_rank") not in [None, ""] and self.matches[match_id].get("player_1_rank") in [None, ""]:
                    self.matches[match_id]["player_1_rank"] = json_data.get("player_1_rank")
                    return
                if json_data.get("player_2_rank") not in [None, ""] and self.matches[match_id].get("player_2_rank") in [None, ""]:
                    self.matches[match_id]["player_2_rank"] = json_data.get("player_2_rank")
                    return
                if (self.matches[match_id].get("player_1_rank") not in [None, ""] and json_data.get("player_1_rank") in [None, ""]) or \
                    (self.matches[match_id].get("player_2_rank") not in [None, ""] and json_data.get("player_2_rank") in [None, ""]):
                    return
                
                if json_data.get("best_of") not in [None, ""]:
                    if self.matches[match_id] in [None, ""]:
                        self.matches[match_id]["best_of"] = json_data.get("best_of")
                    else:
                        self.matches[match_id]["best_of"] = max(int(self.matches[match_id].get("best_of")), int(json_data.get("best_of")))
                    return
                if json_data.get("charting_id") in [None, ""] and self.matches[match_id].get("charting_id") not in [None, ""]:
                    return
                if (self.matches[match_id].get("charting_id") in [None, ""] and json_data.get("charting_id") not in [None, ""]):
                    self.matches[match_id]["charting_id"] = json_data.get("charting_id")
                    return
                LOGGER.fatal("Unexpected change in match data (%s): %s\n%s", match_id, json_data, self.matches[match_id])
                quit()



# =========================
# INGESTION ENGINE
# =========================

def ingest_match(player_id: str, match: list[str]):
    player_fullname = find_player_full_name(player_id)
    player = PlayerFactory.get(player_id)

    is_charted = False
    charting_id = get_charting_id(match)
    new_match = match[:len(MATCH_BASE_ATTRIBUTES)]
    # new_match.append(charting_id)
    player.hydrate_match(new_match, charting_id)
    opponent_name = new_match[MATCH_BASE_ATTRIBUTES.index("opponent_fullname")]
    opponent_id = opponent_name.replace(" ", "")
    opponent = PlayerFactory.get(opponent_id)
    if opponent:
        opponent.fullname = opponent_name
        opponent.nameparam = opponent_id
        opponent.hand = match[MATCH_BASE_ATTRIBUTES.index("ohand")]
        opponent.dob = match[MATCH_BASE_ATTRIBUTES.index("odob")]
        opponent.ht = match[MATCH_BASE_ATTRIBUTES.index("oht")]
        opponent.country = match[MATCH_BASE_ATTRIBUTES.index("ocountry")]

        orank = new_match[MATCH_BASE_ATTRIBUTES.index("orank")]
        new_match[MATCH_BASE_ATTRIBUTES.index("orank")] = new_match[MATCH_BASE_ATTRIBUTES.index("rank")]
        new_match[MATCH_BASE_ATTRIBUTES.index("rank")] = orank
        
        oseed = new_match[MATCH_BASE_ATTRIBUTES.index("oseed")]
        new_match[MATCH_BASE_ATTRIBUTES.index("oseed")] = new_match[MATCH_BASE_ATTRIBUTES.index("seed")]
        new_match[MATCH_BASE_ATTRIBUTES.index("seed")] = oseed
        
        oentry = new_match[MATCH_BASE_ATTRIBUTES.index("oentry")]
        new_match[MATCH_BASE_ATTRIBUTES.index("oentry")] = new_match[MATCH_BASE_ATTRIBUTES.index("entry")]
        new_match[MATCH_BASE_ATTRIBUTES.index("entry")] = oentry        
        
        new_match[MATCH_BASE_ATTRIBUTES.index("opponent_fullname")] = player_fullname
        new_match[MATCH_BASE_ATTRIBUTES.index("ohand")] = player.hand
        new_match[MATCH_BASE_ATTRIBUTES.index("odob")] = player.dob
        new_match[MATCH_BASE_ATTRIBUTES.index("oht")] = player.ht
        new_match[MATCH_BASE_ATTRIBUTES.index("ocountry")] = player.country
        new_match[MATCH_BASE_ATTRIBUTES.index("oactive")] = None

        if new_match[MATCH_BASE_ATTRIBUTES.index("wl")] == "W":
            new_match[MATCH_BASE_ATTRIBUTES.index("wl")] = "L"
        if new_match[MATCH_BASE_ATTRIBUTES.index("wl")] == "L":
            new_match[MATCH_BASE_ATTRIBUTES.index("wl")] = "W"
        opponent.hydrate_match(new_match, charting_id)


# =========================
# DIRECTORY INGESTION
# =========================

def ingest_player_directory(player_dir: pathlib.Path):
    player_id = player_dir.name
    player = PlayerFactory.get(player_id)
    has_all_matches = False

    for file in player_dir.iterdir():
        if file.suffix.strip() not in [".js", ".html"] and not file.name.endswith(".js.gz"):
            continue

        try:
            obj = data_objects.DataObjectFactory.create(file)
            text = obj.data
        except Exception as e:
            LOGGER.exception("Failed to load file: %s", e)
            raise

        profile = extract_javascript_variables(text, PLAYER_ATTRIBUTES)
        if file.suffix == ".html":
            if "// test" in text or not javascript_variable_exists(text, "matchmx"):
                LOGGER.debug("HTML is test page: %s", file.name)
                continue
            matches = extract_html_javascript_array(text, "matchmx")
            has_all_matches = True
        elif (file.suffix == ".js" or file.name.endswith(".js.gz")) and not has_all_matches:
            if "career" in file.name:
                matches = extract_html_javascript_array(text, "morematchmx")
            else:
                matches = extract_html_javascript_array(text, "matchmx")

        player.hydrate_profile(profile)
        unique = []
        duplicates = []
        seen = set()
        for m in matches:
            if not isinstance(m, list):
                continue
            key = tuple(m)
            if key not in seen:
                ingest_match(player_id, m)
                seen.add(key)
    
    # print(len(player.matches))
    # PlayerStore.save(player)


# =========================
# MAIN ENTRY
# =========================

def run(players_dir: pathlib.Path):
    count = 0
    for player_dir in players_dir.iterdir():
        if count % 40 == 0:
            LOGGER.info(f"Completed {(count / 2204) * 100:.2f}%")
        if player_dir.is_dir():
            ingest_player_directory(player_dir)
        count += 1

    all_players = PlayerFactory.all()
    print(f"Successfully Scraped {len(all_players)} Players")
    print(len(all_players[0].matches))
    print(len(all_players[1].matches))
    write_players_jsonl(all_players, DATA_DIR / "dev/tennisabstract/players_all.jsonl")

    # flush final cache
    #for player in PlayerFactory._cache.values():
    #    PlayerStore.save(player)


# =========================
# PLACEHOLDER PARSERS
# =========================
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

def extract_matches(self, file, text):
    if file.suffix == ".html":
        if "// test" in text or not javascript_variable_exists(text, "matchmx"):
            LOGGER.debug("HTML is test page: %s", file.name)
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

def get_charting_id(arr):
        if len(arr) in [25, 27, 28, 30, 44]:
            match_id = arr[-4]
        elif len(arr) == 39:
            return None
        elif len(arr) == 42:
            match_id = arr[-2]
        elif len(arr) == 45:
            match_id = arr[-5]
        elif len(arr) == 47:
            match_id = arr[-7]
        elif len(arr) == 48:
            match_id = arr[-8]
        else:
            raise ValueError(f"Unexpected match length (len = {len(arr)}): {arr}")
        return match_id.replace(".html", "")

def find_player_full_name(name):
    for _, v in CHARTED_MATCHES_BY_ID.items():
        if name == v["player_1_id"]:
            return v.get("player_1_fullname", None)
        elif name == v["player_2_id"]:
            return v.get("player_2_fullname", None)
    LOGGER.warning("No charted matches with player named %s", name)

def find_player_id(name):
    for _, v in CHARTED_MATCHES_BY_ID.items():
        if name == v["player_1_fullname"]:
            return v.get("player_1_id", None)
        elif name == v["player_2_fullname"]:
            return v.get("player_2_id", None)
    LOGGER.warning("No charted matches with player named %s", name)

def write_players_jsonl(players: list["Player"], output_path: pathlib.Path):
    with open(output_path, "w", encoding="utf-8") as f:
        for player in players:
            f.write(json.dumps(dataclasses.asdict(player), ensure_ascii=False) + "\n")

# =========================
# RUN
# =========================

if __name__ == "__main__":
    PLAYER_ATTRIBUTES = data_objects.DataObjectFactory.create(DATA_DIR / "raw/tennisabstract/scraper/js_player_attributes.json").data
    MATCH_BASE_ATTRIBUTES = data_objects.DataObjectFactory.create(DATA_DIR / "raw/tennisabstract/scraper/js_match_attributes.json").data
    CHARTED_MATCHES_BY_ID = build_dict(CHARTED_MATCHES, "match_id")
    run(PLAYERS_DIR)