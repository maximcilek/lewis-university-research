# tennisabstractscraper/models/tennisabstract_data.py

import dataclasses
from . import data_objects
import logging
import typing
import re
import json
import pyarrow.parquet as pq
import pathlib

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)

DATA_DIR = pathlib.Path(__file__).resolve().parent.parent.parent / "data"

T = typing.TypeVar("T")
# Serve direction, faults, and outcomes
SERVE_DIRECTIONS = {'4': 'wide', '5': 'body', '6': 'T', '7': 'within_service_boxes', '0': 'unknown'}
SERVE_FAULTS = {'n': 'net', 'w': 'wide', 'd': 'deep', 'x': 'wide and deep', 'g': 'foot fault', 'e': 'unknown', '!': 'shank', 'V': 'time violation'}

# Shot types for rallies
SHOT_TYPES = set("fbvzosuplhijktq")  # includes all shot codes
DIRECTIONS = set("1230")             # direction codes
DEPTHS = set("789")                  # optional depths
ERRORS = set("nwde!")                # ending errors
ENDING = set("@#*")                  # unforced, forced, winner

# Regex patterns
SERVE_PATTERN = re.compile(r'^(c*)([4560]?)([nwde!]?)([\*#]?)(\+?)')
RALLY_PATTERN = re.compile(r'^([fbvzosuplhijktq][1230]?([789])?)+([nwde!]?[@#])?$')

tiebreak_score_table = {}

unique_scores = []
def parse_score(x):
  return int(x) if x.isdigit() else x
def next_score(p1_pts, p2_pts, p1_games, p2_games, p1_sets, p2_sets,
               point_winner, tiebreak=False):

    score_map = [0, 15, 30, 40]

    # --- NORMALIZE INPUT (handle "AD") ---
    def to_index(x):
        if x == "AD":
            return 4
        if x in score_map:
            return score_map.index(x)
        return x  # for tiebreak integers

    def from_index(i, opponent_i):
        # Deuce case
        if i >= 3 and opponent_i >= 3:
            if i == opponent_i:
                return 40
            elif i == opponent_i + 1:
                return "AD"
            elif opponent_i == i + 1:
                return 40
        return score_map[i] if i < 4 else "AD"

    # --- TIEBREAK ---
    if tiebreak:
        if point_winner == 1:
            p1_pts += 1
        else:
            p2_pts += 1

        if (p1_pts >= 7 or p2_pts >= 7) and abs(p1_pts - p2_pts) >= 2:
            if p1_pts > p2_pts:
                p1_sets += 1
            else:
                p2_sets += 1
            return 0, 0, 0, 0, p1_sets, p2_sets, False

        return p1_pts, p2_pts, p1_games, p2_games, p1_sets, p2_sets, True

    # --- NORMAL GAME ---
    p1 = to_index(p1_pts)
    p2 = to_index(p2_pts)

    # Add point
    if point_winner == 1:
        p1 += 1
    else:
        p2 += 1

    # --- GAME WIN LOGIC ---
    if p1 >= 3 and p2 >= 3:
        if p1 >= p2 + 2:
            p1_games += 1
            p1, p2 = 0, 0
        elif p2 >= p1 + 2:
            p2_games += 1
            p1, p2 = 0, 0
        else:
            return (
                from_index(p1, p2),
                from_index(p2, p1),
                p1_games,
                p2_games,
                p1_sets,
                p2_sets,
                False
            )
    elif p1 >= 4:
        p1_games += 1
        p1, p2 = 0, 0
    elif p2 >= 4:
        p2_games += 1
        p1, p2 = 0, 0
    else:
        return (
            from_index(p1, p2),
            from_index(p2, p1),
            p1_games,
            p2_games,
            p1_sets,
            p2_sets,
            False
        )

    # --- SET WIN ---
    if (p1_games >= 6 or p2_games >= 6) and abs(p1_games - p2_games) >= 2:
        if p1_games > p2_games:
            p1_sets += 1
        else:
            p2_sets += 1
        return 0, 0, 0, 0, p1_sets, p2_sets, False

    # --- TIEBREAK TRIGGER ---
    if p1_games == 6 and p2_games == 6:
        return 0, 0, p1_games, p2_games, p1_sets, p2_sets, True

    return 0, 0, p1_games, p2_games, p1_sets, p2_sets, False

