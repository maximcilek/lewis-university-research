import zipfile
from pathlib import Path

zip_dir = Path("/home/mcilek/Github/maximcilek/lewis-university-research/data/raw/tennisabstract/zip")
extract_dir = Path("/home/mcilek/Github/maximcilek/lewis-university-research/data/raw/tennisabstract")
extract_dir.mkdir(parents=True, exist_ok=True)

for zip_path in zip_dir.glob("*.zip"):
    print(f"Processing {zip_path}...")

    target_root = extract_dir / zip_path.stem
    target_root.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(zip_path, "r") as z:
        for member in z.namelist():

            if not member.lower().endswith(".csv"):
                continue

            # Remove the first directory level
            parts = Path(member).parts
            stripped_path = Path(*parts[1:])  # drop top folder

            target_path = target_root / stripped_path
            target_path.parent.mkdir(parents=True, exist_ok=True)

            print(f"  Writing {target_path}")

            with z.open(member) as src, open(target_path, "wb") as dst:
                dst.write(src.read())

print("Done.")