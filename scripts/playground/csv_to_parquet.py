import pandas as pd

# Load CSV
df = pd.read_csv("/home/mcilek/Github/maximcilek/lewis-university-research/data/prod/charting-matches - All Matches CSV Raw.csv")

# Save to Parquet
df.to_parquet("/home/mcilek/Github/maximcilek/lewis-university-research/data/prod/charting-matches-new.parquet", engine="pyarrow", index=False)