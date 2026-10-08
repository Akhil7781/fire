import hashlib
import json
from pathlib import Path
import sys
import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.ds08_annotation_tool import validate_annotation_payload

FINAL_DIR = PROJECT_ROOT / "data" / "reference" / "ds08" / "annotations" / "final"
DRAFT_DIR = PROJECT_ROOT / "data" / "reference" / "ds08" / "annotations" / "draft"
REVIEW_DIR = PROJECT_ROOT / "data" / "reference" / "ds08" / "annotations" / "review"

FROZEN_ARTIFACTS = {
    "models/tcn/best_tcn.pt": "dfa2decb772cf71b65601a4cb83a12b73ee1706ff47e2acb23a9f53c84506f16",
    "models/deep_sad/best_deep_sad.pt": "a7f99f521cf56e3d651101259543f967eee535df82736aae3ae4271922947eaa",
    "models/yolo/infrastructure/best_infrastructure.pt": "bad5d3942f469b74a7778762696bb390174619cb0f403dbcc93be1066ba5dcf6",
    "models/yolo/fire_smoke/best_fire_smoke.pt": "29ab42eda1cd05d7141525927ab1c502c249082b5b2bbf5f2e0c9e8847c3d227",
    "data/embeddings/fusion/india_2025_tcn_sad_aligned.parquet": "49505cb4705516aef8d77af628debc485be894fae75dc19e3269b3ba6df7e931",
}


def compute_sha256(filepath: Path) -> str:
    sha = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            sha.update(chunk)
    return sha.hexdigest()


def test_final_adjudicated_files_count_and_naming():
    """Verify that final/ contains EXACTLY the 3 adjudicated chips and no others."""
    assert FINAL_DIR.exists(), f"{FINAL_DIR} does not exist"
    final_files = sorted(list(FINAL_DIR.glob("*.json")))
    expected_filenames = [
        "PILOT_01_NORTH_adjudicated_v1.json",
        "PILOT_13_EAST_adjudicated_v1.json",
        "PILOT_17_WEST_adjudicated_v1.json",
    ]
    assert len(final_files) == 3, f"Expected exactly 3 adjudicated files, found {len(final_files)}: {[f.name for f in final_files]}"
    assert [f.name for f in final_files] == expected_filenames


def test_original_draft_annotations_unmodified():
    """Verify that draft/annotator_1 and draft/annotator_2 still contain exactly their 5 files."""
    a1_dir = DRAFT_DIR / "annotator_1"
    a2_dir = DRAFT_DIR / "annotator_2"
    assert a1_dir.exists() and a2_dir.exists()

    a1_files = sorted([f.name for f in a1_dir.glob("*.json")])
    a2_files = sorted([f.name for f in a2_dir.glob("*.json")])

    expected_chips = [
        "PILOT_01_NORTH",
        "PILOT_05_CENTRAL",
        "PILOT_09_SOUTH",
        "PILOT_13_EAST",
        "PILOT_17_WEST",
    ]
    for c in expected_chips:
        assert (a1_dir / f"{c}_annotator1.json").exists(), f"Missing {c}_annotator1.json"
        assert (a2_dir / f"{c}_annotator2.json").exists(), f"Missing {c}_annotator2.json"


def test_adjudicated_files_schema_compliance():
    """Verify that all 3 final adjudicated files strictly conform to the schema validator."""
    for chip_id in ["PILOT_01_NORTH", "PILOT_13_EAST", "PILOT_17_WEST"]:
        filepath = FINAL_DIR / f"{chip_id}_adjudicated_v1.json"
        assert filepath.exists(), f"File {filepath} missing"
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        valid, errors = validate_annotation_payload(data)
        assert valid, f"Validation failed for {chip_id}: {errors}"


def test_pilot_01_north_adjudication():
    """Verify specific adjudication outcomes for PILOT_01_NORTH."""
    filepath = FINAL_DIR / "PILOT_01_NORTH_adjudicated_v1.json"
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert data["chip_annotation_status"] == "NO_VISIBLE_TARGET"
    assert data["annotations"] == []
    assert data["chip_id"] == "PILOT_01_NORTH"


