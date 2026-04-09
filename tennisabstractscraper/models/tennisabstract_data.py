# tennisabstractscraper/models/tennisabstract_data.py

import dataclasses
from . import data_objects
import logging
import typing
import json
import pyarrow.parquet as pq

logger = logging.getLogger(__name__)

T = typing.TypeVar("T")

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

    def _parse_serve(self, serve_code: str) -> dict:
        """
        Parses a single serve code into a structured dictionary.
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

        # Special cases like server wins or penalties
        if serve_code in ["S", "R", "P", "Q"]:
            serve["shot_type"] = serve_code
            return serve

        # Direction codes
        if serve_code[0] in ["4", "5", "6", "0"]:
            serve["direction"] = serve_code[0]

        # Outcome symbols
        if "*" in serve_code:
            serve["result"] = "ace"
            print(f"Found Ace")
            quit()
        if "#" in serve_code:
            serve["result"] = "unreturnable"
        if "@" in serve_code:
            serve["result"] = "unforced_error"

        # Optional modifiers like serve-and-volley
        if "+" in serve_code:
            serve["modifiers"].append("+")

        # Check for faults
        faults = {"n", "w", "d", "x", "g", "e", "!"}
        for f in faults:
            if f in serve_code:
                serve["error_type"] = f

        return serve  
    def load_points(self):
        for count, batch in enumerate(self.data_object):
            for point in batch:
                shots = []
                first = point.get("first_serve_rally")
                second = point.get("second_serve_rally")
                
                result = {"first_serve": None, "second_serve": None, "rally": [], "ending": None, "winner": None}

                serve_shot = self._parse_serve(first[0])  # first character usually direction/fault
                # print(serve_shot)
                if "*" in first: # serve_shot["result"] != "normal" or serve_shot["error_type"] is not None or serve_shot["forced"] is not None:
                    print(first)
                    # quit()
                # quit()
                # --- Handle special cases ---
                # check_list = [c for c in first if c in [i.get("code") for i in self.rally_codes["point_codes"]]]
                """point_codes = [item for item in self.rally_codes["point_codes"] if item.get("code") in first]
                if point_codes != []:
                    if len(first) != 1 or len(point_codes) != 1:
                        logger.exception("Unexpected point_code, got: %s", first)
                        raise
                    
                    decoded_point_code = point_codes[0]
                    if decoded_point_code.get("code") in ["S", "Q"]:
                        result["winner"] = "server"
                    elif decoded_point_code.get("code") in ["R", "P"]:
                        result["winner"] = "returner"
                    result["reason"] = decoded_point_code.get("description")


                    print(point_codes[0], first, len(first))
                    quit()"""