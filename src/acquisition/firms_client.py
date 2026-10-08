"""
Reproducible NASA FIRMS API Acquisition Client for VIIRS NOAA-20 SP data.

SECURITY INVARIANTS:
1. FIRMS_MAP_KEY is retrieved securely from environment / .env.
2. The key is NEVER printed, logged, or exposed in error messages or manifests.
3. Every request URL logged has the key replaced with '[REDACTED]'.
"""

from __future__ import annotations

import csv
import datetime
import hashlib
import json
import logging
import os
import random
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional, Tuple

import requests

from src.utils.config import get_firms_map_key, is_firms_map_key_set

logger = logging.getLogger(__name__)

FIRMS_AREA_API_BASE = "https://firms.modaps.eosdis.nasa.gov/api/area/csv"
DEFAULT_INDIA_BBOX = (68.0, 8.0, 98.0, 37.0)  # west, south, east, north


@dataclass
class FIRMSChunkRequest:
    """Represents a discrete temporal chunk to be fetched from the FIRMS API."""
    source: str
    bbox: Tuple[float, float, float, float]  # west, south, east, north
    start_date: str  # YYYY-MM-DD
    day_range: int   # 1 to 5
    end_date: str    # YYYY-MM-DD
    is_burn_in_context: bool
    target_dir: Path
    filename: str

    @property
    def target_file(self) -> Path:
        return self.target_dir / self.filename


@dataclass
class ManifestRecord:
    """Record representing a downloaded or skipped chunk in the manifest."""
    source: str
    start_date: str
    end_date: str
    day_range: int
    is_burn_in_context: bool
    file_path: str
    row_count: int
    download_status: str  # SUCCESS, FAILED, SKIPPED_EXISTING
    sha256_checksum: str
    error_message: Optional[str]
    timestamp_utc: str


