import hashlib
import json
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

OUT = PROJECT_ROOT / "artifacts/stage8_43"


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_only_confident_stage834_development_events_are_in_ledger():
    trusted = pd.read_parquet(PROJECT_ROOT / "artifacts/stage8_34/trusted_development_cohort.parquet")
    ledger = pd.read_csv(OUT / "eligible_event_provenance.csv")
    manifest = json.loads((OUT / "persistence_expert_development_manifest.json").read_text())
    assert len(trusted) == 131 and trusted.event_id.is_unique
    assert ledger.event_id.is_unique
    assert set(ledger.event_id).issubset(set(trusted.event_id))
    assert set(ledger.label_confidence) == {"LABEL_CONFIDENT"}
    assert ledger.history_coverage_status.str.startswith("UNAVAILABLE").all()
    assert len(ledger) == 99
    assert int((ledger.class_id == 3).sum()) == 24
    assert manifest["dataset_created"] is False
    assert manifest["record_count"] == 0
    assert manifest["status"] == "NOT_READY_FOR_MODELING"


def test_persistent_t0_is_not_taken_from_fixed_event_start_metadata():
    ledger = pd.read_csv(OUT / "eligible_event_provenance.csv")
    persistent = ledger[ledger.class_id == 3]
    assert persistent.t0.isna().all()
    assert persistent.metadata_event_start.astype(str).str.startswith("2018-03-15").all()
    assert persistent.t0_status.str.startswith("UNVERIFIED").all()


def test_raw_inventory_excludes_2026_and_records_hashes():
    inv = json.loads((OUT / "raw_source_inventory.json").read_text())
    assert inv["summary"]["annual_2025_file_count"] == 73
    assert inv["summary"]["event_window_file_count"] == 90
    assert all("2026" not in row["relative_path"] for row in inv["files"])
    assert all(len(row["sha256"]) == 64 for row in inv["files"])


def test_invalid_events_are_listed_with_exact_stage_reason():
    excluded = pd.read_csv(OUT / "excluded_events.csv")
    counts = excluded.groupby("cohort_origin").size().to_dict()
    assert counts == {"STAGE_8_34_CANONICAL": 32, "STAGE_8_35_EXPANSION": 18}
    generated = excluded[excluded.cohort_origin == "STAGE_8_35_EXPANSION"]
    assert generated.event_id.is_unique
    assert generated.exclusion_reason.str.contains("fixed thermal and recurrence values").all()


def test_cross_split_spatial_overlap_is_recorded_and_blocks_readiness():
    manifest = json.loads((OUT / "persistence_expert_development_manifest.json").read_text())
    pairs = pd.read_csv(OUT / "closest_development_event_pairs.csv")
    near = pairs[(pairs.distance_km <= 5) & (~pairs.same_split)]
    assert len(near) == 2
    assert near.same_spatial_component.all()
    assert manifest["status"] == "NOT_READY_FOR_MODELING"


def test_frozen_checkpoint_and_counter_are_preserved():
    checkpoint = PROJECT_ROOT / "models/stage8_36/final_neural_model.pt"
    counter = PROJECT_ROOT / "artifacts/stage8_36/.test_eval_counter"
    assert sha256(checkpoint) == "5bdbfbd503a3c0acbd50caefd2b1c88b5e0190a7176d70a517165814722bcff2"
    assert counter.read_text().strip() == "1"
    assert not (PROJECT_ROOT / "data/interim/persistence_expert_development.parquet").exists()
