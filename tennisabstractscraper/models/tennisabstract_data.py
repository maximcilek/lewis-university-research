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