"""
CLI runner for Stage 8.1: India-wide Frozen TCN Inference.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.models.tcn_inference import TCNIndiaInferencePipeline


def main():
    print("Initializing TCN India Inference Pipeline...")
    pipeline = TCNIndiaInferencePipeline(project_root=PROJECT_ROOT)
    summary = pipeline.run_inference()
    print("\nExecution Summary:")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