@dataclasses.dataclass
class TennisAbstractData:
    _players_file_path: str = dataclasses.field(default=None, init=True, repr=False)
    _charting_matches_file_path: str = dataclasses.field(default=None, init=True, repr=False)
    _charting_points_file_path: str = dataclasses.field(default=None, init=True, repr=False)

    _players: T = dataclasses.field(default=None, init=False, repr=False)
    _charting_matches: T = dataclasses.field(default=None, init=False, repr=False)
    _charting_points: T = dataclasses.field(default=None, init=False, repr=False)

    @property
    def players_file_path(self) -> str:
      return self._players_file_path
    @property
    def charting_matches_file_path(self) -> str:
      return self._charting_matches_file_path
    @property
    def charting_points_file_path(self) -> str:
      return self._charting_points_file_path


    @property
    def players(self) -> T:
        if self._players is None:
            self._players = self._load_players().data
        return self._players    
    @property
    def charting_matches(self) -> T:
        if self._charting_matches is None:
            self._charting_matches = self._load_charting_matches().data
        return self._charting_matches
    @property
    def charting_points(self) -> typing.Iterator[dict]:
        if self._charting_points is None:
            self._charting_points = self._load_charting_points()
        logger.info("Streaming charting points from file: %s", self.charting_points_file_path)
        return self._charting_points.data  # iterator from Parquet/JSONL object

    def _load_players(self) -> T:
        try:
            obj = data_objects.DataObjectFactory.create(self.players_file_path)
            if isinstance(obj, data_objects.ParquetDataObject):
                parquet_file = pq.ParquetFile(self.players_file_path)
                total_rows = parquet_file.metadata.num_rows
                logger.info("Successfully loaded %d players (streaming)", total_rows)
            else:
                logger.info("Successfully loaded players as %s", type(obj))
            return obj
        except Exception as e:
            logger.exception("Failed to load players: %s", e)
            raise
    
    def _load_charting_matches(self) -> T:
        try:
            obj = data_objects.DataObjectFactory.create(self.charting_matches_file_path)
            if isinstance(obj, data_objects.ParquetDataObject):
                parquet_file = pq.ParquetFile(self.charting_matches_file_path)
                total_rows = parquet_file.metadata.num_rows
                logger.info("Charting matches ready for streaming (%d rows)", total_rows)
            else:
                logger.info("Successfully loaded matches as %s", type(obj))
            return obj
        except Exception as e:
            logger.exception("Failed to load charting matches: %s", e)
            raise
    
    def _load_charting_points(self) -> T:
        logger.info("Loading charting points from file: %s", self.charting_points_file_path)
        try:
            obj = data_objects.DataObjectFactory.create(self.charting_points_file_path)
            logger.info("Charting points ready for streaming from file: %s", self.charting_points_file_path)
            return obj
        except Exception as e:
            logger.exception("Failed to load charting points: %s", e)
            raise

    """
    def stream_jsonl(self, file_path):
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                yield json.loads(line)
    """

