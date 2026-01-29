import csv
from pathlib import Path

def csv_dimensions(file_path):
    """
    Returns (num_rows, num_columns) of a CSV file without fully loading it.
    """
    file_path = Path(file_path)
    if not file_path.exists():
        raise FileNotFoundError(f"CSV file does not exist: {file_path}")

    num_rows = 0
    num_columns = 0
    with open(file_path, newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        for i, row in enumerate(reader):
            if i == 0:
                num_columns = len(row)
            num_rows += 1
    return num_rows, num_columns


def csv_column_names(file_path):
    file_path = Path(file_path)
    if not file_path.exists():
        raise FileNotFoundError(f"CSV file does not exist: {file_path}")

    with open(file_path, newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        columns = next(reader)  # first row is the header
    return columns

# Example usage
file = "/home/mcilek/Github/maximcilek/lewis-university-tennis-research/data/raw/Combined_pointsfile.csv"
rows, cols = csv_dimensions(file)
print(f"CSV Dimensions: {rows} rows x {cols} columns")

cols = csv_column_names(file)
print(f"CSV Column Names ({len(cols)} columns): {cols}")
