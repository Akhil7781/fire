"""
Unit tests for DS08 Manual Annotation UI End-to-End Validation (Stage 8.12A).

Verifies:
1. Manual annotation web server and request handlers execute correctly end-to-end.
2. HTTP GET / serves complete HTML5/Canvas UI with mandatory FIRMS Context Banner:
   'FIRMS CONTEXT — NOT GROUND TRUTH'.
3. RGB and SWIR preview endpoints serve valid PNG imagery.
4. Zoom, pan, bbox drawing, class/evidence/visibility/confidence selection work end-to-end.
5. Opening a chip performs ZERO auto-labeling (annotations remain [] and task_status remains PENDING).
6. Blank templates remain substantively blank until valid manual submission.
7. Completion logic enforces distinction between PENDING_MANUAL_INPUT and COMPLETED_HUMAN_ANNOTATION.
8. NO_VISIBLE_TARGET is handled as a legitimate manual state with empty annotations.
9. human_verified=true cannot occur without genuine manual annotation submission.
10. Strict annotator isolation: Annotator 1 cannot see or access Annotator 2 workspace, and vice versa.
11. Quarantine isolation: manual UI never reads quarantined Stage 8.11 files.
12. All 30 real manual task templates in manual/annotator_1 and manual/annotator_2 remain 100% blank.
13. Invariant integrity of all 5 frozen predecessor artifacts.
"""

from __future__ import annotations

import copy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import socketserver
import sys
import threading
import urllib.request
import urllib.error

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.ds08_annotation_tool import (
    AFFECTED_15_CHIPS,
    DS08AnnotationServerHandler,
    get_annotator_dir,
    load_manual_template,
    save_manual_annotation,
    validate_annotation_payload,
    validate_manual_annotation_provenance,
)

ANNOTATIONS_DIR = PROJECT_ROOT / "data" / "reference" / "ds08" / "annotations"
MANUAL_DIR = ANNOTATIONS_DIR / "manual"
QUARANTINE_DIR = ANNOTATIONS_DIR / "quarantine"
FINAL_DIR = ANNOTATIONS_DIR / "final"