@dataclasses.dataclass
class TennisAbstractPointsData:
    _file_path: str = dataclasses.field(default=None, init=True, repr=False)
    _rally_codes_file_path: str = dataclasses.field(default=None, init=True, repr=False)
    _data_object: T = dataclasses.field(default=None, init=False, repr=False)
    _rally_codes: T | None = dataclasses.field(default=None, init=False, repr=False)

    @property
    def file_path(self) -> str:
      return self._file_path
    
    @property
    def rally_codes_file_path(self) -> str:
      return self._rally_codes_file_path

    @property
    def data_object(self) -> T:
        if self._data_object == None:
          try:
              self._data_object = data_objects.DataObjectFactory.create(self.file_path)
          except Exception as e:
              logger.exception("Failed to load points: %s", e)
              raise
        return self._data_object
    
    @property
    def rally_codes(self) -> dict:
        if self._rally_codes is None:
            try:
              self._rally_codes = data_objects.DataObjectFactory.create(self.rally_codes_file_path).data
            except Exception as e:
                logger.exception("Failed to load rally codes: %s", e)
                raise
        return self._rally_codes
    
    def next_tiebreak_score(self, score, is_server_winner):
        a, b = map(int, score.split("-"))
        
        if is_server_winner:
            a += 1
        else:
            b += 1
        
        if (max(a, b) >= 7) and (abs(a - b) >= 2):
            return f"0-0"
            
        return f"{a}-{b}"
    def next_game_score(self, a, b, server_wins):
        if server_wins:
            a += 1
        else:
            b += 1

        # convert raw points to tennis display
        def fmt(x):
            return {0:"0",1:"15",2:"30",3:"40"}.get(x, "40")

        # deuce logic
        if a >= 3 and b >= 3:
            if a == b:
                return "40-40"
            if a == b + 1:
                return "ad-40"
            if b == a + 1:
                return "40-ad"

        return f"{fmt(a)}-{fmt(b)}"
    
    
    def _is_serve_in(self, clean_rally_pattern):
      # 1st Rally In: =IF(N18="","",IF(LEN(FIRST_SERVE_RALLY_PATTERN)=1,"",IF(ISERROR(FIND(MID(FIRST_SERVE_RALLY_PATTERN_NO_LETS,2,1),"wdnxgeVPQRS"))=TRUE(),1,0)))
      if not clean_rally_pattern or len(clean_rally_pattern) == 1:
          is_in = None
      else:
          is_in = 1 if clean_rally_pattern[1] not in "wdnxgeVPQRS" else 0
      return is_in

    def _remove_lets_from_rally_pattern(self, pattern):
        return pattern.replace("c", "")

    def _ensure_player_games_won(self, point, prev_point):
        def parse(value, fallback):
            def normalize(v):
                if v is None:
                    return ""
                return str(v).strip()
            value = normalize(value)
            fallback = normalize(fallback)
            if value.isdigit():
                return int(value)
            if fallback.isdigit():
                return int(fallback)
            return None

        game_1 = parse(point.get("game_1"), prev_point.get("game_1"))
        game_2 = parse(point.get("game_2"), prev_point.get("game_2"))
        
        if game_1 not in [None, ""] and game_2 not in [None, ""]:
            point["game_1"] = game_1
            point["game_2"] = game_2
            return point
        print(game_1)
        print(game_2, prev_point.get("game_2"))
        logger.fatal("missing a player's number of games won in the match: %s | %s", point.get("game_1"), point.get("game_2"))
        raise ValueError("Invalid match state: missing games won values")

    def _is_point_in_tiebreaker_set(self, tiebreaker_str):
        if tiebreaker_str == "t":
            return True
        elif tiebreaker_str == "f":
            return False
        else:
            raise ValueError("Unexpected tiebreaker_set value, expected 't' or 'f' but got: %s", tiebreaker_str)
            return

    def _update_tiebreak_point_flag(self, point, prev_point, tb_set):
        tb_point_flag = 1 if point.get("game_1") == 6 and point.get("game_2") == 6 and tb_set == 1 else 0
        point["tb_point_flag"] = tb_point_flag
        if tb_point_flag == 1:
            if point["game_score"] == "0-0":
                tb_point_number = 1
            else:
                tb_point_number = prev_point["tb_point_number"] + 1
            prev_point["tb_point_number"] = tb_point_number
        else:
            tb_point_number = 0
            prev_point["tb_point_number"] = 0
        point["tb_point_number"] = tb_point_number
        return point, prev_point
        
    def load_points(self, charted_matches_by_id):
        count_points = 0
        skipped = 0
        prev_point = {}
        prev_result = {}
        points = {}
        all_points = []
        with open(DATA_DIR / "dev/tennisabstract/charting_points.jsonl", "w", encoding="utf-8") as f:
            for count, batch in enumerate(self.data_object):
                for point in batch:
                    if charted_matches_by_id.get(point.get("match_id")) is None or point.get("tiebreaker_set") in [None, ""]:
                        skipped += 1
                        continue

                    charted_match = charted_matches_by_id.get(point.get("match_id"))

                    if point["match_id"] not in points:
                        points[point["match_id"]] = []
                    
                    shots = []
                    first = point.get("first_serve_rally").replace(")*", "0*").replace("&*", "0*").replace("?", "0")
                    second = point.get("second_serve_rally")

                    first_no_let = self._remove_lets_from_rally_pattern(first)
                    second_no_let = self._remove_lets_from_rally_pattern(second)
                    first_in = self._is_serve_in(first_no_let)
                    second_in = self._is_serve_in(second_no_let)


                    point = self._ensure_player_games_won(point, prev_point)
                    tb_set = self._is_point_in_tiebreaker_set(point.get("tiebreaker_set"))
                    point, prev_point = self._update_tiebreak_point_flag(point, prev_point, tb_set)
                    
                    # IsRally1st =IF(N18="","",IF(S18=0,0,IF(LEN(Q18)>2,1,0)))
                    is_rally_first = 0 if first_in == 0 else int(len(first_no_let) > 2)
                    is_rally_second = 0 if second_in == 0 else int(len(second_no_let) > 2)

                    # Serve{1,2}: =IF(N18="","",IF(U18=0,Q18,LEFT(Q18,1)))
                    serve1 = first_no_let if is_rally_first == 0 else first_no_let[0]
                    serve2 = second_no_let if is_rally_second == 0 else second_no_let[0]

                    # Rally
                    """
                    =IF(N18="","",IF(U18=1,RIGHT(Q18,(LEN(Q18)-1)),IF(V18=1,RIGHT(R18,(LEN(R18)-1)),"")))
                    """
                    if is_rally_first == 1:
                        rally_part = first_no_let[1:]
                    elif is_rally_second == 1:
                        rally_part = second_no_let[1:]
                    else:
                        rally_part = None

                    # isAce: =IF(N18="","",IF(U18=1,RIGHT(Q18,(LEN(Q18)-1)),IF(V18=1,RIGHT(R18,(LEN(R18)-1)),"")))
                    # isUnret: =IF(W18="","",OR(IF(ISERR(FIND("#",W18)),FALSE(),TRUE()), IF(ISERR(FIND("#",X18)),FALSE(),TRUE())))
                    is_unret = "#" in serve1 if serve2 in [None, ""] else "#" in serve2

                    # isRallyWinner: =IF(W18="","",IF(ISERR(FIND("*",Y18)),FALSE(),TRUE()))
                    is_rally_winner = "*" in rally_part if rally_part else False
                    # isForced: =IF(W18="","",IF(ISERR(FIND("#",Y18)),FALSE(),TRUE())) 
                    is_forced = "#" in rally_part if rally_part else False
                    # isUnforced: =IF(W18="","",IF(ISERR(FIND("@",Y18)),FALSE(),TRUE()))
                    is_unforced = "@" in rally_part if rally_part else False
                    # isDouble: =IF(N18="","",IF(AND(S18=0,T18=0),TRUE(),FALSE()))
                    is_double = None if (first_in is None or second_in is None) else int(first_in == 0 and second_in == 0)                # rallyNoSpec: =SUBSTITUTE(SUBSTITUTE(SUBSTITUTE(SUBSTITUTE(SUBSTITUTE(SUBSTITUTE(SUBSTITUTE(Y18, "-", ""), "=", ""), "@", ""), "#", ""), "*", ""), ";", ""), "+", "")
                    rally_no_spec = rally_part.translate(str.maketrans("", "", "-=@#*;+")) if rally_part else None
                    # RallyNoError: =SUBSTITUTE(SUBSTITUTE(SUBSTITUTE(SUBSTITUTE(SUBSTITUTE(RALLY_NO_SPEC, "d", ""), "w", ""), "x", ""), "e", ""), "n", "")
                    rally_no_error = rally_no_spec.translate(str.maketrans("", "", "dwxen")) if rally_no_spec else None
                    # RallyNoDirection: =SUBSTITUTE(SUBSTITUTE(SUBSTITUTE(SUBSTITUTE(SUBSTITUTE(SUBSTITUTE(RALLY_NO_ERROR, "1", ""), "2", ""), "3", ""), "7", ""), "8", ""), "9", "")
                    rally_no_direction = rally_no_error.translate(str.maketrans("", "", "123789")) if rally_no_error else None
                    # RallyLen: =IF(N18="","",LEN(RALLY_NO_DIRECTION))
                    rally_len = None if rally_no_direction is None else len(rally_no_direction)

                    # PointWinner: =IF(OR(N18="P",N18="R"),L18,IF(OR(N18="Q",N18="S"),K18,IF(AND(Y18="",OR(Z18=FALSE(),Z18=""),OR(AA18=FALSE(),AA18=""),OR(AE18=FALSE(),AE18="")),"",IF(OR(Z18=TRUE(),AA18=TRUE(),AND((MOD(AI18,2)=0),AB18=TRUE()),AND((MOD(AI18,2)=1),OR(AC18=TRUE(),AD18=TRUE()))),K18,L18))))
                    server = int(point["server_player_number"])
                    returner = 2 if server == 1 else 1
                    first_code = point.get("first_serve_rally")
                    if first_code in ["P", "R"]:
                        point_winner = "server"
                    elif first_code in ["Q", "S"]:
                        point_winner = "returner"
                    else:
                        winner = int(point["point_winner_player_number"])

                        if winner not in (server, returner):
                            raise ValueError(f"Invalid point_winner_player_number: {point}")
                            quit()

                        point_winner = "server" if winner == server else "returner"

                    # isServerWinner: =IF(AJ18="","",IF(AJ18=K18,1,0))
                    if point_winner is None:
                        raise ValueError(f"Expected point winner to be defined: {point}")
                        quit()
                    else:
                        is_server_winner = 1 if point_winner == "server" else 0

                    # PointsAfter: =IF(POINT_WINNER="","",IF(IS_TIEBREAKER_POINT=0,IF(IS_SERVER_WINNER=1,VLOOKUP(GAME_SCORE,$Tables.P1_NAME:PLAYER_2_SET_SCORE,2,FALSE()),VLOOKUP(GAME_SCORE,$Tables.PLAYER_1_NAME:PLAYER_2_SET_SCORE,3,FALSE())),IF(IS_SERVER_WINNER=1,VLOOKUP(GAME_SCORE,$Tables.IS_TIEBREAKER_SET:IS_TIEBREAKER_POINT,2,FALSE()),VLOOKUP(GAME_SCORE,$Tables.IS_TIEBREAKER_SET:IS_TIEBREAKER_POINT,3,FALSE()))))
                  
                    result = {
                      "match_id": point.get("match_id"),
                      "match_date": point.get("match_date"),
                      "surface": charted_matches_by_id[point["match_id"]].get("surface"),
                      "match_duration": charted_matches_by_id[point["match_id"]].get("time"),
                      "level": charted_matches_by_id[point["match_id"]].get("level"),
                      "player_1_id": charted_matches_by_id[point["match_id"]].get("player_1_id"),
                      "player_2_id": charted_matches_by_id[point["match_id"]].get("player_2_id"),
                      "player_1_hand": charted_matches_by_id[point["match_id"]].get("player_1_hand"),
                      "player_2_hand": charted_matches_by_id[point["match_id"]].get("player_2_hand"),
                      "player_1_rank": charted_matches_by_id[point["match_id"]].get("player_1_rank"),
                      "player_1_seed": charted_matches_by_id[point["match_id"]].get("player_1_seed"),
                      "player_1_entry": charted_matches_by_id[point["match_id"]].get("player_1_entry"),
                      "player_2_rank": charted_matches_by_id[point["match_id"]].get("player_2_rank"),
                      "player_2_seed": charted_matches_by_id[point["match_id"]].get("player_2_seed"),
                      "player_2_entry": charted_matches_by_id[point["match_id"]].get("player_2_entry"),
                      "point_number": point.get("point_number"),
                      "set_1": point.get("set_1"),
                      "set_2": point.get("set_2"),
                      "game_1": point.get("game_1"),
                      "game_2": point.get("game_2"),
                      "game_score": point.get("game_score"),
                      "game_number": point.get("game_number"),
                      "is_tiebreaker_set": tb_set,
                      "tb_point_number": point.get("tb_point_number"),
                      "tb_point": point.get("tb_point_flag"),
                      "server_player_number": point.get("server_player_number"),
                      "first_serve_rally": point.get("first_serve_rally"),
                      "second_serve_rally": point.get("second_serve_rally"),
                      "point_winner_player_number": point.get("point_winner_player_number"),
                      "point_winner": point_winner,
                      "is_server_winner": is_server_winner,
                      # "1stNoLet": first_no_let,
                      # "2ndNoLet": second_no_let,
                      "first_serve_in_play": first_in,
                      "second_serve_in_play": second_in,
                      #"isRally1st": is_rally_first,
                      #"isRally2nd": is_rally_second,
                      #"serve1": serve1,
                      #"serve2": serve2,
                      "rally": rally_part,
                      "is_ace": "*" in serve1 if serve2 in [None, ""] else "*" in serve2,
                      "is_unret": is_unret,
                      "is_rally_winner": is_rally_winner,
                      "is_forced_error": is_forced,
                      "is_unforced_error": is_unforced,
                      "is_double": is_double,
                      #"rally_no_spec": rally_no_spec,
                      #"rally_no_error": rally_no_error,
                      #"rally_no_direction": rally_no_direction,
                      "rally_length": rally_len,
                      "gender": charted_matches_by_id[point["match_id"]].get("gender")
                    }
                    f.write(json.dumps(result, ensure_ascii=False) + "\n")

                    prev_point = point
                    prev_result = result
                    count_points += 1
                    points[point["match_id"]].append(result)
                    #if result not in all_points:
                    #    all_points.append(result)
        return points, count_points

