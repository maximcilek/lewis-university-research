import json
import pyarrow as pa
import pyarrow.parquet as pq

input_path = "data/prod/players.jsonl"
output_path = "data/dev/matches.parquet"

mkeys = [
    'tournament_start_date', 'tournament_name', 'surface', 'level',
    'round', 'score', 'best_of', 'time', 'charting_id', 'winner',
    'player_2_fullname', 'player_2_rank', 'player_2_seed', 'player_2_entry',
    'player_1_fullname', 'player_1_rank', 'player_1_seed', 'player_1_entry'
]

# -------------------------
# NORMALIZER (UNCHANGED)
# -------------------------
def normalize_player(row):
    def s(v):
        return None if v is None else str(v)

    def maybe_str(v):
        return None if v is None else str(v)

    def maybe_int(v):
        try:
            return int(v)
        except:
            return None

    return {
        "player_id": s(row.get("player_id")),
        "fullname": s(row.get("fullname")),
        "nameparam": s(row.get("nameparam")),
        "lastname": s(row.get("lastname")),
        "country": s(row.get("country")),
        "dob": s(row.get("dob")),
        "hand": s(row.get("hand")),
        "backhand": s(row.get("backhand")),

        "ht": maybe_int(row.get("ht")),

        "atp_id": maybe_str(row.get("atp_id")),
        "wta_id": maybe_str(row.get("wta_id")),
        "itf_id": maybe_str(row.get("itf_id")),
        "fc_id": maybe_str(row.get("fc_id")),
        "dc_id": maybe_str(row.get("dc_id")),
        "twitter": maybe_str(row.get("twitter")),
        "wiki_id": maybe_str(row.get("wiki_id")),
    }

# -------------------------
# STREAMING WRITER (FIXED)
# -------------------------
buffer = []
writer = None
schema = None
batch_size = 50

with open(input_path, "r") as f:
    for line in f:
        row = json.loads(line)

        player = normalize_player(row)
        matches = row.get("matches") or {}

        for match_id, m in matches.items():

            flat = {
                **player,
                "match_id": match_id,
            }

            for k in mkeys:
                flat[k] = m.get(k)

            buffer.append(flat)

        # -------------------------
        # WRITE BATCH SAFELY
        # -------------------------
        if len(buffer) >= batch_size:
            table = pa.Table.from_pylist(buffer)

            # lock schema on first batch
            if writer is None:
                schema = table.schema
                writer = pq.ParquetWriter(output_path, schema)
            else:
                table = table.cast(schema)

            writer.write_table(table)
            buffer.clear()

# -------------------------
# FLUSH FINAL BATCH
# -------------------------
if buffer:
    table = pa.Table.from_pylist(buffer)

    if writer is None:
        writer = pq.ParquetWriter(output_path, table.schema)
    else:
        table = table.cast(schema)

    writer.write_table(table)

if writer:
    writer.close()

print("DONE")