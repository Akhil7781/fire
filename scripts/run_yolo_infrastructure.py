"""
CLI runner for Stage 8.3: YOLOv8n Infrastructure Vision Branch (DS06 DIOR).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.models.yolo_infrastructure import YOLOInfrastructurePipeline


def main():
    print("================================================================")
    print("STAGE 8.3: YOLO INFRASTRUCTURE BRANCH (DS06 DIOR)")
    print("================================================================")
    pipeline = YOLOInfrastructurePipeline(project_root=PROJECT_ROOT)
    results = pipeline.run_full_pipeline()
    print("\nStage 8.3 Execution Summary:")
    print(json.dumps(results, indent=2))
    print("\nSTAGE 8.3 COMPLETED SUCCESSFULLY.")


if __name__ == "__main__":
    main()
