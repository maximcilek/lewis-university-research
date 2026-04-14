import json
import pyarrow as pa
import pyarrow.parquet as pq

input_path = "data/prod/charting_matches.jsonl"
output_path = "data/prod/charting_matches.parquet"
mkeys = [
    "tournament_start_date", "tournament_name", "surface", "level",
    "round", "score", "best_of", "time", "charting_id", "winner",
    "player_2_fullname", "player_2_rank", "player_2_seed", "player_2_entry",
    "player_1_fullname", "player_1_rank", "player_1_seed", "player_1_entry"
]

# -----------------------------
# SAFE TYPE NORMALIZER
# -----------------------------
def norm_str(v):
    if v is None:
        return None
    return str(v)

def norm_int(v):
    if v is None or v == "":
        return None
    try:
        return int(v)
    except:
        return None

def normalize_player(row):
    return {
        "player_id": norm_str(row.get("player_id")),
        "fullname": norm_str(row.get("fullname")),
        "nameparam": norm_str(row.get("nameparam")),
        "lastname": norm_str(row.get("lastname")),
        "country": norm_str(row.get("country")),
        "dob": norm_str(row.get("dob")),
        "hand": norm_str(row.get("hand")),
        "backhand": norm_str(row.get("backhand")),

        "ht": norm_int(row.get("ht")),

        "atp_id": norm_str(row.get("atp_id")),
        "wta_id": norm_str(row.get("wta_id")),
        "itf_id": norm_str(row.get("itf_id")),
        "fc_id": norm_str(row.get("fc_id")),
        "dc_id": norm_str(row.get("dc_id")),
        "twitter": norm_str(row.get("twitter")),
        "wiki_id": norm_str(row.get("wiki_id")),
    }

# -----------------------------
# STREAMING WRITER
# -----------------------------
buffer = []
writer = None
batch_size = 50

with open(input_path, "r") as f:
    for line in f:
        row = json.loads(line)
        print(row)
        quit()
        player = normalize_player(row)

        matches = row.get("matches") or {}

        for match_id, m in matches.items():

            flat = {
                **player,
                "match_id": norm_str(match_id),
            }

            # force ALL match fields to stable types
            for k in mkeys:
                if k in ["winner", "time"]:
                    flat[k] = norm_int(m.get(k))
                else:
                    flat[k] = norm_str(m.get(k))

            buffer.append(flat)

        # write batch
        if len(buffer) >= batch_size:
            table = pa.Table.from_pylist(buffer)

            if writer is None:
                writer = pq.ParquetWriter(output_path, table.schema)

            writer.write_table(table)
            buffer.clear()

# flush
if buffer:
    table = pa.Table.from_pylist(buffer)

    if writer is None:
        writer = pq.ParquetWriter(output_path, table.schema)

    writer.write_table(table)

if writer:
    writer.close()

print("DONE")














"""


import pyarrow.json as paj
import pyarrow.parquet as pq

reader = paj.open_json("data/prod/charting_matches.jsonl")

reader = paj.open_json(
    "data/prod/charting_matches.jsonl",
    parse_options=paj.ParseOptions(explicit_schema=None)
)

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
)"""