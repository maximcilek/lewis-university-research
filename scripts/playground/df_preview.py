import pandas as pd
from datetime import datetime
from pathlib import Path
import pathlib
import sys
sys.path.append(str(pathlib.Path(__file__).resolve().parent.parent.parent))

DATA_DIR = pathlib.Path(__file__).resolve().parent.parent.parent / "data"
METADATA_DIR = DATA_DIR / "canonical/tennisabstract/_meta"

df = pd.read_json(DATA_DIR / "prod/charting_points.jsonl", lines=True)

print(df.info())
print("--------------------------------------------")
print(df.head(20))


print("==================================")


chunks = []
for chunk in pd.read_json("your_file.json", lines=True, chunksize=10000):
    chunks.append(chunk[["rally_length", "is_double"]])  # only keep what you need

df = pd.concat(chunks, ignore_index=True)
print(df.info())
print(df.head(10))

# df.plot.line(subplots=True)