def assign_case(score_state, server, point_winner, p1_server=True):

    p1_wins = (point_winner == "server" and p1_server) or \
              (point_winner == "returner" and not p1_server)

    p1_loses = not p1_wins

    # CASE 3: draws
    if score_state in ["0-0", "15-15", "30-30", "40-40"]:
        return "CASE_3"

    # CASE 1
    if (p1_loses and p1_server) or (p1_wins and not p1_server):
        return "CASE_1"

    # CASE 2
    if (p1_wins and p1_server) or (p1_loses and not p1_server):
        return "CASE_2"

    return None


"""
def compute_serve_rally_counts(df):
    df_new = df.copy()

    def is_serve_in(series):
        \"""
        Vectorized version:
        Returns:
            1 if serve is in
            0 if serve is out
            NaN if undefined
        \"""
        cond_valid = series.notna() & (series.str.len() > 1)
        second_char = series.str[1]
        is_in = (~second_char.isin(list("wdnxgeVPQRS"))).astype(float)
        is_in = is_in.where(cond_valid, other=np.nan)
        return is_in

    # Clean rally patterns
    df_new["first_clean"] = (df["first_serve_rally"].fillna("").str.replace(r"\)\*", "0*", regex=True).str.replace(r"&\*", "0*", regex=True).str.replace(r"\?", "0", regex=True))
    df_new["second_clean"] = (df["second_serve_rally"].fillna("").str.replace(r"\)\*", "0*", regex=True).str.replace(r"&\*", "0*", regex=True).str.replace(r"\?", "0", regex=True))

    # remove lets ("c")
    df_new["first_no_lets"] = df_new["first_clean"].str.replace("c", "", regex=False)
    df_new["second_no_lets"] = df_new["second_clean"].str.replace("c", "", regex=False)

    # Serve in/out
    df_new["first_in"] = is_serve_in(df_new["first_no_lets"])
    df_new["second_in"] = is_serve_in(df_new["second_no_lets"])

    # Rally detection
    df_new["is_rally_first"] = np.where(df_new["first_in"] == 0, 0, (df_new["first_no_lets"].str.len() > 2).astype(int))
    df_new["is_rally_second"] = np.where(df_new["second_in"] == 0, 0, (df_new["second_no_lets"].str.len() > 2).astype(int))

    # Extract serve outcomes
    df_new["serve1"] = np.where(df_new["is_rally_first"] == 0, df_new["first_no_lets"], df_new["first_no_lets"].str[0])
    df_new["serve2"] = np.where(df_new["is_rally_second"] == 0, df_new["second_no_lets"], df_new["second_no_lets"].str[0])
    df_new["rally_part"] = np.where(df_new["is_rally_first"] == 1, df_new["first_no_lets"].str[1:], np.where(df_new["is_rally_second"] == 1, df_new["second_no_lets"].str[1:], None))

    # Outcome flags (vectorized)
    df_new["is_rally_winner"] = df_new["rally_part"].str.contains(r"\*", na=False)
    df_new["is_forced_error"] = df_new["rally_part"].str.contains(r"#", na=False)
    df_new["is_unforced_error"] = df_new["rally_part"].str.contains(r"@", na=False)

    # double fault
    df_new["is_double"] = ((df_new["first_in"] == 0) & (df_new["second_in"] == 0)).astype(float)
    df_new["rally_no_spec"] = df_new["rally_part"].str.replace(r"[-=@#*;+]", "", regex=True)
    df_new["rally_no_error"] = df_new["rally_no_spec"].str.replace(r"[dwxen]", "", regex=True)
    df_new["rally_no_direction"] = df_new["rally_no_error"].str.replace(r"[123789]", "", regex=True)
    df_new["rally_len"] = df_new["rally_no_direction"].str.len().fillna(0)
    rally_counts = []
    rally_parts = []
    is_doubles = []
    for i, row in df_new.iterrows():
        w = row.get("serve1", "")
        y = row.get("rally_part", "")
        ai = row.get("rally_len", np.nan)  # THIS is critical (previous value)
        is_double = bool(row.get("is_double", False))

        rally_parts.append(y)
        is_doubles.append(is_double)
        # 1. blank serve1 server sequence
        if pd.isna(w) or w == "":
            rally_counts.append(np.nan)
            continue
        # 2. terminal rally
        if isinstance(y, str) and y.endswith(("@", "#")):
            rally_counts.append(ai)
            continue
        # 3. double fault
        if is_double:
            rally_counts.append(0)
            continue
        # 4. default
        if pd.isna(ai):
            rally_counts.append(np.nan)
        else:
            rally_counts.append(ai + 1)
    df["rally_count"] = rally_counts
    df["rally_count"] = df["rally_count"].fillna(0)
    df["rally"] = rally_parts
    df["rally"] = df["rally"].fillna("")
    df["is_double"] = is_doubles
    return df
"""