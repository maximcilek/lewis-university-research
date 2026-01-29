from pathlib import Path
import pandas as pd
from pandas import json_normalize
import re, codecs, zipfile, csv

def find_repo_root(start_path=None):
    """
    Walk upward until a .git directory is found.
    Returns the repo root as a Path.
    """
    current = Path(start_path or __file__).resolve()
    for parent in [current] + list(current.parents):
        if (parent / ".git").exists():
            return parent
    raise RuntimeError("Not inside a Git repository")

def walk_all_files(path):
    """
    Recursively walks through a directory and yields all files inside it.
    Works with deeply nested subdirectories.
    """
    if not path.exists():
        raise FileNotFoundError(f"Path does not exist: {path}")

    if not path.is_dir():
        raise NotADirectoryError(f"Path is not a directory: {path}")

    for file_path in path.rglob("*"):
        if file_path.is_file(): # and file_path.suffix.lower() in {".csv", ".xls", ".xlsx"}:
            yield file_path

def print_file_size(size_bytes):
    for unit in ['B','KB','MB','GB','TB']:
        if size_bytes < 1024:
            break
        size_bytes /= 1024
    print(f"File Size: {size_bytes:.2f} {unit}")

def get_file_encoding_type(file_path):
    """
    Tries common text encodings and returns the first one that successfully
    reads the CSV header.
    """
    file_path = Path(file_path).resolve()
    encodings = ["utf-8", "cp1252", "latin-1"]

    for enc in encodings:
        try:
            with open(file_path, newline="", encoding=enc) as f:
                reader = csv.reader(f)
                next(reader)  # Try reading header
            return enc
        except UnicodeDecodeError:
            continue

    raise UnicodeDecodeError(
        "utf-8",
        b"",
        0,
        1,
        f"Could not determine encoding for file: {file_path}"
    )

