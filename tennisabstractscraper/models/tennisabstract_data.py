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

normal_score_table = {
    "0-0": {"server": "15-0", "returner": "0-15"},
    "15-0": {"server": "30-0", "returner": "15-15"},
    "30-0": {"server": "40-0", "returner": "30-15"},
    "40-0": {"server": "G-0", "returner": "40-15"},
    "40-15": {"server": "G-15", "returner": "40-30"},
    "40-30": {"server": "G-30", "returner": "40-40"},
    "40-40": {"server": "Ad-40", "returner": "40-Ad"},
    "Ad-40": {"server": "G", "returner": "40-40"},
    "40-Ad": {"server": "40-40", "returner": "G"},
}

tiebreak_score_table = {}

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
        logger.info("Loading players from file: %s", self.players_file_path)
        try:
            obj = data_objects.DataObjectFactory.create(self.players_file_path)
            if isinstance(obj, data_objects.ParquetDataObject):
                parquet_file = pq.ParquetFile(self.players_file_path)
                total_rows = parquet_file.metadata.num_rows
                logger.info("Successfully loaded %d players (streaming)", total_rows)
            else:
                logger.info("Successfully loaded %d players", len(obj.data))
            return obj
        except Exception as e:
            logger.exception("Failed to load players: %s", e)
            raise
    
    def _load_charting_matches(self) -> T:
        logger.info("Loading charting matches from file: %s", self.charting_matches_file_path)
        try:
            obj = data_objects.DataObjectFactory.create(self.charting_matches_file_path)
            if isinstance(obj, data_objects.ParquetDataObject):
                parquet_file = pq.ParquetFile(self.charting_matches_file_path)
                total_rows = parquet_file.metadata.num_rows
                logger.info("Charting matches ready for streaming (%d rows)", total_rows)
            else:
                logger.info("Successfully loaded %d matches", len(obj.data))
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
    
    """def _parse_serve(self, serve_code):
        \"""
        Parses a serve code like '6*', '4n', '5+', 'S', 'R', 'P', 'Q'.
        Returns a dict following the JSON schema for a shot.
        \"""
        if not serve_code:
            return None
        
        serve = {"player": "server", "shot_type": "serve", "result": "normal"}
        
        # Edge cases
        if serve_code in ["S", "R", "P", "Q"]:
            serve["shot_type"] = serve_code
            serve["result"] = "normal"
            return serve
        
        # Direction
        if serve_code[0] in "0456":
            serve["direction"] = serve_code[0]
            remainder = serve_code[1:]
        else:
            serve["direction"] = "0"
            remainder = serve_code
        
        # Check for modifiers +, *, #, @
        serve["modifiers"] = []
        serve["forced"] = None
        serve["error_type"] = None
        
        for c in remainder:
            if c == "+":
                serve["modifiers"].append("+")
            elif c == "*":
                serve["result"] = "winner"
            elif c == "#":
                serve["result"] = "error"
                serve["forced"] = True
            elif c == "@":
                serve["result"] = "error"
                serve["forced"] = False
            elif c in "nwdxg!Ve":
                serve["error_type"] = c
        
        return serve"""

    def _parse_serve(self, serve_code: str, serve_code_2: str, point: dict) -> dict:
        """
        Parses a single serve code into a structured dictionary.
        Handles direction, faults, modifiers, and point-ending symbols (ace, unreturnable, unforced error).
        """
        serve = {
            "player": "server",
            "shot_type": "serve",
            "result": "normal",
            "direction": "0",
            "modifiers": [],
            "forced": None,
            "error_type": None
        }

        shots = []
        shot = {}
        serve_pattern = []
        c = 0
        char = serve_code[c]
        while c < len(serve_code) and serve_code[c].lower() == "c":
            serve_pattern.append("let")
            c += 1

        modifiers = serve_code[c:]
        # print(f"Original = {serve_code} | After = {modifiers}")
        has_direction = False
        for m in modifiers:
            if m.isdigit() and not has_direction:
                serve_pattern.append({"direction": int(m)})
                has_direction = True
            elif m.isdigit() and has_direction == True:
                print(f"Already Has Direction: {point}")
                quit()
            else:
                if m == "f":
                    serve_pattern.append({"shot_type": "forehand"})
                elif m == "x":
                    serve_pattern.append({"depth": "wide_and_deep"})
                elif m == "w":
                    serve_pattern.append({"shot_depth": "wide"})
                elif m == "n":
                    serve_pattern.append({"fault_type": "net"})
                elif m == "e":
                    serve_pattern.append({"fault_type": "unknown"})
                elif m == ";":
                    serve_pattern.append({"extras": "clipped_net_cord"})
        print(f"{point['first_serve_rally']} - {serve_pattern}")
                # quit()
        #if len(serve_code) > 5 and (point["notes"] is not None and ("challenge" in point["notes"] or "replay" in point["notes"])):
        #    pass
            # print(serve_code, serve_code_2, point)
        #else:
        #    print(serve_code)

        #if "*" in serve_code[:4] and len(serve_code) > 4: # "*" in serve_code and serve_code[-1] != "*":
        #    print(f"Serve: {serve_code}")
        #    return {"result":"ace"}

        # for count, char in enumerate(serve_code):
        #     if char.isdigit():
        #         num = int(char)
        #         if count == 0:
        #             shot["serve_direction"] = num
        #     else:
        #         if len(serve_code) < 4:
        #             print("Error", serve_code)

        # if serve_code[0].isdigit():
        #     num = int(serve_code[0])
        #     if num == 0:
        #         print(f"Rally: {serve_code}")
        #         quit()
        #     return int(serve_code[0])
        # else:
        #     print(f"Rally: {serve_code}")
        #     return serve

        # Special cases: server wins or penalties
        #if serve_code in ["S", "R", "P", "Q"]:
        #    serve["shot_type"] = serve_code
        #    return serve

        """# Extract direction if present
        if serve_code and serve_code[0] in ["0", "4", "5", "6"]:
            serve["direction"] = serve_code[0]

        # Detect point-ending symbols
        if "*" in serve_code:
            serve["result"] = "ace"
            serve_code = serve_code.replace("*", "")
        elif "#" in serve_code:
            serve["result"] = "unreturnable"
            serve_code = serve_code.replace("#", "")
        elif "@" in serve_code:
            serve["result"] = "unforced_error"
            serve_code = serve_code.replace("@", "")

        # Detect optional modifiers (serve-and-volley)
        if "+" in serve_code:
            serve["modifiers"].append("serve_and_volley")
            serve_code = serve_code.replace("+", "")

        # Detect faults
        faults = {"n", "w", "d", "x", "g", "e", "!"}
        for f in faults:
            if f in serve_code:
                serve["error_type"] = f
                break  # only one fault type per serve"""

        return serve

    def _is_serve_in(self, serve_code: str) -> bool:
        """
        Determines if the serve is considered "in" based on the serve code.

        Serve codes:
        - 4, 5, 6 => valid serves in wide/body/T
        - c => let (replay, serve not counted as in yet)
        - lowercase letters n, w, d, x, g, e => faults
        - !, V => shank or time violation (faults)
        - + => serve-and-volley attempt (does not affect "in" status)

        Args:
            serve_code (str): The code for the serve, e.g., "6", "5d", "cc4", "4+"

        Returns:
            bool: True if the serve is in, False if it was a fault
        """
        if not serve_code:
            return False

        # Remove all let ('c') prefixes
        serve_code = serve_code.lstrip('c')

        # Remove optional serve-and-volley '+'
        serve_code = serve_code.replace('+', '')

        if not serve_code:
            # Only lets remain
            return False

        # First character determines the main serve type
        first_char = serve_code[0]

        # In serves are digits 4,5,6
        return first_char in {'1', '2', '3', '4', '5', '6', '7', '9'}
    
    def load_points(self):
        unums = []
        for count, batch in enumerate(self.data_object):
            for point in batch:
                shots = []
                first = point.get("first_serve_rally").replace(")*", "0*").replace("&*", "0*").replace("?", "0")
                second = point.get("second_serve_rally")

                first_no_let = first.replace("c", "")
                second_no_let = second.replace("c", "")

                if point.get("tiebreaker_set") == "t":
                    tb_set = 1
                elif point.get("tiebreaker_set") == "f":
                    tb_set = 0
                else:
                    tb_set = None
                # tb_set = 1 if point.get("tiebreaker_set") == "t" or (point.get("game_1") + point.get("game_2") + 1) < BEST_OF else 0
                tb_point_flag = 1 if point.get("game_1") == 6 and point.get("game_2") == 6 and tb_set == 1 else 0
                if tb_point_flag:
                    if point_score == "0-0":
                        tb_point_number = 1
                    else:
                        tb_point_number = prev_tb_point_number + 1
                    prev_tb_point_number = tb_point_number
                else:
                    tb_point_number = None
                    prev_tb_point_number = 0  # reset for next tiebreak

                # 1st Rally In
                """
                =IF(N18="","",IF(LEN(N18)=1,"",IF(ISERROR(FIND(MID(Q18,2,1),"wdnxgeVPQRS"))=TRUE(),1,0)))
                """
                if not first_no_let or len(first_no_let) == 1:
                    first_in = None
                else:
                    first_in = 1 if first_no_let[1] not in "wdnxgeVPQRS" else 0
                
                # 2nd Rally In
                """
                =IF(O18="","",IF(ISERROR(FIND(MID(R18,2,1),"wdnxgeVPQRS"))=TRUE(),1,0))
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
                """
                =IF(OR(N18="P",N18="R"),L18,IF(OR(N18="Q",N18="S"),K18,IF(AND(Y18="",OR(Z18=FALSE(),Z18=""),OR(AA18=FALSE(),AA18=""),OR(AE18=FALSE(),AE18="")),"",IF(OR(Z18=TRUE(),AA18=TRUE(),AND((MOD(AI18,2)=0),AB18=TRUE()),AND((MOD(AI18,2)=1),OR(AC18=TRUE(),AD18=TRUE()))),K18,L18))))
                """
                first_code = point.get("first_serve_rally")
                if first_code in ["P", "R"]:
                    point_winner = "server"
                elif first_code in ["Q", "S"]:
                    point_winner = "returner"
                elif rally_part is None and not any([is_ace, is_unret, is_rally_winner, is_forced, is_unforced]):
                    point_winner = None
                else:
                    if (
                        is_ace
                        or is_unret
                        or (rally_len is not None and rally_len % 2 == 0 and is_rally_winner)
                        or (rally_len is not None and rally_len % 2 == 1 and (is_forced or is_unforced))
                    ):
                        point_winner = "server"
                    else:
                        point_winner = "returner"

                # isServerWinner
                """
                =IF(AJ18="","",IF(AJ18=K18,1,0))
                """
                if point_winner is None:
                    is_server_winner = None
                else:
                    is_server_winner = 1 if point_winner == "server" else 0

                # PointsAfter
                """
                =IF(AJ18="","",IF(I18=0,IF(AK18=1,VLOOKUP(F18,$Tables.A$1:C$18,2,FALSE()),VLOOKUP(F18,$Tables.A$1:C$18,3,FALSE())),IF(AK18=1,VLOOKUP(F18,$Tables.H$1:J$95,2,FALSE()),VLOOKUP(F18,$Tables.H$1:J$95,3,FALSE()))))
                """
                
                """current_score = point.get("game_score")   # F18
                tiebreak = point.get("tiebreaker_set")   # I18 (likely 0/1 or "t"/"f")

                # normalize tiebreak
                is_tiebreak = str(tiebreak).lower() in ["1", "t", "true"]

                if point_winner is None:
                    points_after = None

                else:
                    # choose correct table
                    table = tiebreak_score_table if is_tiebreak else normal_score_table

                    # choose column
                    if is_server_winner == 1:
                        points_after = table.get(current_score, {}).get("server")
                    else:
                        points_after = table.get(current_score, {}).get("returner")"""

                result = {
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
                  "points_after": points_after,
                  "tb_set": tb_set,
                  "tb_point": tb_point_flag,
                  "tb_point_number": tb_point_number,
                }

                if tb_point_flag == 1: # count > 10:
                    print(result)
                    quit()