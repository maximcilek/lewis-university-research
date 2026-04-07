import json
from itertools import zip_longest

def map_to_dict(headers, row):
    record = {}
    for header, value in zip_longest(headers, row, fillvalue=None):
        if isinstance(value, str) and value.strip() == "":
            value = None
        record[header] = value
    return record

if __name__ == "__main__":
    headersStr = "tourney_id,tourney_name,surface,draw_size,tourney_level,tourney_date,match_num,winner_id,winner_seed,winner_entry,winner_name,winner_hand,winner_ht,winner_ioc,winner_age,loser_id,loser_seed,loser_entry,loser_name,loser_hand,loser_ht,loser_ioc,loser_age,score,best_of,round,minutes,w_ace,w_df,w_svpt,w_1stIn,w_1stWon,w_2ndWon,w_SvGms,w_bpSaved,w_bpFaced,l_ace,l_df,l_svpt,l_1stIn,l_1stWon,l_2ndWon,l_SvGms,l_bpSaved,l_bpFaced,winner_rank,winner_rank_points,loser_rank,loser_rank_points"
    rowStr = "1877-540,Wimbledon,Grass,32,G,18770709,1,113987,,,Spencer William Gore,,,GBR,27.33196441,114009,,,Ht Gilson,,,GBR,,6-2 6-0 6-3,5,R32,,,,,,,,,,,,,,"
    temp = "1877-540,Wimbledon,Grass,32,G,18770709,1,113987,,,Spencer William Gore,,,GBR,27.33196441,114009,,,Ht Gilson,,,GBR,,6-2 6-0 6-3,5,R32,,,,,,,,,,,,,,,,,,,,,,,".split(",")
    temp2 = "1877-540,Wimbledon,Grass,32,G,18770709,1,113987,,,Spencer William Gore,,,GBR,27.33196441,114009,,,Ht Gilson,,,GBR,,6-2 6-0 6-3,5,R32,,,,,,,,,,,,,,".split(",")
    print(f"Row length: {len(temp)}")
    print(f"Row length Before: {len(temp2)}")
    quit()
    headers = headersStr.split(",")
    row = rowStr.split(",")

    data = map_to_dict(headers, row)
    print(f"Headers length: {len(headers)}")
    print(f"Row length: {len(row)}")
    print(f"New Row length: {len(data.keys())}")
    print(json.dumps(data, indent=2))


"""
python3 - <<'PY'
import csv, sys
path = "/home/mcilek/Github/maximcilek/lewis-university-research/data/staging/tennisabstract/points/slams/slams_points_doubles.csv"
with open(path, newline='', encoding='utf-8') as f:
    r = csv.reader(f)
    header = next(r)
    n = len(header)
    for i, row in enumerate(r, start=2):  # line numbers (header is line 1)
        if len(row) != n:
            print(f"Line {i}: fields={len(row)} expected={n} :: {row}")
print("done")
PY


python3 - <<'PY'
import csv, os

path = "/home/mcilek/Github/maximcilek/lewis-university-research/data/staging/tennisabstract/points/slams/slams_points.csv"
tmp = path + ".tmp"

fixed = 0

with open(path, newline='', encoding='utf-8') as f_in, \
     open(tmp, 'w', newline='', encoding='utf-8') as f_out:

    reader = csv.reader(f_in)
    writer = csv.writer(f_out)

    header = next(reader)
    n = len(header)
    writer.writerow(header)

    for i, row in enumerate(reader, start=2):
        if len(row) < n:
            missing = n - len(row)
            row = row + [''] * missing
            fixed += 1
            print(f"Line {i}: padded {missing} empty fields ({len(row)}/{n})")

        elif len(row) > n:
            extra = len(row) - n
            row = row[:n]
            fixed += 1
            print(f"Line {i}: trimmed {extra} extra fields ({len(row)}/{n})")

        writer.writerow(row)

os.replace(tmp, path)

print(f"done - fixed {fixed} rows")
PY
"""