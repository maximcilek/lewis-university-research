import csv
import json
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional

ROOT_DIR = Path(__file__).parent.parent.parent
DATA_DIR = ROOT_DIR / "data"
RAW_DATA_DIR = DATA_DIR / "raw" / "tennisabstract"
CANONICAL_DATA_DIR = DATA_DIR / "canonical" / "tennisabstract"
REVISION_LOG_PATH = RAW_DATA_DIR / "revision_log.json"

config = {
    "log_headers": False
}


@dataclass
class Revision:
    line_num: int
    issue: str
    details: str


def is_whitespace_only(x: Optional[str]) -> bool:
    return not (x or "").strip()


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def canonicalize_csv_file(raw_path: Path, canonical_path: Path):
    revisions = []
    had_revisions = False

    ensure_parent(canonical_path)

    with raw_path.open(newline="", encoding="utf-8") as src, canonical_path.open(
        "w", newline="", encoding="utf-8"
    ) as dst:
        reader = csv.reader(src)
        writer = csv.writer(dst)

        try:
            header = next(reader)
        except StopIteration:
            revisions.append(Revision(1, "EMPTY_FILE", "CSV has no header/rows."))
            return True, revisions

        num_columns = len(header)

        writer.writerow(header)

        for line_num, row in enumerate(reader, start=2):
            if len(row) == num_columns:
                writer.writerow(row)
            elif len(row) > num_columns:
              trimmedRow = row[:num_columns]
              extraColumns = row[num_columns:]
              if not all(not (cell or "").strip() for cell in extraColumns):
                raise SystemExit(f"[FATAL] - {raw_path.name} | Line {line_num} | TRIM_TRAILING_EMPTY_COLUMNS | Non-empty extra cells beyond header. Trimmed {len(row) - num_columns} empty columns.")
              writer.writerow(trimmedRow)
            else:
                had_revisions = True
                if raw_path.name == "atp_matches_amateur.csv" and num_columns - len(row) == 9:
                    row = row + ([""] * 9)
                else:
                    revisions.append(Revision(line_num, "PAD_MISSING_COLUMNS", f"Manually add {num_columns - len(row)} empty columns to match header."))
                writer.writerow(row)
    return had_revisions, revisions

def copy_raw_to_canonical_and_log():
    revision_dict = {}
    total_files = 0
    revised_files = 0

    for raw_path in RAW_DATA_DIR.rglob("*.csv"):
        total_files += 1
        canonical_path = CANONICAL_DATA_DIR / raw_path.relative_to(RAW_DATA_DIR)

        had_revisions, revisions = canonicalize_csv_file(raw_path, canonical_path)

        if had_revisions and len(revisions) > 0:
            revised_files += 1
            revision_dict[raw_path.name] = [asdict(r) for r in revisions]

    # Write JSON log
    ensure_parent(REVISION_LOG_PATH)
    with REVISION_LOG_PATH.open("w", encoding="utf-8") as f:
        json.dump(revision_dict, f, indent=2)

    print(f"Processed {total_files} CSV files.")
    print(f"Files needing revision: {revised_files}")
    print(f"Revision log written to: {REVISION_LOG_PATH}")


if __name__ == "__main__":
    CANONICAL_DATA_DIR.mkdir(parents=True, exist_ok=True)
    copy_raw_to_canonical_and_log()