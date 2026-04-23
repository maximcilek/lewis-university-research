import pyarrow.json as paj
import pyarrow.parquet as pq
import sys
sys.path.append(str(pathlib.Path(__file__).resolve().parent.parent.parent))

# ENV VARIABLES
DATA_DIR = pathlib.Path(__file__).resolve().parent.parent.parent / "data/prod"
INPUT_FILE = DATA_DIR / "players.jsonl"

def load_full_file(fp):
  parquet_file = pq.ParquetFile(fp)
  chunks = []
  for batch in parquet_file.iter_batches(batch_size=10000):
      chunk = batch.to_pandas()
      chunks.append(chunk)

  df = pd.concat(chunks, ignore_index=True)

reader = paj.open_json(INPUT_FILE)
# reader = paj.open_json(INPUT_FILE, parse_options=paj.ParseOptions(explicit_schema=None))

with pq.ParquetWriter("data/prod/charting_matches.parquet", reader.schema) as writer:
    for batch in reader:
        writer.write_batch(batch)

import dask.dataframe as dd

df = dd.read_json(
    "data/dev/tennisabstract/players_all.jsonl",
    lines=True,
    blocksize="64MB",
    dtype="object"
)

df.to_parquet(
    "data/prod/players.parquet",
    engine="pyarrow"
)