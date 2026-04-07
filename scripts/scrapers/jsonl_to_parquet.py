import pyarrow as pa
import pyarrow.json as paj
import pyarrow.parquet as pq

# Read JSONL
table = paj.read_json("data/canonical/tennisabstract/charting_matches.jsonl")

# Write to parquet
pq.write_table(table, "data/canonical/tennisabstract/charting_matches.parquet")

"""
import json

input_path = "data/canonical/tennisabstract/players.jsonl"
output_path = "data/canonical/tennisabstract/players_clean.jsonl"

DATE_FIELDS = {"death_date", "dob"}
STRING_FIELDS = {"twitter", "wiki_id"}
NUMERIC_FIELDS = {"ht", "dob_approx", "atp_id", "wta_id", "itf_id", "fc_id", "dc_id", "elo_rank", "elo_rating"}

with open(input_path) as infile, open(output_path, "w") as out:
    for line in infile:
        row = json.loads(line)

        for c in DATE_FIELDS:
            val = row.get(c)
            if val in [None, ""]:
                row[c] = None
            else:
                row[c] = str(val)

        for c in STRING_FIELDS:
            val = row.get(c)
            if val in [None, ""]:
                row[c] = None
            else:
                row[c] = str(val)

        for c in NUMERIC_FIELDS:
            val = row.get(c)
            if val in [None, ""]:
                row[c] = None
            else:
                row[c] = val  # ← keep numbers, including 0

        out.write(json.dumps(row) + "\n")
"""