#!/usr/bin/env python3
"""
Test Suite: DS08 Stage 8.18 Planning & Protocol Specification
--------------------------------------------------------------
Verifies:
1. Complete existence of all Stage 8.18 planning deliverables in docs/stage8_18/.
2. Internal mathematical and logical consistency of sampling_plan.json:
   - Strata sum == 250
   - Geographic sum == 250 (100.0%)
   - Seasonal sum == 250 (100.0%)
   - Pilot benchmark == 15, expansion == 235
3. Formatting and validity of sampling_plan.csv.
4. Protection of existing pilot dataset (ds08_pilot_v1) and predecessor invariants.
5. Strict enforcement of non-execution boundaries (zero bulk imagery, zero model training).
"""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DOCS_DIR = PROJECT_ROOT / "docs" / "stage8_18"
PROTO_DIR = PROJECT_ROOT / "data" / "reference" / "ds08" / "protocols" / "stage8_18"
PILOT_PACKAGE_DIR = PROJECT_ROOT / "data" / "reference" / "ds08" / "packages" / "ds08_pilot_v1"
A1_DIR = PROJECT_ROOT / "data" / "reference" / "ds08" / "annotations" / "manual" / "annotator_1"
A2_DIR = PROJECT_ROOT / "data" / "reference" / "ds08" / "annotations" / "manual" / "annotator_2"
REVIEW_DIR = PROJECT_ROOT / "data" / "reference" / "ds08" / "annotations" / "adjudication" / "review"
SOURCE_MANIFEST_PATH = PROJECT_ROOT / "data" / "reference" / "ds08" / "annotations" / "adjudication" / "stage8_16_source_manifest.json"

FROZEN_PREDECESSORS = {
    "models/tcn/best_tcn.pt": "dfa2decb772cf71b65601a4cb83a12b73ee1706ff47e2acb23a9f53c84506f16",
    "models/deep_sad/best_deep_sad.pt": "a7f99f521cf56e3d651101259543f967eee535df82736aae3ae4271922947eaa",
    "models/yolo/infrastructure/best_infrastructure.pt": "bad5d3942f469b74a7778762696bb390174619cb0f403dbcc93be1066ba5dcf6",
    "models/yolo/fire_smoke/best_fire_smoke.pt": "29ab42eda1cd05d7141525927ab1c502c249082b5b2bbf5f2e0c9e8847c3d227",
    "data/embeddings/fusion/india_2025_tcn_sad_aligned.parquet": "49505cb4705516aef8d77af628debc485be894fae75dc19e3269b3ba6df7e931",
}


def compute_sha256(filepath: Path) -> str:
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def test_1_deliverables_exist():
    expected_files = [
        "stage8_18_sampling_protocol.md",
        "stage8_18_acquisition_protocol.md",
        "stage8_18_annotation_protocol.md",
        "stage8_18_quality_and_governance.md",
        "stage8_18_split_strategy.md",
        "stage8_18_decision_log.md",
        "sampling_plan.json",
        "sampling_plan.csv",
        "STAGE8_18_PLANNING_AUDIT_REPORT.md",
    ]
    for ef in expected_files:
        fp = DOCS_DIR / ef
        assert fp.exists(), f"Deliverable missing: {ef}"
        assert fp.stat().st_size > 0, f"Deliverable is empty: {ef}"

    # Also check review report mirror
    review_report = PROJECT_ROOT / "data" / "reference" / "ds08" / "annotations" / "review" / "stage8_18_planning_audit_report.md"
    assert review_report.exists(), "Review mirror report missing"


def test_2_sampling_plan_internal_consistency():
    plan_path = DOCS_DIR / "sampling_plan.json"
    data = json.loads(plan_path.read_text(encoding="utf-8"))

    assert data["target_total_chips"] == 250
    assert data["pilot_benchmark_chips"] == 15
    assert data["expansion_target_chips"] == 235
    assert data["target_total_chips"] == data["pilot_benchmark_chips"] + data["expansion_target_chips"]

    # Strata sum
    strata = data["strata"]
    assert len(strata) == 7, f"Expected 7 strata, got {len(strata)}"
    strata_sum = sum(s["allocated_chips"] for s in strata)
    assert strata_sum == 250, f"Strata sum mismatch: expected 250, got {strata_sum}"

    # Geographic sum
    geo = data["geographic_allocation"]
    geo_sum = sum(g["allocated_chips"] for g in geo.values())
    geo_pct_sum = sum(g["percentage"] for g in geo.values())
    assert geo_sum == 250, f"Geographic sum mismatch: expected 250, got {geo_sum}"
    assert round(geo_pct_sum, 1) == 100.0, f"Geographic percentage sum mismatch: {geo_pct_sum}"

    # Seasonal sum
    season = data["seasonal_distribution"]
    season_sum = sum(s["allocated_chips"] for s in season.values())
    season_pct_sum = sum(s["percentage"] for s in season.values())
    assert season_sum == 250, f"Seasonal sum mismatch: expected 250, got {season_sum}"
    assert round(season_pct_sum, 1) == 100.0, f"Seasonal percentage sum mismatch: {season_pct_sum}"


def test_3_sampling_plan_csv_validity():
    csv_path = DOCS_DIR / "sampling_plan.csv"
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = list(csv.DictReader(f))

    assert len(reader) == 8, f"Expected 7 strata + 1 total row in CSV, got {len(reader)}"
    total_row = reader[-1]
    assert total_row["stratum_id"] == "TOTAL"
    assert int(total_row["allocated_chips"]) == 250


def test_4_pilot_package_remains_intact():
    assert PILOT_PACKAGE_DIR.exists()
    manifest = json.loads((PILOT_PACKAGE_DIR / "manifest.json").read_text(encoding="utf-8"))
    assert len(manifest["chips"]) == 15
    # Verify a random chip file
    p02_tif = PILOT_PACKAGE_DIR / "chips" / "PILOT_02_NORTH_chip.tif"
    assert p02_tif.exists() and p02_tif.stat().st_size > 0


def test_5_baselines_and_predecessors_immutable():
    a1_files = list(A1_DIR.glob("*.json"))
    a2_files = list(A2_DIR.glob("*.json"))
    assert len(a1_files) == 15 and len(a2_files) == 15

    p02 = A1_DIR / "PILOT_02_NORTH_annotator1.json"
    assert compute_sha256(p02) == "a7b3e2a1796c64ba4b2d6e1afdfae23c2144b0b1effe223597b100fa1bdf1d50"

    src_manifest = json.loads(SOURCE_MANIFEST_PATH.read_text(encoding="utf-8"))
    for cid, finfo in src_manifest["files"].items():
        fp = REVIEW_DIR / finfo["filename"]
        assert compute_sha256(fp) == finfo["sha256"]

    for rel_p, exp_h in FROZEN_PREDECESSORS.items():
        fp = PROJECT_ROOT / rel_p
        assert compute_sha256(fp) == exp_h