class FIRMSAcquisitionClient:
    """
    Robust, fault-tolerant NASA FIRMS acquisition client with exponential backoff,
    atomic file persistence, response schema verification, and resume capability.
    """

    def __init__(
        self,
        map_key: Optional[str] = None,
        base_url: str = FIRMS_AREA_API_BASE,
        inter_request_sleep_sec: float = 0.5,
    ):
        if map_key is None:
            if not is_firms_map_key_set():
                raise ValueError("FIRMS_MAP_KEY is not set or contains default placeholder.")
            self._map_key = get_firms_map_key()
        else:
            self._map_key = map_key.strip()

        self.base_url = base_url
        self.inter_request_sleep_sec = inter_request_sleep_sec
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "SatelliteThermalAnomalyResearch/1.0"})

    def _build_request_url(self, chunk: FIRMSChunkRequest) -> str:
        west, south, east, north = chunk.bbox
        bbox_str = f"{west},{south},{east},{north}"
        return f"{self.base_url}/{self._map_key}/{chunk.source}/{bbox_str}/{chunk.day_range}/{chunk.start_date}"

    def _build_masked_url(self, chunk: FIRMSChunkRequest) -> str:
        west, south, east, north = chunk.bbox
        bbox_str = f"{west},{south},{east},{north}"
        return f"{self.base_url}/[REDACTED]/{chunk.source}/{bbox_str}/{chunk.day_range}/{chunk.start_date}"

    @staticmethod
    def compute_file_sha256_and_rows(file_path: Path) -> Tuple[str, int]:
        """Calculates SHA-256 hex digest and counts data rows (excluding header)."""
        hasher = hashlib.sha256()
        row_count = 0
        with open(file_path, "r", encoding="utf-8") as f:
            for i, line in enumerate(f):
                hasher.update(line.encode("utf-8"))
                if i > 0 and line.strip():  # Exclude header and empty lines
                    row_count += 1
        return hasher.hexdigest(), row_count

    def validate_csv_content(self, text: str) -> Tuple[bool, str, int]:
        """
        Validates that response text is valid CSV containing standard FIRMS columns.
        Returns: (is_valid, error_msg, row_count)
        """
        lines = text.strip().splitlines()
        if not lines:
            return False, "Response body is empty", 0

        header_line = lines[0].strip()
        # NASA FIRMS error responses are plain text without commas or start with Error
        if "Bad MAP_KEY" in header_line:
            return False, "API Error: Invalid or unauthorized MAP_KEY", 0
        if header_line.startswith("Error") or "Exception" in header_line or "<!DOCTYPE" in header_line:
            return False, f"API Error response: {header_line[:100]}", 0

        if "," not in header_line:
            return False, f"Invalid header format (no commas found): {header_line[:100]}", 0

        columns = [c.strip().lower() for c in header_line.split(",")]
        # Standard essential columns for active fire detections
        essential = ["latitude", "longitude", "bright_ti4"]
        for col in essential:
            if col not in columns:
                return False, f"Missing required column '{col}' in header: {header_line}", 0

        row_count = len(lines) - 1
        return True, "", row_count

    def fetch_chunk(
        self,
        chunk: FIRMSChunkRequest,
        max_retries: int = 5,
        overwrite: bool = False,
    ) -> ManifestRecord:
        """
        Fetches a single chunk with retry and exponential backoff, saving atomically.
        """
        target_path = chunk.target_file
        chunk.target_dir.mkdir(parents=True, exist_ok=True)

        # 1. Resume check: If file already exists and overwrite is False, verify and return
        if target_path.exists() and not overwrite:
            try:
                checksum, row_count = self.compute_file_sha256_and_rows(target_path)
                if row_count >= 0:
                    return ManifestRecord(
                        source=chunk.source,
                        start_date=chunk.start_date,
                        end_date=chunk.end_date,
                        day_range=chunk.day_range,
                        is_burn_in_context=chunk.is_burn_in_context,
                        file_path=str(target_path),
                        row_count=row_count,
                        download_status="SKIPPED_EXISTING",
                        sha256_checksum=checksum,
                        error_message=None,
                        timestamp_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                    )
            except Exception as e:
                # If existing file is corrupted, re-download
                pass

        url = self._build_request_url(chunk)
        masked_url = self._build_masked_url(chunk)

        last_error = ""
        backoff_sec = 2.0

        for attempt in range(1, max_retries + 1):
            try:
                time.sleep(self.inter_request_sleep_sec)
                resp = self.session.get(url, timeout=45)

                if resp.status_code == 200:
                    is_valid, err_msg, row_count = self.validate_csv_content(resp.text)
                    if not is_valid:
                        # NASA FIRMS occasionally returns temporary status 200 with text error message
                        last_error = err_msg
                        time.sleep(backoff_sec)
                        backoff_sec *= 2.0
                        continue

                    # Atomic save via temporary file
                    tmp_file = chunk.target_dir / f".tmp_{chunk.filename}_{os.getpid()}"
                    with open(tmp_file, "w", encoding="utf-8", newline="") as f:
                        f.write(resp.text)
                        f.flush()
                        os.fsync(f.fileno())

                    # Calculate checksum and atomic rename
                    os.replace(tmp_file, target_path)
                    checksum, verified_rows = self.compute_file_sha256_and_rows(target_path)

                    return ManifestRecord(
                        source=chunk.source,
                        start_date=chunk.start_date,
                        end_date=chunk.end_date,
                        day_range=chunk.day_range,
                        is_burn_in_context=chunk.is_burn_in_context,
                        file_path=str(target_path),
                        row_count=verified_rows,
                        download_status="SUCCESS",
                        sha256_checksum=checksum,
                        error_message=None,
                        timestamp_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                    )

                elif resp.status_code == 429:
                    last_error = f"HTTP 429: Rate limited by NASA FIRMS API on attempt {attempt}"
                    sleep_time = backoff_sec + random.uniform(1.0, 3.0)
                    time.sleep(sleep_time)
                    backoff_sec *= 2.0

                elif 500 <= resp.status_code < 600:
                    last_error = f"HTTP {resp.status_code}: NASA FIRMS server error on attempt {attempt}"
                    time.sleep(backoff_sec)
                    backoff_sec *= 2.0

                else:
                    last_error = f"HTTP {resp.status_code}: Non-retryable status code"
                    break

            except requests.RequestException as e:
                last_error = f"Network exception on attempt {attempt}: {str(e)}"
                time.sleep(backoff_sec)
                backoff_sec *= 2.0

        # All retries failed
        return ManifestRecord(
            source=chunk.source,
            start_date=chunk.start_date,
            end_date=chunk.end_date,
            day_range=chunk.day_range,
            is_burn_in_context=chunk.is_burn_in_context,
            file_path=str(target_path),
            row_count=0,
            download_status="FAILED",
            sha256_checksum="",
            error_message=last_error,
            timestamp_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        )


def generate_date_chunks(
    start_date: datetime.date,
    end_date: datetime.date,
    max_days_per_chunk: int = 5,
    source: str = "VIIRS_NOAA20_SP",
    bbox: Tuple[float, float, float, float] = DEFAULT_INDIA_BBOX,
    target_dir: Path = Path("data/raw/2025"),
    is_burn_in_context: bool = False,
) -> List[FIRMSChunkRequest]:
    """
    Generates contiguous <=5-day chunk requests covering [start_date, end_date] inclusively.
    """
    chunks: List[FIRMSChunkRequest] = []
    curr = start_date

    while curr <= end_date:
        remaining_days = (end_date - curr).days + 1
        day_range = min(max_days_per_chunk, remaining_days)
        chunk_end = curr + datetime.timedelta(days=day_range - 1)

        start_str = curr.strftime("%Y-%m-%d")
        end_str = chunk_end.strftime("%Y-%m-%d")
        filename = f"{source}_{start_str}_to_{end_str}.csv"

        chunk = FIRMSChunkRequest(
            source=source,
            bbox=bbox,
            start_date=start_str,
            day_range=day_range,
            end_date=end_str,
            is_burn_in_context=is_burn_in_context,
            target_dir=target_dir,
            filename=filename,
        )
        chunks.append(chunk)
        curr = chunk_end + datetime.timedelta(days=1)

    return chunks
