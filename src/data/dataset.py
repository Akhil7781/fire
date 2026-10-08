"""
Dataset definitions and loading stubs for NASA FIRMS VIIRS NOAA-20 dataset.

Dataset Specification:
- Platform: NOAA-20 (JPSS-1)
- Instrument: VIIRS (375m active fire product)
- Processing: Standard Processing (2025-01-01 to 2025-12-31)
- Total Files: 73 CSV files
- Total Records: 1,024,996 detections
- Original Columns: 16 attributes
"""

from pathlib import Path
from typing import List, Optional


class FIRMSDataset:
    """
    Placeholder class for loading and managing the 2025 FIRMS VIIRS NOAA-20 dataset.
    Methodology and data structures will be implemented in subsequent project phases.
    """

    def __init__(self, data_dir: Path):
        self.data_dir = Path(data_dir)

    def list_raw_files(self) -> List[Path]:
        """Returns sorted list of raw CSV files in data_dir without modifying them."""
        if not self.data_dir.exists():
            return []
        return sorted(self.data_dir.glob("*.csv"))

    def __len__(self) -> int:
        raise NotImplementedError("Dataset size implementation deferred to data phase.")
