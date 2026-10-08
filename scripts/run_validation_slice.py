"""
Validation slice execution script.
Runs the complete 6-stage preprocessing pipeline on a deterministic validation slice,
measures execution runtime and peak RAM, enforces all invariants, and exports artifacts.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd
from tests.test_preprocessing_slice import create_deterministic_validation_slice
from src.data.pipeline import PreprocessingPipeline


def main() -> int:
    print("\n" + "=" * 75)
    print("EXECUTING DETERMINISTIC PREPROCESSING VALIDATION SLICE")
    print("=" * 75)

    primary_df, context_df = create_deterministic_validation_slice()
    print(f"  Primary 2025 Slice Records:    {len(primary_df)}")
    print(f"  Context 2024 Q4 Burn-In Records: {len(context_df)}")

    output_dir = PROJECT_ROOT / "data" / "interim"
    pipeline = PreprocessingPipeline(output_dir=output_dir)

    print("\n  Executing Stages 0 through 6...")
    metrics = pipeline.run_on_dataframe(
        raw_2025_df=primary_df,
        context_burn_in_df=context_df,
        source_name_2025="validation_slice_india_2025.csv",
        source_name_context="burn_in_context_india_2024.csv",
    )

    # Save detailed metadata
    metadata_dir = PROJECT_ROOT / "data" / "processed"
    metadata_dir.mkdir(parents=True, exist_ok=True)
    metadata_file = metadata_dir / "slice_validation_report.json"
    with open(metadata_file, "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2)

    print("\n" + "=" * 75)
    print("VALIDATION SLICE EXECUTION COMPLETED")
    print("=" * 75)
    print(f"  Runtime:                {metrics['runtime_seconds']} seconds")
    print(f"  Peak Traced Memory:     {metrics['peak_memory_mb']} MB")
    print(f"  Total Output Columns:   {metrics['total_columns']}")
    print(f"  Parquet Output:         {metrics['output_path']}")
    print(f"  Metadata Report:        {metadata_file}")
    print("\n  Stage Row Counts:")
    for stage, count in metrics["stage_counts"].items():
        print(f"    - {stage:32s}: {count}")

    print("\n  Partition Distribution:")
    for partition, count in metrics["partition_distribution"].items():
        print(f"    - {partition:32s}: {count}")

    # Inspect output dataframe
    df = pd.read_parquet(metrics["output_path"])
    print("\n  Sample Output Columns:")
    print(f"    {list(df.columns[:10])} ... and {len(df.columns)-10} more.")

    print("\n[SUCCESS] Deterministic validation slice passed all invariant tests.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