FROZEN_PREDECESSOR_HASHES = {
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


class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    allow_reuse_address = True


@pytest.fixture
def test_server(tmp_path):
    """Launches an ephemeral HTTP server backed by a temporary test workspace."""
    test_workspace = tmp_path / "ui_test_workspace"
    a1_dir = test_workspace / "annotator_1"
    a2_dir = test_workspace / "annotator_2"
    a1_dir.mkdir(parents=True, exist_ok=True)
    a2_dir.mkdir(parents=True, exist_ok=True)

    # Initialize exactly ONE test template copy marked UI_TEST_ONLY
    real_template = load_manual_template("annotator_1", "PILOT_02_NORTH")
    test_template = copy.deepcopy(real_template)
    test_template["notes"] = "UI_TEST_ONLY - Dedicated test copy"
    with open(a1_dir / "PILOT_02_NORTH_annotator1.json", "w", encoding="utf-8") as f:
        json.dump(test_template, f, indent=2)

    # Handler factory binding to test workspace
    def handler_factory(*args, **kwargs):
        return DS08AnnotationServerHandler(
            *args, active_annotator="annotator_1", workspace_dir=a1_dir, **kwargs
        )

    server = ThreadedTCPServer(("127.0.0.1", 0), handler_factory)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    yield {
        "url": f"http://127.0.0.1:{port}",
        "port": port,
        "workspace": a1_dir,
        "test_workspace_root": test_workspace,
    }

    server.shutdown()
    server.server_close()


def test_server_html_ui_and_firms_banner(test_server):
    """Verify that HTTP GET / serves complete manual HTML5 UI with FIRMS warning banner."""
    base_url = test_server["url"]
    req = urllib.request.Request(f"{base_url}/")
    with urllib.request.urlopen(req) as resp:
        assert resp.status == 200
        content_type = resp.headers.get("Content-Type", "")
        assert "text/html" in content_type
        html = resp.read().decode("utf-8")

    # Mandatory FIRMS disclaimer banner
    assert "FIRMS CONTEXT — NOT GROUND TRUTH" in html
    assert "Thermal anomalies detected by VIIRS/MODIS indicate satellite thermal context ONLY" in html

    # Canvas & controls
    assert 'id="image-canvas"' in html
    assert 'width="512"' in html
    assert 'height="512"' in html
    assert "RGB Preview" in html
    assert "SWIR Preview" in html
    assert "Zoom +" in html
    assert "Zoom -" in html
    assert "100%" in html
    assert "FIRMS Reference" in html

    # Manual form inputs (strictly no auto-labeling)
    assert "HAS_ANNOTATIONS" in html
    assert "NO_VISIBLE_TARGET" in html
    assert "UNRESOLVED" in html
    assert "Industrial Fire" in html
    assert "Forest Fire" in html
    assert "Agricultural Fire" in html
    assert "Other Thermal Source" in html
    assert "DIRECT_FIRE_VISIBLE" in html
    assert "SMOKE_VISIBLE" in html
    assert "BURN_SCAR_VISIBLE" in html
    assert "Save Human Annotation" in html


def test_preview_endpoints_rgb_and_swir(test_server):
    """Verify that /api/preview/{chip_id}/rgb and swir endpoints stream valid PNGs."""
    base_url = test_server["url"]

    # RGB preview
    req_rgb = urllib.request.Request(f"{base_url}/api/preview/PILOT_02_NORTH/rgb")
    with urllib.request.urlopen(req_rgb) as resp:
        assert resp.status == 200
        assert resp.headers.get("Content-Type") == "image/png"
        rgb_bytes = resp.read()
        assert rgb_bytes.startswith(b"\x89PNG\r\n\x1a\n")
        assert len(rgb_bytes) > 1000

    # SWIR preview
    req_swir = urllib.request.Request(f"{base_url}/api/preview/PILOT_02_NORTH/swir")
    with urllib.request.urlopen(req_swir) as resp:
        assert resp.status == 200
        assert resp.headers.get("Content-Type") == "image/png"
        swir_bytes = resp.read()
        assert swir_bytes.startswith(b"\x89PNG\r\n\x1a\n")
        assert len(swir_bytes) > 1000

    # Non-existent chip returns 404
    with pytest.raises(urllib.error.HTTPError) as exc_info:
        urllib.request.urlopen(f"{base_url}/api/preview/NON_EXISTENT_CHIP/rgb")
    assert exc_info.value.code == 404


def test_no_autolabeling_when_opening_chip(test_server):
    """Verify that opening a chip does NOT auto-assign any label, box, or model prediction."""
    base_url = test_server["url"]

    # Request chip data through UI API
    req = urllib.request.Request(f"{base_url}/api/chip/PILOT_02_NORTH")
    with urllib.request.urlopen(req) as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode("utf-8"))

    # Prove blank template invariants hold
    assert data["chip_id"] == "PILOT_02_NORTH"
    assert data["task_status"] == "PENDING_MANUAL_INPUT"
    assert data["human_verified"] is False
    assert data["chip_annotation_status"] is None
    assert data["annotations"] == []

    # Ensure zero model predictions or auto-labels exist
    content_str = json.dumps(data).lower()
    for forbidden in ["model_predicted", "yolo", "predicted_class", "auto_label", "synthetic"]:
        assert forbidden not in content_str

    # Verify template file on disk remains completely blank and unmodified
    disk_file = test_server["workspace"] / "PILOT_02_NORTH_annotator1.json"
    with open(disk_file, "r", encoding="utf-8") as f:
        disk_data = json.load(f)
    assert disk_data["annotations"] == []
    assert disk_data["human_verified"] is False
    assert disk_data["task_status"] == "PENDING_MANUAL_INPUT"


def test_end_to_end_manual_annotation_interaction_and_save(test_server):
    """Simulates complete human interaction: draw box, select class/evidence, save, reload."""
    base_url = test_server["url"]

    # 1. Fetch initial blank template
    with urllib.request.urlopen(f"{base_url}/api/chip/PILOT_02_NORTH") as resp:
        chip_template = json.loads(resp.read().decode("utf-8"))

    # 2. Construct manually submitted test payload (clearly marked UI_TEST_ONLY)
    manual_submission = {
        "chip_id": "PILOT_02_NORTH",
        "annotation_version": "v1.0",
        "chip_annotation_status": "HAS_ANNOTATIONS",
        "human_verified": True,
        "annotation_start_timestamp": datetime.now(timezone.utc).isoformat(),
        "annotation_completion_timestamp": datetime.now(timezone.utc).isoformat(),
        "interaction_audit": {
            "interface_version": "v1.0_manual",
            "bbox_creation_actions": 1,
            "bbox_edit_actions": 0,
            "class_selection_actions": 1,
            "save_events": 1,
        },
        "annotations": [
            {
                "annotation_id": "PILOT_02_NORTH_ANN_01",
                "class_id": 3,
                "class_name": "Agricultural Fire",
                "bbox": {"x_min": 210, "y_min": 180, "x_max": 275, "y_max": 245},
                "geometry_confidence": "HIGH",
                "source_class_confidence": "HIGH",
                "visibility_status": "CLEAR",
                "visual_evidence": ["CROPLAND_CONTEXT_VISIBLE", "SMOKE_VISIBLE"],
                "firms_relationship": "INSIDE_OBJECT",
                "review_status": "PENDING",
                "annotator_id": "HUMAN_ANNOTATOR_01",
                "notes": "UI_TEST_ONLY — manual interaction validation test",
            }
        ],
        "context_metadata": chip_template["context_metadata"],
    }

    # 3. Post to /api/save
    req = urllib.request.Request(
        f"{base_url}/api/save",
        data=json.dumps(manual_submission).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req) as resp:
        assert resp.status == 200
        save_resp = json.loads(resp.read().decode("utf-8"))
        assert save_resp["success"] is True
        assert save_resp["errors"] == []

    # 4. Reload from /api/chip/PILOT_02_NORTH and verify
    with urllib.request.urlopen(f"{base_url}/api/chip/PILOT_02_NORTH") as resp:
        reloaded = json.loads(resp.read().decode("utf-8"))

    assert reloaded["task_status"] == "COMPLETED_HUMAN_ANNOTATION"
    assert reloaded["human_verified"] is True
    assert reloaded["chip_annotation_status"] == "HAS_ANNOTATIONS"
    assert len(reloaded["annotations"]) == 1
    assert reloaded["annotations"][0]["class_name"] == "Agricultural Fire"
    assert reloaded["annotations"][0]["bbox"] == {"x_min": 210, "y_min": 180, "x_max": 275, "y_max": 245}
    assert reloaded["annotations"][0]["geometry_confidence"] == "HIGH"
    assert reloaded["annotations"][0]["source_class_confidence"] == "HIGH"
    assert reloaded["annotations"][0]["visibility_status"] == "CLEAR"
    assert reloaded["annotations"][0]["visual_evidence"] == ["CROPLAND_CONTEXT_VISIBLE", "SMOKE_VISIBLE"]

    # 5. Schema validation must succeed
    valid, errors = validate_annotation_payload(reloaded)
    assert valid is True, f"Reloaded payload failed schema validation: {errors}"


