"""
Script to execute the complete label construction pipeline.
Supports full dataset execution as well as bounded sample validation slices.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.labeling.pipeline import LabelConstructionPipeline
from src.labeling.config import get_label_config


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the FIRMS Label Construction Pipeline")
    parser.add_argument(
        "--sample-size",
        type=int,
        default=None,
        help="Optional sample size for bounded slice validation (e.g. 5000)",
    )
    parser.add_argument(
        "--no-save",
        action="store_true",
        help="Do not save output parquet (dry run / test mode)",
    )
    args = parser.parse_args()

    config = get_label_config()
    pipeline = LabelConstructionPipeline(config=config)

    summary = pipeline.run(
        sample_size=args.sample_size,
        save_output=not args.no_save,
    )

    print("Execution finished with summary:", summary["class_distribution"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
