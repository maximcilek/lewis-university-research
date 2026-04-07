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

logger = logging.getLogger(__name__)
T = typing.TypeVar("T")  # Generic type for items loaded by the loader

@dataclasses.dataclass
class AbstractDataObject(abc.ABC, typing.Generic[T]):
    """
    Abstract base class for all data loaders.
    Enforces a consistent interface for loading data from files.
    """
    _file_path: str | pathlib.Path
    _data: T = dataclasses.field(default=None, init=False, repr=False)

    def __post_init__(self):
        self._file_path = pathlib.Path(self._file_path)  # ensure Path object
        if not self._file_path.is_file():
            raise FileNotFoundError(f"{self.__class__.__name__}: {type(self).file_path.fset.__name__} must exist and be a valid file path, got {self._file_path!r}")
    
    @property
    def file_path(self) -> pathlib.Path: return self._file_path

    @property
    @abc.abstractmethod
    def data(self) -> T:
        ...
    
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
        logger.info("Loading CSV file: %s", path)
        with path.open("r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            data = [{k: v.strip() if isinstance(v, str) else v for k, v in row.items()} for row in reader if any(row.values())]
        logger.info("Loaded %d records from CSV file: %s", len(data), path)
        return data

    @property
    def data(self) -> list[dict]:
        if self._data is None:
            logger.debug("Data not cached, loading CSV: %s", self.file_path)
            self._data = self._load()
        return self._data

class ParquetDataObject(AbstractDataObject[typing.Iterator[dict]]):
    """
    Streams data from a Parquet (.parquet) file row by row.
    """
    
    # def _load(self) -> typing.List[dict]:
    #     # optional: load everything into a list (memory-heavy)
    #     return list(self.data)

    @property
    def data(self) -> typing.Iterator[dict]:
        path = pathlib.Path(self.file_path)
        logger.info("Streaming Parquet file: %s", path)
        parquet_file = pq.ParquetFile(path)

        for batch in parquet_file.iter_batches(batch_size=10000):
            for row in batch.to_pylist():
                yield row

class DataObjectFactory:
    @staticmethod
    def create(path: str) -> T:
        logger.debug("Creating data object for path: %s", path)
        if path.endswith(".jsonl"):
            return JsonlDataObject(path)
        elif path.endswith(".csv"):
            return CsvDataObject(path)
        elif path.endswith(".parquet"):
            return ParquetDataObject(path)
        else:
            logger.warning("Unknown file type for path: %s", path)
            raise ValueError(f"Unsupported file type: {path}")