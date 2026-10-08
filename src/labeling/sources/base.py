"""
Base abstract class for all independent reference evidence adapters.
"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
import pandas as pd

from src.labeling.schemas import (
    ConfidenceTier,
    LocationPrecision,
    NormalizedEvidence,
    OfficialnessLevel,
    SourceType,
    TargetClass,
)


class BaseEvidenceAdapter(ABC):
    """
    Abstract base adapter for normalizing external reference sources.
    """

    def __init__(
        self,
        source_name: str,
        class_candidate: TargetClass,
        source_type: SourceType,
        officialness_level: OfficialnessLevel,
        reference_dir: Path,
    ) -> None:
        self.source_name = source_name
        self.class_candidate = class_candidate
        self.source_type = source_type
        self.officialness_level = officialness_level
        self.reference_dir = Path(reference_dir)
        self.reference_dir.mkdir(parents=True, exist_ok=True)

    @abstractmethod
    def fetch_or_load(self) -> Any:
        """Loads raw reference data from disk or official API."""
        pass

    @abstractmethod
    def normalize(self, raw_data: Any) -> List[NormalizedEvidence]:
        """Maps raw records to the canonical NormalizedEvidence model."""
        pass

    def save_normalized(self, records: List[NormalizedEvidence], filename: Optional[str] = None) -> Path:
        """
        Saves normalized evidence list as a standardized Parquet table.
        """
        if not filename:
            filename = f"{self.source_name.lower()}_normalized.parquet"
        out_path = self.reference_dir / filename

        rows = []
        for r in records:
            rows.append({
                "evidence_id": r.evidence_id,
                "source_name": r.source_name,
                "source_type": r.source_type.value,
                "evidence_category": r.evidence_category.value,
                "class_candidate": r.class_candidate.value,
                "event_datetime_start": r.event_datetime_start,
                "event_datetime_end": r.event_datetime_end,
                "latitude": r.latitude,
                "longitude": r.longitude,
                "geometry_wkt": r.geometry_wkt,
                "location_precision": r.location_precision.value,
                "officialness_level": r.officialness_level.value,
                "event_description": r.event_description,
                "source_url": r.source_url,
                "source_record_id": r.source_record_id,
                "retrieval_timestamp": r.retrieval_timestamp,
                "license_notes": r.license_notes,
                "confidence_basis": r.confidence_basis,
                "metadata_json": r.metadata_json,
            })

        df = pd.DataFrame(rows)
        df.to_parquet(out_path, index=False)
        return out_path

    def compute_diagnostics(self, records: List[NormalizedEvidence]) -> Dict[str, Any]:
        """
        Computes required Step 4 diagnostics:
        - record count
        - geographic extent (bbox)
        - temporal extent
        - missingness
        - duplicate rate
        """
        if not records:
            return {
                "source_name": self.source_name,
                "record_count": 0,
                "geographic_extent": None,
                "temporal_extent": None,
                "missingness": {},
                "duplicate_rate": 0.0,
            }

        lats = [r.latitude for r in records]
        lons = [r.longitude for r in records]
        t_starts = [r.event_datetime_start for r in records]
        t_ends = [r.event_datetime_end for r in records]
        ids = [r.evidence_id for r in records]

        unique_ids = len(set(ids))
        duplicate_rate = 1.0 - (unique_ids / len(ids)) if ids else 0.0

        missingness = {
            "geometry_wkt": sum(1 for r in records if r.geometry_wkt is None) / len(records),
            "event_description": sum(1 for r in records if r.event_description is None) / len(records),
            "source_url": sum(1 for r in records if r.source_url is None) / len(records),
        }

        return {
            "source_name": self.source_name,
            "record_count": len(records),
            "unique_evidence_ids": unique_ids,
            "duplicate_rate": round(duplicate_rate, 4),
            "geographic_extent": {
                "min_lat": round(min(lats), 4),
                "max_lat": round(max(lats), 4),
                "min_lon": round(min(lons), 4),
                "max_lon": round(max(lons), 4),
            },
            "temporal_extent": {
                "min_start": min(t_starts).isoformat(),
                "max_end": max(t_ends).isoformat(),
            },
            "missingness": missingness,
        }
