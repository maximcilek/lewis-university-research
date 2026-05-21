import pandas as pd

# Load parquet file
df = pd.read_parquet("/home/mcilek/Github/maximcilek/lewis-university-research/data/prod/charting-matches.parquet")

# Save as CSV
df.to_csv("/home/mcilek/Github/maximcilek/lewis-university-research/data/prod/charting-matches.csv", index=False)