def test_pilot_13_east_adjudication():
    """Verify specific adjudication outcomes for PILOT_13_EAST."""
    filepath = FINAL_DIR / "PILOT_13_EAST_adjudicated_v1.json"
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert data["chip_annotation_status"] == "UNRESOLVED"
    assert len(data["annotations"]) == 1
    ann = data["annotations"][0]
    assert ann["class_name"] == "UNRESOLVED"
    assert ann["class_id"] == 0
    assert ann["geometry_confidence"] == "LOW"
    assert ann["source_class_confidence"] == "LOW"
    assert ann["bbox"] == {"x_min": 225, "y_min": 225, "x_max": 290, "y_max": 290}
    assert "FOREST_CONTEXT_VISIBLE" in ann["visual_evidence"]
    assert "NO_CLEAR_VISUAL_EVIDENCE" in ann["visual_evidence"]


def test_pilot_17_west_adjudication():
    """Verify specific adjudication outcomes for PILOT_17_WEST."""
    filepath = FINAL_DIR / "PILOT_17_WEST_adjudicated_v1.json"
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert data["chip_annotation_status"] == "HAS_ANNOTATIONS"
    assert len(data["annotations"]) == 1
    ann = data["annotations"][0]
    assert ann["class_name"] == "Agricultural Fire"
    assert ann["class_id"] == 3
    assert ann["geometry_confidence"] == "HIGH"
    assert ann["source_class_confidence"] == "HIGH"
    assert ann["bbox"] == {"x_min": 166, "y_min": 243, "x_max": 199, "y_max": 269}
    assert "DIRECT_FIRE_VISIBLE" in ann["visual_evidence"]
    assert "CROPLAND_CONTEXT_VISIBLE" in ann["visual_evidence"]
    assert "BURN_SCAR_VISIBLE" in ann["visual_evidence"]


def test_adjudication_record_and_summary_exist():
    """Verify adjudication record JSON and summary markdown exist and contain required keys."""
    rec_path = REVIEW_DIR / "adjudication_v1.json"
    summary_path = REVIEW_DIR / "pilot_adjudication_summary_v1.md"

    assert rec_path.exists(), f"{rec_path} missing"
    assert summary_path.exists(), f"{summary_path} missing"

    with open(rec_path, "r", encoding="utf-8") as f:
        rec = json.load(f)

    assert rec["status"] == "STAGE_8.10B_PILOT_ADJUDICATION_COMPLETE"
    assert rec["adjudicated_chips_count"] == 3
    assert "disputed_chips_adjudicated" in rec
    assert len(rec["disputed_chips_adjudicated"]) == 3

    # Protocol evaluations
    evals = rec["protocol_proposals_evaluation"]
    assert evals["proposal_a"]["decision"] == "DEFER"
    assert evals["proposal_a"]["policy_status"] == "ASSOCIATION_RADIUS_POLICY = NOT_YET_FROZEN"
    assert evals["proposal_b"]["decision"] == "REJECT"
    assert evals["proposal_b"]["policy_status"] == "MONTANE_B12_THRESHOLD_POLICY = REJECTED_AS_MANDATORY_CRITERION"

    # Protocol versioning
    assert evals["protocol_versioning"]["version_decision"] == "NO_PROTOCOL_CHANGE_REQUIRED"
    assert evals["protocol_versioning"]["protocol_version"] == "v1.0"


def test_no_model_predictions_as_ground_truth():
    """Verify no YOLO / ML inference predictions used as ground truth."""
    for chip_id in ["PILOT_01_NORTH", "PILOT_13_EAST", "PILOT_17_WEST"]:
        filepath = FINAL_DIR / f"{chip_id}_adjudicated_v1.json"
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
        assert "yolo" not in content.lower()
        assert "tcn" not in content.lower()
        assert "deep_sad" not in content.lower()


def test_frozen_predecessors_unmodified():
    """Verify that all frozen model weights and fusion parquet files remain byte-for-byte identical."""
    for rel_path, expected_hash in FROZEN_ARTIFACTS.items():
        full_path = PROJECT_ROOT / rel_path
        assert full_path.exists(), f"Predecessor artifact missing: {rel_path}"
        actual_hash = compute_sha256(full_path)
        assert actual_hash == expected_hash, f"Hash mismatch for {rel_path}: expected {expected_hash}, got {actual_hash}"


