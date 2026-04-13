# tennisabstractscraper/models/tennisabstract_data.py

import dataclasses
from . import data_objects
import logging
import typing
import re
import json
import pyarrow.parquet as pq

logger = logging.getLogger(__name__)

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
    def load_points(self, charted_matches_by_id):
        count_points = 0
        skipped = 0
        prev_point = {}
        prev_result = {}
        points = {}
        all_points = []
        for count, batch in enumerate(self.data_object):
            for point in batch:
                if not (charted_matches_by_id[point.get("match_id")].get("best_of")) or point.get("tiebreaker_set") in [None, ""]:
                    skipped += 1
                    continue

                if point["match_id"] not in points:
                    points[point["match_id"]] = []
                
                shots = []
                first = point.get("first_serve_rally").replace(")*", "0*").replace("&*", "0*").replace("?", "0")
                second = point.get("second_serve_rally")

                first_no_let = first.replace("c", "")
                second_no_let = second.replace("c", "")

                if point.get("game_1") in [None, ""]:
                    point["game_1"] = prev_point["game_1"]
                if point.get("game_2") in [None, ""]:
                    point["game_2"] = prev_point["game_2"]

                if point.get("tiebreaker_set") == "t":
                    tb_set = 1
                elif point.get("tiebreaker_set") == "f":
                    tb_set = 0
                else:
                    tb_set = None
                    raise ValueError("Unexpected tiebreaker_set value, expected 't' or 'f' but got '%s': %s", point.get("tiebreaker_set"), point)

                # "20191124-M-Davis_Cup_Finals-F-Rafael_Nadal-Denis_Shapovalov"
                tb_point_flag = 1 if int(point.get("game_1")) == 6 and int(point.get("game_2")) == 6 and tb_set == 1 else 0
                # tb_active = (tb_set == 1 and int(point["game_1"]) == 6 and int(point["game_2"]) == 6)
                if tb_point_flag == 1:
                    if point["game_score"] == "0-0":
                        tb_point_number = 1
                    else:
                        tb_point_number = prev_result["tb_point_number"] + 1
                    prev_result["tb_point_number"] = tb_point_number
                else:
                    tb_point_number = 0
                    prev_result["tb_point_number"] = 0

                # 1st Rally In
                """
                =IF(N18="","",IF(LEN(FIRST_SERVE_RALLY_PATTERN)=1,"",IF(ISERROR(FIND(MID(FIRST_SERVE_RALLY_PATTERN_NO_LETS,2,1),"wdnxgeVPQRS"))=TRUE(),1,0)))
                """
                if not first_no_let or len(first_no_let) == 1:
                    first_in = None
                else:
                    first_in = 1 if first_no_let[1] not in "wdnxgeVPQRS" else 0
                
                # 2nd Rally In
                """
                =IF(SECOND_SERVE_RALLY_PATTERN="","",IF(ISERROR(FIND(MID(SECOND_SERVE_RALLY_PATTERN_NO_LETS,2,1),"wdnxgeVPQRS"))=TRUE(),1,0))
                """
                if not second_no_let or len(second_no_let) == 1:
                    second_in = None
                else:
                    second_in = 1 if second_no_let[1] not in "wdnxgeVPQRS" else 0
                
                
                # IsRally1st
                """
                =IF(N18="","",IF(S18=0,0,IF(LEN(Q18)>2,1,0)))
                """
                if first_in and first_in == 0:
                    is_rally_first = 0
                else:
                    is_rally_first = 1 if len(first_no_let) > 2 else 0

                # IsRally2nd
                """
                =IF(N18="","",IF(T18=0,0,IF(LEN(R18)>2,1,0)))
                """
                if second_in and second_in == 0:
                    is_rally_second = 0
                else:
                    is_rally_second = 1 if len(second_no_let) > 2 else 0

                # Serve1
                """
                =IF(N18="","",IF(U18=0,Q18,LEFT(Q18,1)))
                """
                if is_rally_first == 0:
                  serve1 = first_no_let
                else:
                  serve1 = first_no_let[0]
                
                # Serve2
                """
                =IF(N18="","",IF(V18=0,R18,LEFT(R18,1)))
                """
                if is_rally_second == 0:
                  serve2 = second_no_let
                else:
                  serve2 = second_no_let[0]

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

                # isAce
                """
                =IF(N18="","",IF(U18=1,RIGHT(Q18,(LEN(Q18)-1)),IF(V18=1,RIGHT(R18,(LEN(R18)-1)),"")))
                """
                if serve2 in [None, ""]:
                    is_ace = "*" in serve1
                else:
                    is_ace = "*" in serve2

                # isUnret
                """
                =IF(W18="","",OR(IF(ISERR(FIND("#",W18)),FALSE(),TRUE()), IF(ISERR(FIND("#",X18)),FALSE(),TRUE())))
                """
                if serve2 in [None, ""]:
                    is_unret = "#" in serve1
                else:
                    is_unret = "#" in serve2

                # isRallyWinner
                """
                =IF(W18="","",IF(ISERR(FIND("*",Y18)),FALSE(),TRUE()))
                """
                is_rally_winner = "*" in rally_part if rally_part else False

                # isForced
                """
                =IF(W18="","",IF(ISERR(FIND("#",Y18)),FALSE(),TRUE()))
                """
                is_forced = "#" in rally_part if rally_part else False

                # isUnforced
                """
                =IF(W18="","",IF(ISERR(FIND("@",Y18)),FALSE(),TRUE()))
                """
                is_unforced = "@" in rally_part if rally_part else False

                # isDouble
                """
                =IF(N18="","",IF(AND(S18=0,T18=0),TRUE(),FALSE()))
                """
                if first_in is None or second_in is None:
                    is_double = None
                else:
                    is_double = (first_in == 0 and second_in == 0)

                # rallyNoSpec
                """
                =SUBSTITUTE(SUBSTITUTE(SUBSTITUTE(SUBSTITUTE(SUBSTITUTE(SUBSTITUTE(SUBSTITUTE(Y18, "-", ""), "=", ""), "@", ""), "#", ""), "*", ""), ";", ""), "+", "")
                """
                if rally_part:
                    remove_chars = "-=@#*;+"
                    rally_no_spec = rally_part.translate(str.maketrans("", "", remove_chars))
                else:
                    rally_no_spec = None

                # RallyNoError
                """
                =SUBSTITUTE(SUBSTITUTE(SUBSTITUTE(SUBSTITUTE(SUBSTITUTE(RALLY_NO_SPEC, "d", ""), "w", ""), "x", ""), "e", ""), "n", "")
                """
                if rally_no_spec:
                    remove_error_chars = "dwxen"
                    rally_no_error = rally_no_spec.translate(
                        str.maketrans("", "", remove_error_chars)
                    )
                else:
                    rally_no_error = None

                # RallyNoDirection
                """
                =SUBSTITUTE(SUBSTITUTE(SUBSTITUTE(SUBSTITUTE(SUBSTITUTE(SUBSTITUTE(RALLY_NO_ERROR, "1", ""), "2", ""), "3", ""), "7", ""), "8", ""), "9", "")
                """
                if rally_no_error:
                    remove_direction_chars = "123789"
                    rally_no_direction = rally_no_error.translate(
                        str.maketrans("", "", remove_direction_chars)
                    )
                else:
                    rally_no_direction = None

                # RallyLen
                """
                =IF(N18="","",LEN(RALLY_NO_DIRECTION))
                """
                if rally_no_direction is None:
                    rally_len = None
                else:
                    rally_len = len(rally_no_direction)

                # PointWinner
                if int(point.get("server_player_number")) == 1:
                    server_player_number = 1
                    returner_player_number = 2
                elif int(point.get("server_player_number")) == 2:
                    server_player_number = 2
                    returner_player_number = 1
                else:
                    raise ValueError("Expected server_player_number to be non-empty: %s", point)
                    quit()
                """
                =IF(OR(N18="P",N18="R"),L18,IF(OR(N18="Q",N18="S"),K18,IF(AND(Y18="",OR(Z18=FALSE(),Z18=""),OR(AA18=FALSE(),AA18=""),OR(AE18=FALSE(),AE18="")),"",IF(OR(Z18=TRUE(),AA18=TRUE(),AND((MOD(AI18,2)=0),AB18=TRUE()),AND((MOD(AI18,2)=1),OR(AC18=TRUE(),AD18=TRUE()))),K18,L18))))
                """
                first_code = point.get("first_serve_rally")
                if first_code in ["P", "R"]:
                    point_winner = "server"
                elif first_code in ["Q", "S"]:
                    point_winner = "returner"
                else:
                    if int(point.get("point_winner_player_number")) == server_player_number:
                        point_winner = "server"
                    elif int(point.get("point_winner_player_number")) == returner_player_number:
                        point_winner = "returner"
                    else:
                        print(server_player_number, returner_player_number, point.get("point_winner_player_number"))
                        raise ValueError(f"Expected point_winner_player_number to be non-empty: {point}")
                        quit()

                # isServerWinner
                """
                =IF(AJ18="","",IF(AJ18=K18,1,0))
                """
                if point_winner is None:
                    raise ValueError(f"Expected point winner to be defined: {point}")
                    quit()
                else:
                    is_server_winner = 1 if point_winner == "server" else 0

                # PointsAfter
                """
                =IF(POINT_WINNER="","",IF(IS_TIEBREAKER_POINT=0,IF(IS_SERVER_WINNER=1,VLOOKUP(GAME_SCORE,$Tables.P1_NAME:PLAYER_2_SET_SCORE,2,FALSE()),VLOOKUP(GAME_SCORE,$Tables.PLAYER_1_NAME:PLAYER_2_SET_SCORE,3,FALSE())),IF(IS_SERVER_WINNER=1,VLOOKUP(GAME_SCORE,$Tables.IS_TIEBREAKER_SET:IS_TIEBREAKER_POINT,2,FALSE()),VLOOKUP(GAME_SCORE,$Tables.IS_TIEBREAKER_SET:IS_TIEBREAKER_POINT,3,FALSE()))))
                """

                current_score = point.get("game_score")
                if current_score not in unique_scores:
                    unique_scores.append(current_score)
                
                # current_scores = current_score.split("-")
                # p1 = parse_score(current_scores[1])
                # p2 = parse_score(current_scores[0])

                result = {
                  "match_id": point.get("match_id"),
                  "point_number": point.get("point_number"),
                  "set_1": point.get("set_1"),
                  "set_2": point.get("set_2"),
                  "game_1": point.get("game_1"),
                  "game_2": point.get("game_2"),
                  "game_score": point.get("game_score"),
                  "game_number": point.get("game_number"),
                  "is_tiebreaker_set": point.get("is_tiebreaker_set"),
                  "server_player_number": point.get("server_player_number"),
                  "first_serve_rally": point.get("first_serve_rally"),
                  "second_serve_rally": point.get("second_serve_rally"),
                  "point_winner_player_number": point.get("point_winner_player_number"),
                  
                  
                  "1stNoLet": first_no_let,
                  "2ndNoLet": second_no_let,
                  "1stIn": first_in,
                  "2ndIn": second_in,
                  "isRally1st": is_rally_first,
                  "isRally2nd": is_rally_second,
                  "serve1": serve1,
                  "serve2": serve2,
                  "rally": rally_part,
                  "is_ace": is_ace,
                  "is_unret": is_unret,
                  "is_rally_winner": is_rally_winner,
                  "is_forced_error": is_forced,
                  "is_unforced_error": is_unforced,
                  "is_double": is_double,
                  "rally_no_spec": rally_no_spec,
                  "rally_no_error": rally_no_error,
                  "rally_no_direction": rally_no_direction,
                  "rally_length": rally_len,
                  "point_winner": point_winner,
                  "is_server_winner": is_server_winner,
                  "tb_set": tb_set,
                  "tb_point": tb_point_flag,
                  "tb_point_number": tb_point_number,
                  "player_1_id": charted_matches_by_id[point["match_id"]].get("player_1_id"),
                  "player_2_id": charted_matches_by_id[point["match_id"]].get("player_2_id"),
                  "gender": charted_matches_by_id[point["match_id"]].get("gender")
                }

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