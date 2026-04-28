import pyarrow.json as paj
import pyarrow.parquet as pq
import pandas as pd
import pathlib
import dask.dataframe as dd

# ENV VARIABLES
DATA_DIR = pathlib.Path(__file__).resolve().parent.parent.parent / "data/prod"
INPUT_FILE = "/home/mcilek/Desktop/TennisAbstract-Old/charting_matches.jsonl"
OUTPUT_FILE = DATA_DIR / "charting-matches.parquet"

def load_full_file(fp):
    # Read JSONL properly
    table = paj.read_json(fp)

    # Convert to pandas
    df = table.to_pandas()

    # Save as parquet
    df.to_parquet(OUTPUT_FILE, index=False)

    print(f"Saved parquet to: {OUTPUT_FILE}")
    print(df.shape)

def write_in_batches(fp):
    # reader = paj.open_json(fp)
    reader = paj.open_json(INPUT_FILE, parse_options=paj.ParseOptions(explicit_schema=None))

    with pq.ParquetWriter(OUTPUT_FILE, reader.schema) as writer:
        for batch in reader:
            writer.write_batch(batch)

def dask_to_parquet(fp):
    df = dd.read_json(
        fp,
        lines=True,
        blocksize="64MB",
        dtype="object"   # <-- forces everything to string-like first
    )

    # Optional: clean columns after load
    df["best_of"] = df["best_of"].astype("float6")

    df.to_parquet(
        OUTPUT_FILE,
        engine="pyarrow",
        write_index=False
    )

    print("Saved parquet:", OUTPUT_FILE)
# write_in_batches(INPUT_FILE)
dask_to_parquet(INPUT_FILE)