def test_pilot_09_south_pre_agreed_forest_fire():
    """Verify PILOT_09_SOUTH was pre-agreed Forest Fire in drafts and NOT adjudicated."""
    a1_path = DRAFT_DIR / "annotator_1" / "PILOT_09_SOUTH_annotator1.json"
    a2_path = DRAFT_DIR / "annotator_2" / "PILOT_09_SOUTH_annotator2.json"
    assert a1_path.exists() and a2_path.exists()

    with open(a1_path, "r", encoding="utf-8") as f:
        d1 = json.load(f)
    with open(a2_path, "r", encoding="utf-8") as f:
        d2 = json.load(f)

    assert d1["chip_annotation_status"] == "HAS_ANNOTATIONS"
    assert d2["chip_annotation_status"] == "HAS_ANNOTATIONS"
    assert len(d1["annotations"]) == 1
    assert len(d2["annotations"]) == 1
    assert d1["annotations"][0]["class_name"] == "Forest Fire"
    assert d1["annotations"][0]["class_id"] == 2
    assert d2["annotations"][0]["class_name"] == "Forest Fire"
    assert d2["annotations"][0]["class_id"] == 2

    # Verify PILOT_09_SOUTH is NOT in final/
    final_p09 = list(FINAL_DIR.glob("*PILOT_09*"))
    assert len(final_p09) == 0, f"PILOT_09_SOUTH should NOT have files in final/, found: {final_p09}"


def test_five_chip_authoritative_distribution():
    """Verify the 5-chip post-adjudication cohort matches authoritative labels."""
    # 1. PILOT_01_NORTH (adjudicated)
    with open(FINAL_DIR / "PILOT_01_NORTH_adjudicated_v1.json", "r", encoding="utf-8") as f:
        p01 = json.load(f)
    assert p01["chip_annotation_status"] == "NO_VISIBLE_TARGET"

    # 2. PILOT_05_CENTRAL (pre-agreed in draft)
    with open(DRAFT_DIR / "annotator_1" / "PILOT_05_CENTRAL_annotator1.json", "r", encoding="utf-8") as f:
        p05 = json.load(f)
    assert p05["chip_annotation_status"] == "NO_VISIBLE_TARGET"

    # 3. PILOT_09_SOUTH (pre-agreed in draft)
    with open(DRAFT_DIR / "annotator_1" / "PILOT_09_SOUTH_annotator1.json", "r", encoding="utf-8") as f:
        p09 = json.load(f)
    assert p09["annotations"][0]["class_name"] == "Forest Fire"

    # 4. PILOT_13_EAST (adjudicated)
    with open(FINAL_DIR / "PILOT_13_EAST_adjudicated_v1.json", "r", encoding="utf-8") as f:
        p13 = json.load(f)
    assert p13["chip_annotation_status"] == "UNRESOLVED"
    assert p13["annotations"][0]["class_name"] == "UNRESOLVED"

    # 5. PILOT_17_WEST (adjudicated)
    with open(FINAL_DIR / "PILOT_17_WEST_adjudicated_v1.json", "r", encoding="utf-8") as f:
        p17 = json.load(f)
    assert p17["annotations"][0]["class_name"] == "Agricultural Fire"

    # Class distribution check
    counts = {
        "Forest Fire": 1,
        "Agricultural Fire": 1,
        "Industrial Fire": 0,
        "Other Thermal Source / Persistent Non-Biomass Thermal Source": 0,
        "NO_VISIBLE_TARGET": 2,
        "UNRESOLVED": 1,
    }
    assert counts["Forest Fire"] == 1
    assert counts["Agricultural Fire"] == 1
    assert counts["Industrial Fire"] == 0
    assert counts["NO_VISIBLE_TARGET"] == 2
    assert counts["UNRESOLVED"] == 1


def test_scientific_wording_no_thermal_emission():
    """Verify B12 BOA reflectance is not described as directly measured thermal emission."""
    for fname in ["adjudication_v1.json", "pilot_adjudication_summary_v1.md"]:
        fpath = REVIEW_DIR / fname
        assert fpath.exists()
        content = fpath.read_text(encoding="utf-8").lower()
        assert "thermal emission" not in content
        assert "thermal radiance" not in content

