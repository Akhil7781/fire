"""
CLI runner for Stage 8.2: TCN + Deep SAD Representation Alignment.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.models.representation_alignment import RepresentationAlignmentPipeline


def main():
    print("================================================================")
    print("STAGE 8.2: TCN + DEEP SAD REPRESENTATION ALIGNMENT")
    print("================================================================")
    pipeline = RepresentationAlignmentPipeline(project_root=PROJECT_ROOT)
    summary = pipeline.run_alignment()
    print("\nExecution Summary:")
    print(json.dumps(summary, indent=2))
    print("\nSTAGE 8.2 COMPLETED SUCCESSFULLY.")


if __name__ == "__main__":
    main()
