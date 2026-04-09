# tennisabstractscraper/models/data_objects.py

from __future__ import absolute_import

__author__ = "maximcilek@gmail.com (Maxim Cilek)"

import abc
import csv
import dataclasses
import json
import logging
import pathlib
import typing
import pyarrow.parquet as pq
import pyarrow as pa

logger = logging.getLogger(__name__)
T = typing.TypeVar("T")  # Generic type for items loaded by the loader
STREAM_THRESHOLD = 100 * 1024 * 1024  # 100 MB

@dataclasses.dataclass
class AbstractDataObject(abc.ABC, typing.Generic[T]):
    """
    Abstract base class for all data loaders. Enforces a consistent interface for loading data from files.
    """
    _file_path: str | pathlib.Path
    _data: T = dataclasses.field(default=None, init=False, repr=False)

    def __post_init__(self):
        self._file_path = pathlib.Path(self._file_path)  # ensure Path object
        if not self._file_path.is_file():
            raise FileNotFoundError(f"{self.__class__.__name__}: file_path must exist and be a valid file path, got {self._file_path!r}")
    
    @property
    def file_path(self) -> pathlib.Path: return self._file_path

    @property
    def data(self) -> T:
        if self._data is None:
            logger.debug("Data not cached, loading into memory: %s", self.file_path)
            self._data = self._load()
        return self._data
    
    # @abc.abstractmethod
    # def _load(self) -> T:
    #     ...
    
    def __iter__(self) -> typing.Iterator:
        """Optional: provide iterator if T supports iteration."""
        if hasattr(self.data, "__iter__"):
            return iter(self.data)
        raise TypeError(f"{type(self).__name__}.{type(self).data.fset.__name__} is not iterable")
    
    def __len__(self) -> int:
        if hasattr(self.data, "__len__"):
            return len(self.data)
        raise TypeError(f"{type(self).__name__}.data has no len()")

class AbstractDataObjectStream(AbstractDataObject[typing.Iterator[T]], abc.ABC):
    """
    Abstract base class for data objects that support streaming iteration.
    Subclasses must implement `_stream()` instead of `_load()`.
    """
    _batch_size: int = 10
    
    @property
    def batch_size(self) -> int:
        return self._batch_size
    @property
    def data(self) -> typing.Iterator[T]:
        return self.__iter__()
    @abc.abstractmethod
    def __iter__(self) -> typing.Iterator[T]:
        ...

class JsonDataObject(AbstractDataObject[T]):
    """
    Loads data from a standard JSON (.json) file. Supports dict or list structures.
    """
    def _load(self) -> T:
        path = self.file_path
        logger.info("Loading JSON file: %s", path)
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            logger.info("Loaded JSON list with %d records: %s", len(data), path.name)
        elif isinstance(data, dict):
            logger.info("Loaded JSON object with %d keys: %s", len(data), path.name)
        else:
            logger.warning("Loaded JSON of unexpected type (%s): %s", type(data), path.name)
        return data

"""
class JsonDataObjectStream(AbstractDataObjectStream[dict]):
    \"""
    Streams a JSON array file (very large JSON). Assumes top-level structure is a list.
    \"""

    def __iter__(self) -> typing.Iterator[dict]:
        import ijson  # requires: pip install ijson

        logger.info("Streaming JSON file: %s", self.file_path)

        with self.file_path.open("r", encoding="utf-8") as f:
            for item in ijson.items(f, "item"):
                yield item
"""

class JsonlDataObject(AbstractDataObject[list]):
    """
    Loads data from a JSONL (.jsonl) file.
    """
    def _load(self) -> list[dict]:
        path = pathlib.Path(self.file_path)
        logger.info("Loading JSONL file: %s", path)
        with path.open("r", encoding="utf-8") as f:
            data = [json.loads(line) for line in f if line.strip()]
        logger.info("Loaded %d records from JSONL file: %s", len(data), path)
        return data
    
    @property
    def data(self) -> list[dict]:
        if self._data is None:
            logger.debug("Data not cached, loading JSONL: %s", self.file_path)
            self._data = self._load()
        return self._data

class CsvDataObject(AbstractDataObject[list]):
    """
    Loads data from a CSV file and maps headers to row values.
    Returns: list[dict]
    """
    def _load(self) -> list[dict]:
        path = pathlib.Path(self.file_path)
        with path.open("r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            data = [{k: v.strip() if isinstance(v, str) else v for k, v in row.items()} for row in reader if any(row.values())]
        logger.info("Loaded %d records from CSV file: %s", len(data), path.name)
        return data
  
class CsvDataObjectStream(AbstractDataObjectStream[T]):
    def __iter__(self) -> typing.Iterator[list[T]]:
        batch: list[T] = []
        with self.file_path.open("r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                clean_row = {k: v.strip() if isinstance(v, str) else v for k, v in row.items()}
                batch.append(clean_row)
                if len(batch) >= self.batch_size:
                    yield batch
                    batch = []
            # Yield any remaining rows
            if batch:
                yield batch

class ParquetDataObject(AbstractDataObject[T]):
    """
    Streams data from a Parquet (.parquet) file row by row.
    """
    def _load(self) -> list[T]: return pq.read_table(self.file_path).to_pylist()

class ParquetDataObjectStream(AbstractDataObjectStream[T]):
    def __iter__(self) -> typing.Iterator[T]:
        path = pathlib.Path(self.file_path)
        parquet_file = pq.ParquetFile(path)
        for batch in parquet_file.iter_batches(batch_size=self.batch_size):
            yield batch

class DataObjectFactory:
    @staticmethod
    def create(path: str) -> T:
        path = pathlib.Path(path)
        should_stream = path.stat().st_size > STREAM_THRESHOLD

        logger.info("Loading data from file (stream = %s): %s", should_stream, path.name)

        if path.suffix == ".jsonl":
            if should_stream:
                raise NotImplementedError("Streaming JSONL not yet supported")
            return JsonlDataObject(path)
        if path.suffix == ".json":
            if should_stream:
                raise NotImplementedError("Streaming JSON not yet supported")
            return JsonDataObject(path)
        elif path.suffix == ".csv":
            logger.info("Loading CSV file: %s", path.name)
            return CsvDataObjectStream(path) if should_stream else CsvDataObject(path)
        elif path.suffix == ".parquet":
            return ParquetDataObjectStream(path) if not should_stream else ParquetDataObject(path)
        else:
            logger.warning("Unknown file type for path: %s", path)
            raise ValueError(f"Unsupported file type: {path}")