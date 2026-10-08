"""
Canonical schemas and identifier generation for FIRMS VIIRS NOAA-20 SP preprocessing.
"""

from __future__ import annotations

import hashlib
from typing import Dict, List
import pyarrow as pa

# The 15 original FIRMS VIIRS NOAA-20 SP attributes
RAW_FIRMS_COLUMNS: List[str] = [
    "latitude",
    "longitude",
    "bright_ti4",
    "scan",
    "track",
    "acq_date",
    "acq_time",
    "satellite",
    "instrument",
    "confidence",
    "version",
    "bright_ti5",
    "frp",
    "daynight",
    "type",
]

# Canonical Pandas dtype dictionary for raw ingestion
RAW_DTYPES: Dict[str, str] = {
    "latitude": "float64",
    "longitude": "float64",
    "bright_ti4": "float32",
    "scan": "float32",
    "track": "float32",
    "acq_date": "string",
    "acq_time": "string",
    "satellite": "string",
    "instrument": "string",
    "confidence": "string",
    "version": "string",
    "bright_ti5": "float32",
    "frp": "float32",
    "daynight": "string",
    "type": "int16",
}

# Master table PyArrow schema
MASTER_PARQUET_SCHEMA = pa.schema([
    pa.field("detection_id", pa.string(), nullable=False),
    pa.field("source_file", pa.string(), nullable=False),
    pa.field("source_row_idx", pa.int32(), nullable=False),
    pa.field("is_burn_in_context", pa.bool_(), nullable=False),
    pa.field("latitude", pa.float64(), nullable=False),
    pa.field("longitude", pa.float64(), nullable=False),
    pa.field("acq_datetime_utc", pa.timestamp("us", tz="UTC"), nullable=False),
    pa.field("timestamp_utc", pa.int64(), nullable=False),
    pa.field("h3_res8", pa.string(), nullable=False),
    pa.field("bright_ti4", pa.float32(), nullable=False),
    pa.field("bright_ti5", pa.float32(), nullable=False),
    pa.field("frp", pa.float32(), nullable=False),
    pa.field("scan", pa.float32(), nullable=False),
    pa.field("track", pa.float32(), nullable=False),
    pa.field("acq_date", pa.string(), nullable=False),
    pa.field("acq_time", pa.string(), nullable=False),
    pa.field("satellite", pa.dictionary(pa.int8(), pa.string()), nullable=False),
    pa.field("instrument", pa.dictionary(pa.int8(), pa.string()), nullable=False),
    pa.field("confidence", pa.dictionary(pa.int8(), pa.string()), nullable=False),
    pa.field("version", pa.dictionary(pa.int8(), pa.string()), nullable=False),
    pa.field("daynight", pa.dictionary(pa.int8(), pa.string()), nullable=False),
    pa.field("type", pa.int16(), nullable=False),
])


def generate_detection_id(
    source_file: str,
    row_idx: int,
    latitude: float,
    longitude: float,
    acq_date: str,
    acq_time: str,
    bright_ti4: float,
    frp: float,
) -> str:
    """
    Computes a deterministic, collision-resistant full 64-character SHA-256 hexadecimal digest
    from the immutable observation provenance tuple.
    """
    token = f"{source_file}:{row_idx}:{latitude:.5f}:{longitude:.5f}:{acq_date}:{acq_time}:{bright_ti4:.2f}:{frp:.2f}"
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
