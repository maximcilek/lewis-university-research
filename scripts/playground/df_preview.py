import pandas as pd
from datetime import datetime
from pathlib import Path
import pathlib
import sys
sys.path.append(str(pathlib.Path(__file__).resolve().parent.parent.parent))

DATA_DIR = pathlib.Path(__file__).resolve().parent.parent.parent / "data"
METADATA_DIR = DATA_DIR / "canonical/tennisabstract/_meta"

df = pd.read_csv(DATA_DIR / "prod/charting_points.jsonl")

print(df.info())
print("--------------------------------------------")
print(df.head(20))
