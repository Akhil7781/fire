"""
CLI runner for Stage 8.4: YOLOv8n Fire/Smoke Vision Branch (DS07 FASDD_RS).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.models.yolo_fire_smoke import YOLOFireSmokePipeline


def main():
    print("================================================================")
    print("STAGE 8.4: YOLO FIRE/SMOKE VISION BRANCH (DS07 FASDD_RS)")
    print("================================================================")
    pipeline = YOLOFireSmokePipeline(project_root=PROJECT_ROOT)
    results = pipeline.run_full_pipeline()
    print("\nStage 8.4 Execution Summary:")
    print(json.dumps(results, indent=2))
    print("\nSTAGE 8.4 COMPLETED SUCCESSFULLY.")


if __name__ == "__main__":
    main()