if __name__ == "__main__":
    root = find_repo_root()
    data_directory = root / "data" / "raw"
    processed_data_directory = root / "data" / "processed"
    print(f"[INFO] - Repository Root: {root}")
    print(f"[INFO] - Data Directory: {data_directory}")

    pattern = re.compile(r'\.(xls|xlsx|csv|json)$', re.IGNORECASE)
    print(f"[INFO] - Walking Files filtering files with regex pattern: {pattern.pattern}")
    files = [f for f in data_directory.rglob(f"*") if f.is_file() and pattern.search(f.name)]
    print(f"[INFO] - Sucessfully Found {len(files)} Data Files")

    # Loop through and perform ad-hoc data cleaning tasks
    # print("\n===========================================================")
    for p in files:
        print(f"\n[INFO] - Preparing Data File: {p}")
        with open(p, "rb") as f:
          df = pd.DataFrame()
          size_bytes = p.stat().st_size
          encoding_type = get_file_encoding_type(p)

          magic_bytes = f.read(8).strip() # print(f"[DEBUG] - Magic Bytes: {magic_bytes}")
          # Binary
          if magic_bytes.startswith(b'\x50\x4B\x03\x04'):
              try:
                  with zipfile.ZipFile(p) as z:
                      if "xl/workbook.xml" in z.namelist():
                          print("[INFO] - File Type: Excel XML Spreadsheet File (.xlsx)")
                          df = pd.read_excel(p)
                      else:
                        print("[WARN] - File Type: Unknown Zip File (.zip)")
              except zipfile.BadZipFile:
                  print(f"[INFO] - Zip File is not Excel XML Spreadsheet: {str(p)}")
          elif magic_bytes.startswith(b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1'):
              print("[INFO] - File Type: Excel 97-2003 Spreadsheet File (.xls)")
              df = pd.read_excel(p)
          elif magic_bytes.startswith(b'PAR1'):
              print("[INFO] - File Type: Parquet File (.parquet)")
          elif magic_bytes.startswith(b"\x89HDF"):
              print("[INFO] - File Type: HDF5 File (.hdf5)")
          elif magic_bytes.startswith(b'%PDF'):
              print(f"[INFO] - File Type: PDF File (No Pandas Support): {str(p)}")
          elif b'\0' in magic_bytes:
              print(f"[INFO] - File Type: Unknown Binary File: {str(p)}")
          else:
              # Text-based
              for bom in (codecs.BOM_UTF8, codecs.BOM_UTF16_LE, codecs.BOM_UTF16_BE):
                if magic_bytes.startswith(bom):
                    print(f"[DEBUG] - Removing Byte Order Mark ({bom}): {magic_bytes}")
                    magic_bytes = magic_bytes[len(bom):]
                    break 
              #print(f"[INFO] - Magic Bytes: {magic_bytes}")
              #print(f"[INFO] - Path Type: {type(p)}")
              try:
                  text = magic_bytes.decode("utf-8", errors="ignore").lstrip()
                  if not text:
                      print(f"[FATAL] - Unknown File Type. Empty string returned after decoding file contents.")
                      quit()
              except Exception as e:
                  print(f"[WARN] - Failed to decode magic bytes {str(p)}: {e}")
              
              try:
                  df = pd.read_json(p)
                  print(f"[INFO] - JSON File (Byte Order Mark)")
              except Exception:
                  pass
              
              if df.empty:
                try:
                    if size_bytes >= 100 * 1024 * 1024:
                        print(f"[WARN] - Oversized File: {size_bytes}")
                        quit()
                        dfs = pd.read_csv(f, sep=",", engine="python", quotechar='"', on_bad_lines="warn", chunksize=50_000) # or engine='c'
                        for i, chunk in enumerate(dfs, start=1):
                            print(f"[DEBUG] - Processing chunk {i} | Rows: {len(chunk):,}")
                        quit()
                    else:
                        df = pd.read_csv(f, sep=None, engine="python", on_bad_lines="error", encoding=encoding_type)
                    print(f"[INFO] - CSV/TSV File (Auto-delimeter detection)")
                except Exception as e:
                  print(f"[DEBUG] - Failed to read file as csv/tsv: {e}")
                  quit()

              if df.empty:
                  print(f"[INFO] - Text file is not a Pandas-compatible data table, skipping: {p}")
                  quit()
          
          if not df.empty:
              rows, cols = df.shape
              mem_mb = df.memory_usage(deep=True).sum() / (1024 ** 2) # Memory
              missing_total = df.isna().sum().sum() # Missing values
              # num_duplicates = df.duplicated().sum()
              
              print_file_size(size_bytes)
              print(f"Memory Usage: {mem_mb:.2f} MB")
              print(f"Shape (Rows x Cols): {rows}x{cols}")
              print(f"Total Missing Values ({missing_total/rows:.2f}%): {missing_total}")
              # print(f"Duplicate Rows: {num_duplicates}")

              if "countries.json" in str(p):
                  print(f"Save Countries DataFrame as CSV: {p}")
                  df.to_csv(f"{processed_data_directory}/countries.csv", index=False)
                  quit()
          print("\n-----------------------------------------------------------")

    print(f"Done: {len(files)} files prepared")


"""
# read_pickle
read_table
read_csv
# read_fwf
# read_clipboard
read_excel
read_json
# read_html
read_xml
read_hdf
# read_feather
read_parquet
# read_iceberg
# read_orc
# read_sas
# read_spss
# read_sql_table
# read_sql_query
# read_sql
# read_stata


# Preview
# print("\n--- Preview (First 5 Rows) ---")
# print(df.head(5).to_string(index=False))

xlsxFile = "/home/mcilek/Github/maximcilek/lewis-university-tennis-research/tmp/excel/TheMatchesTennis.xlsx"
xlsFile = "/home/mcilek/Github/maximcilek/lewis-university-tennis-research/tmp/excel/xls_file_example.xls"
csvFile = "/home/mcilek/Github/maximcilek/lewis-university-tennis-research/data/raw/TheMatchesTennis.csv"
pdfFile = "/home/mcilek/Documents/college_of_dupage_transcript.pdf"
extenionlessFile = "/home/mcilek/example_file"
essayTextFile = "/home/mcilek/Documents/ApexAchievers_P2_Survey.txt" 
jsonFile = "/home/mcilek/Documents/weed-strain-data.json"
testPaths = [xlsxFile, xlsFile, csvFile, pdfFile, extenionlessFile, essayTextFile, jsonFile]



numeric_cols = df.select_dtypes(include="number")
if not numeric_cols.empty:
    print("\n-------------- DATAFRAME COLUMNS STATS --------------")
    print(numeric_cols.describe().to_string())

# print("\n-------------- DATAFRAME COLUMNS --------------")
# for col in df.columns:
#     non_null = df[col].notna().sum()
#     dtype = df[col].dtype
#     print(f"{col:20} | {str(dtype):10} | {non_null}/{rows} non-null")
"""