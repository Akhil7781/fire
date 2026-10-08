"""
Master pipeline coordinator for the Label Construction phase.
Ingests reference sources, executes spatiotemporal matching, fuses multi-source evidence,
and produces the audited detection-level label Parquet table.
"""

from __future__ import annotations

import json
import time
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import pandas as pd
import pyarrow.parquet as pq

from src.labeling.config import LabelConfig, get_label_config
from src.labeling.fusion import fuse_detection_matches
from src.labeling.matching import match_evidence_to_firms
from src.labeling.schemas import (
    ConfidenceTier,
    EvidenceMatch,
    FinalLabelRecord,
    LabelStatus,
    NormalizedEvidence,
    TargetClass,
)
from src.labeling.sources import (
    AgriculturalFireAdapter,
    ForestFireAdapter,
    GlobalFireAtlasAdapter,
    IndustrialFireAdapter,
    MCD64A1Adapter,
    OtherThermalSourceAdapter,
    Sentinel2AgriculturalPilotAdapter,
)


class LabelConstructionPipeline:
    """
    Orchestrates the entire label construction workflow across all four target classes.
    """

    def __init__(self, config: Optional[LabelConfig] = None) -> None:
        self.config = config or get_label_config()

        # Instantiate adapters for all target classes
        self.industrial_adapter = IndustrialFireAdapter(self.config.reference_dir / "industrial")
        self.forest_adapter = ForestFireAdapter(self.config.reference_dir / "forest")
        self.mcd64a1_adapter = MCD64A1Adapter(self.config.reference_dir / "forest")
        self.gfa_adapter = GlobalFireAtlasAdapter(self.config.reference_dir / "forest")
        self.agri_adapter = AgriculturalFireAdapter(self.config.reference_dir / "agriculture")
        self.s2_agri_adapter = Sentinel2AgriculturalPilotAdapter(self.config.reference_dir / "agriculture")
        self.other_adapter = OtherThermalSourceAdapter(self.config.reference_dir / "other_thermal")

    def ingest_all_reference_sources(self) -> Tuple[List[NormalizedEvidence], Dict[str, Any]]:
        """
        Runs Step 4: ingests, normalizes, validates, and saves reference datasets.
        Returns a flat list of all normalized evidence records and source diagnostics.
        """
        all_evidence: List[NormalizedEvidence] = []
        diagnostics: Dict[str, Any] = {}

        adapters = [
            self.industrial_adapter,
            self.forest_adapter,
            self.mcd64a1_adapter,
            self.gfa_adapter,
            self.agri_adapter,
            self.s2_agri_adapter,
            self.other_adapter,
        ]

        for adapter in adapters:
            raw_data = adapter.fetch_or_load()
            records = adapter.normalize(raw_data)
            adapter.save_normalized(records)
            diag = adapter.compute_diagnostics(records)
            diagnostics[adapter.source_name] = diag
            all_evidence.extend(records)

        return all_evidence, diagnostics

    def run_matching_and_fusion(
        self,
        firms_df: pd.DataFrame,
        evidence_records: List[NormalizedEvidence],
    ) -> pd.DataFrame:
        """
        Executes Steps 5 through 9:
        - Geodesic spatial and temporal interval matching
        - Grouping matches by detection_id
        - Evidence fusion and conflict resolution
        - Canonical label record creation
        """
        # Match FIRMS detections against all evidence
        matches: List[EvidenceMatch] = match_evidence_to_firms(firms_df, evidence_records, self.config)

        # Group matches by detection_id
        matches_by_det: Dict[str, List[EvidenceMatch]] = defaultdict(list)
        for m in matches:
            matches_by_det[m.detection_id].append(m)

        # Iterate through every detection in firms_df to guarantee 1:1 row alignment
        det_ids = firms_df["detection_id"].to_numpy()
        label_records: List[Dict[str, Any]] = []

        for det_id in det_ids:
            det_id_str = str(det_id)
            det_matches = matches_by_det.get(det_id_str, [])
            final_rec = fuse_detection_matches(det_id_str, det_matches)
            label_records.append(final_rec.to_dict())

        return pd.DataFrame(label_records)

    def run(
        self,
        sample_size: Optional[int] = None,
        save_output: bool = True,
    ) -> Dict[str, Any]:
        """
        Executes the complete label construction pipeline.
        """
        t0 = time.perf_counter()

        print("\n" + "=" * 75)
        print("STARTING INDEPENDENT LABEL CONSTRUCTION PIPELINE")
        print("=" * 75)

        # 1. Ingest all independent reference sources
        print("\n[Step 1/4] Ingesting and normalizing all 4 reference source classes...")
        all_evidence, src_diagnostics = self.ingest_all_reference_sources()
        print(f"  Ingested {len(all_evidence)} total reference evidence records across 4 classes.")
        for src, diag in src_diagnostics.items():
            print(f"  - {src:35s}: {diag['record_count']:5d} records, Bbox: {diag.get('geographic_extent')}")

        # 2. Load frozen FIRMS dataset (or sample)
        print("\n[Step 2/4] Reading frozen FIRMS feature dataset...")
        cols_needed = ["detection_id", "latitude", "longitude", "acq_datetime_utc", "partition", "is_burn_in_context"]
        if sample_size:
            print(f"  Running in test/slice mode with sample_size={sample_size}...")
            firms_df = pd.read_parquet(self.config.frozen_features_path, columns=cols_needed).iloc[:sample_size].copy()
        else:
            print("  Loading all 1,175,795 rows from frozen Parquet table...")
            firms_df = pd.read_parquet(self.config.frozen_features_path, columns=cols_needed)

        total_firms = len(firms_df)
        print(f"  Loaded {total_firms} FIRMS detections.")

        # 3. Match and fuse evidence
        print("\n[Step 3/4] Performing spatiotemporal matching & conflict-aware evidence fusion...")
        labels_df = self.run_matching_and_fusion(firms_df, all_evidence)

        # Join partition column for split auditing
        labels_df["partition"] = firms_df["partition"].values
        labels_df["is_burn_in_context"] = firms_df["is_burn_in_context"].values

        # 4. Save output label table
        out_parquet = self.config.output_labels_dir / "master_labels_2025.parquet"
        if save_output:
            print(f"\n[Step 4/4] Writing master label table to: {out_parquet}...")
            self.config.output_labels_dir.mkdir(parents=True, exist_ok=True)
            # Remove partition / context helper columns before final write to maintain exact schema
            out_df = labels_df.drop(columns=["partition", "is_burn_in_context"], errors="ignore")
            out_df.to_parquet(out_parquet, index=False)
            print(f"  [PASS] Saved {len(out_df)} rows to {out_parquet}.")

        elapsed = time.perf_counter() - t0

        # Compute summary metrics
        class_counts = labels_df["label_class"].value_counts().to_dict()
        tier_counts = labels_df["confidence_tier"].value_counts().to_dict()
        status_counts = labels_df["label_status"].value_counts().to_dict()
        split_counts = labels_df.groupby(["partition", "label_class"]).size().unstack(fill_value=0).to_dict(orient="index")

        n_labeled = int((labels_df["label_class"] > 0).sum())
        n_unlabeled = int((labels_df["label_class"] == 0).sum())

        summary = {
            "runtime_seconds": round(elapsed, 2),
            "total_firms_detections": total_firms,
            "total_labeled": n_labeled,
            "total_unlabeled": n_unlabeled,
            "labeled_percentage": round((n_labeled / total_firms) * 100, 4) if total_firms else 0.0,
            "class_distribution": class_counts,
            "confidence_tier_distribution": tier_counts,
            "label_status_distribution": status_counts,
            "partition_class_matrix": split_counts,
            "reference_diagnostics": src_diagnostics,
            "output_path": str(out_parquet) if save_output else "IN_MEMORY",
        }

        # Save summary report
        summary_path = self.config.audits_dir / "label_pipeline_summary.json"
        self.config.audits_dir.mkdir(parents=True, exist_ok=True)
        with open(summary_path, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2)

        print("\n" + "=" * 75)
        print("LABEL CONSTRUCTION PIPELINE COMPLETE")
        print("=" * 75)
        print(f"  Runtime:               {elapsed:.2f} s")
        print(f"  Total Detections:      {total_firms:,d}")
        print(f"  Total Labeled:         {n_labeled:,d} ({summary['labeled_percentage']}%)")
        print(f"  Total Unlabeled:       {n_unlabeled:,d}")
        print(f"  Class 1 (Industrial):  {class_counts.get(1, 0):,d}")
        print(f"  Class 2 (Forest):      {class_counts.get(2, 0):,d}")
        print(f"  Class 3 (Agri):        {class_counts.get(3, 0):,d}")
        print(f"  Class 4 (Other):       {class_counts.get(4, 0):,d}")
        print(f"  Confirmed (Tier A):    {tier_counts.get(ConfidenceTier.TIER_A.value, 0):,d}")
        print(f"  Probable (Tier B):     {tier_counts.get(ConfidenceTier.TIER_B.value, 0):,d}")
        print(f"  Summary JSON:          {summary_path}\n")

        return summary
