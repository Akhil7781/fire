"""Stage 8.37 NASA FIRMS Data Ingestion Layer.

Ingests and validates NASA FIRMS thermal anomaly observations from:
- CSV files (live streams, local archives, API uploads)
- Parquet / JSON historical files
- In-memory pandas DataFrames or raw dictionaries
"""

import io
import logging
from pathlib import Path
from typing import List, Union, Dict, Any
import pandas as pd

from src.stage8_37.inference.schemas import FirmsDetectionRecord
from src.stage8_37.ingestion.validators import validate_detection_record, deduplicate_detections

logger = logging.getLogger(__name__)

class FirmsLoader:
    """Ingestion engine for raw NASA FIRMS detections."""

    @staticmethod
    def load_from_dataframe(df: pd.DataFrame) -> List[FirmsDetectionRecord]:
        """Validates and parses a pandas DataFrame of FIRMS observations."""
        records = df.to_dict(orient="records")
        valid_records = []
        errors = []

        for idx, rec in enumerate(records):
            is_valid, err, norm_rec = validate_detection_record(rec)
            if is_valid:
                valid_records.append(norm_rec)
            else:
                errors.append(f"Row {idx}: {err}")

        if errors:
            logger.warning(f"Skipped {len(errors)} invalid FIRMS records out of {len(records)}.")

        deduped = deduplicate_detections(valid_records)
        return [FirmsDetectionRecord(**r) for r in deduped]

    @classmethod
    def load_from_csv(cls, source: Union[str, Path, io.StringIO, io.BytesIO]) -> List[FirmsDetectionRecord]:
        """Loads and normalizes FIRMS records from CSV path or file buffer."""
        df = pd.read_csv(source)
        return cls.load_from_dataframe(df)

    @classmethod
    def load_from_parquet(cls, path: Union[str, Path]) -> List[FirmsDetectionRecord]:
        """Loads and normalizes FIRMS records from Parquet file."""
        df = pd.read_parquet(path)
        return cls.load_from_dataframe(df)

    @classmethod
    def load_from_dict_list(cls, records: List[Dict[str, Any]]) -> List[FirmsDetectionRecord]:
        """Loads and normalizes from a list of dictionaries."""
        df = pd.DataFrame(records)
        return cls.load_from_dataframe(df)
