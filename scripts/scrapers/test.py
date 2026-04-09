import json
import logging
import pathlib
import sys
sys.path.append(str(pathlib.Path(__file__).resolve().parent.parent.parent))

import tennisabstractscraper.models.data_objects as data_objects
import tennisabstractscraper.models.tennisabstract_data as tennisabstract_data

DATA_DIR = pathlib.Path(__file__).resolve().parent.parent.parent / "data/canonical/tennisabstract"
METADATA_DIR = DATA_DIR / "_meta"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
LOGGER = logging.getLogger(__name__)

if __name__ == "__main__":
    LOGGER.info("Loading TennisAbstract Data")


    charting_points_file_path = DATA_DIR / "charting_points.csv"
    rally_codes_file_path = METADATA_DIR / "rally_codes.json"
    # charting_points_file_path = DATA_DIR / "players.parquet"

    tennisabstract_points = tennisabstract_data.TennisAbstractPointsData(str(charting_points_file_path), str(rally_codes_file_path))
    tennisabstract_points.load_points()
    # print(type(tennisabstract_points.data))    

"""
for batch_num, batch in enumerate(tennisabstract_points, 1):
    # col1 = batch.column('fullname')
    LOGGER.info("Batch #%s (%.2f MB) - %s rows %s columns", batch_num, batch.nbytes / (1024 * 1024), batch.num_rows, batch.num_columns)
    LOGGER.debug("Column(s): %s", json.dumps({col_name: str(batch.schema.types[i]) for i, col_name in enumerate(batch.column_names)}))
    LOGGER.debug("Schema Metadata: %s", batch.schema.metadata)
    results = [row for row in batch.to_pylist()]
"""