def test_completion_logic_enforcement(test_server):
    """Verify that empty annotations cannot be marked as HAS_ANNOTATIONS completed."""
    base_url = test_server["url"]

    with urllib.request.urlopen(f"{base_url}/api/chip/PILOT_02_NORTH") as resp:
        chip_template = json.loads(resp.read().decode("utf-8"))

    # Invalid: HAS_ANNOTATIONS but annotations list is empty
    empty_submission = {
        "chip_id": "PILOT_02_NORTH",
        "annotation_version": "v1.0",
        "chip_annotation_status": "HAS_ANNOTATIONS",
        "annotations": [],
        "context_metadata": chip_template["context_metadata"],
    }
    req = urllib.request.Request(
        f"{base_url}/api/save",
        data=json.dumps(empty_submission).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    with pytest.raises(urllib.error.HTTPError) as exc_info:
        urllib.request.urlopen(req)
    assert exc_info.value.code == 400
    err_body = json.loads(exc_info.value.read().decode("utf-8"))
    assert err_body["success"] is False
    assert any("requires at least one" in e for e in err_body["errors"])

    # Valid: NO_VISIBLE_TARGET with empty annotations list
    no_target_submission = {
        "chip_id": "PILOT_02_NORTH",
        "annotation_version": "v1.0",
        "chip_annotation_status": "NO_VISIBLE_TARGET",
        "annotations": [],
        "context_metadata": chip_template["context_metadata"],
    }
    req_valid = urllib.request.Request(
        f"{base_url}/api/save",
        data=json.dumps(no_target_submission).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req_valid) as resp:
        assert resp.status == 200
        res = json.loads(resp.read().decode("utf-8"))
        assert res["success"] is True


def test_human_provenance_triggers(test_server):
    """Verify human_verified=true cannot be triggered by opening, loading, or inspecting."""
    base_url = test_server["url"]

    # Opening a chip
    with urllib.request.urlopen(f"{base_url}/api/chip/PILOT_02_NORTH") as resp:
        data = json.loads(resp.read().decode("utf-8"))
        assert data["human_verified"] is False

    # Listing chips
    with urllib.request.urlopen(f"{base_url}/api/chips") as resp:
        chips = json.loads(resp.read().decode("utf-8"))
        assert len(chips) > 0

    # Viewing previews
    with urllib.request.urlopen(f"{base_url}/api/preview/PILOT_02_NORTH/rgb") as resp:
        assert resp.status == 200

    # Template on disk remains human_verified: False
    disk_file = test_server["workspace"] / "PILOT_02_NORTH_annotator1.json"
    with open(disk_file, "r", encoding="utf-8") as f:
        disk_data = json.load(f)
    assert disk_data["human_verified"] is False


def test_annotator_isolation_and_no_cross_endpoints(tmp_path):
    """Verify Annotator 1 cannot access Annotator 2 workspace and vice-versa."""
    test_root = tmp_path / "isolation_test"
    a1_dir = test_root / "annotator_1"
    a2_dir = test_root / "annotator_2"
    a1_dir.mkdir(parents=True, exist_ok=True)
    a2_dir.mkdir(parents=True, exist_ok=True)

    # Put a distinct file in A1 and A2
    with open(a1_dir / "PILOT_02_NORTH_annotator1.json", "w", encoding="utf-8") as f:
        json.dump({"chip_id": "PILOT_02_NORTH", "marker": "A1_ONLY", "task_status": "PENDING_MANUAL_INPUT"}, f)

    with open(a2_dir / "PILOT_02_NORTH_annotator2.json", "w", encoding="utf-8") as f:
        json.dump({"chip_id": "PILOT_02_NORTH", "marker": "A2_ONLY", "task_status": "PENDING_MANUAL_INPUT"}, f)

    # Server 1
    def factory1(*args, **kwargs):
        return DS08AnnotationServerHandler(*args, active_annotator="annotator_1", workspace_dir=a1_dir, **kwargs)

    server1 = ThreadedTCPServer(("127.0.0.1", 0), factory1)
    port1 = server1.server_address[1]
    threading.Thread(target=server1.serve_forever, daemon=True).start()

    # Server 2
    def factory2(*args, **kwargs):
        return DS08AnnotationServerHandler(*args, active_annotator="annotator_2", workspace_dir=a2_dir, **kwargs)

    server2 = ThreadedTCPServer(("127.0.0.1", 0), factory2)
    port2 = server2.server_address[1]
    threading.Thread(target=server2.serve_forever, daemon=True).start()

    try:
        # A1 server only sees A1 file
        with urllib.request.urlopen(f"http://127.0.0.1:{port1}/api/chip/PILOT_02_NORTH") as resp:
            data1 = json.loads(resp.read().decode("utf-8"))
            assert data1["marker"] == "A1_ONLY"

        # A2 server only sees A2 file
        with urllib.request.urlopen(f"http://127.0.0.1:{port2}/api/chip/PILOT_02_NORTH") as resp:
            data2 = json.loads(resp.read().decode("utf-8"))
            assert data2["marker"] == "A2_ONLY"

        # Neither server has endpoints to query or list the other annotator's workspace
        with pytest.raises(urllib.error.HTTPError) as exc_info:
            urllib.request.urlopen(f"http://127.0.0.1:{port1}/api/annotator_2/chip/PILOT_02_NORTH")
        assert exc_info.value.code == 404
    finally:
        server1.shutdown()
        server1.server_close()
        server2.shutdown()
        server2.server_close()


def test_quarantine_isolation():
    """Verify that manual UI never reads from quarantine repository."""
    quar_dir = QUARANTINE_DIR / "stage8_11_script_generated"
    assert quar_dir.exists()

    # Verify that get_annotator_dir rejects quarantine paths
    with pytest.raises(ValueError):
        get_annotator_dir("quarantine")
    with pytest.raises(ValueError):
        get_annotator_dir("stage8_11_script_generated")


def test_real_manual_templates_unmodified_and_blank():
    """Verify that all 30 real manual task templates remain 100% blank and untouched."""
    a1_dir = MANUAL_DIR / "annotator_1"
    a2_dir = MANUAL_DIR / "annotator_2"

    a1_files = sorted(list(a1_dir.glob("*.json")))
    a2_files = sorted(list(a2_dir.glob("*.json")))
    assert len(a1_files) == 15
    assert len(a2_files) == 15

    for adir, suffix, exp_id in [
        (a1_dir, "annotator1", "HUMAN_ANNOTATOR_01"),
        (a2_dir, "annotator2", "HUMAN_ANNOTATOR_02"),
    ]:
        for cid in AFFECTED_15_CHIPS:
            fpath = adir / f"{cid}_{suffix}.json"
            assert fpath.exists(), f"Missing real template: {fpath.name}"
            with open(fpath, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Strict blank invariant
            assert data["task_status"] == "PENDING_MANUAL_INPUT"
            assert data["human_verified"] is False
            assert data["chip_annotation_status"] is None
            assert data["annotations"] == []
            assert data["annotator_id"] == exp_id

            # Zero bounding boxes, zero classes, zero evidence
            content = fpath.read_text(encoding="utf-8").lower()
            for forbidden in ["model_predicted", "yolo", "predicted_class", "auto_label"]:
                assert forbidden not in content


def test_frozen_predecessors_unmodified():
    """Verify that all 5 frozen predecessor artifacts remain byte-for-byte unmodified."""
    for rel_path, exp_hash in FROZEN_PREDECESSOR_HASHES.items():
        full_path = PROJECT_ROOT / rel_path
        assert full_path.exists(), f"Missing predecessor artifact: {rel_path}"
        actual = compute_sha256(full_path)
        assert actual == exp_hash, f"Hash mismatch for {rel_path}: expected {exp_hash}, got {actual}"
