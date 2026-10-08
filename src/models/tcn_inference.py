"""
Stage 8.1: India-wide Frozen TCN Inference Pipeline.

Generates 64-dimensional latent temporal embeddings z_TCN for India 2025 FIRMS causal sequences
using the frozen 5-block 1D Dilated Causal TCN (models/tcn/best_tcn.pt) and the exact
scaler parameters from pretraining (models/tcn/scaler_params.json).

Architectural Invariants Strictly Preserved:
  1. Input Shape: (B, T=16, C=8)
  2. Channels:
     0: elapsed_time_hours
     1: geodesic_distance_km
     2: thermal_contrast_k
     3: frp_mw
     4: log1p_frp
     5: pixel_footprint_km2
     6: solar_zenith_deg
     7: daynight_flag
  3. Strict Causality:
     - For target observation t_i, all historical observations j satisfy t_j <= t_i.
     - Snapshot exclusion: t_i - t_j >= 900 s (15 minutes).
     - Lookback horizon: t_i - t_j <= 90 days (7,776,000 s).
     - Spatial context radius: d(x_i, x_j) <= 2.0 km.
     - Target timestamp = sequence endpoint (step 15).
     - Zero future observations.
  4. Active-Aware Pooling:
     - Left-only padding with zero vectors for histories < 16.
     - Masked pooling over active timesteps alone.
  5. State Isolation & Immutability:
     - TCN checkpoint is loaded with torch.no_grad() and eval() mode.
     - Zero checkpoint modification or retraining.
     - Scaler statistics loaded strictly from pretraining (no refitting).
"""

from __future__ import annotations

import bisect
import gc
import hashlib
import json
import math
import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import h3
import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import torch

PROJECT_ROOT = Path("d:/DATA PREPROCESSING")
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.models.tcn import TemporalConvolutionalNetwork
from src.training.tcn_dataset import ChannelScaler, ScalerParams

DEG2RAD = math.pi / 180.0


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Computes great-circle distance on spherical Earth in kilometers."""
    p1 = lat1 * DEG2RAD
    p2 = lat2 * DEG2RAD
    dp = (lat2 - lat1) * DEG2RAD
    dl = (lon2 - lon1) * DEG2RAD
    a = math.sin(dp * 0.5) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl * 0.5) ** 2
    return 12742.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))


def compute_solar_zenith_vectorized(
    lats: np.ndarray, lons: np.ndarray, dt_series: pd.Series
) -> np.ndarray:
    """
    Vectorized NOAA solar position equation.
    Matches src/labeling/ds02.py:calculate_solar_zenith bit-for-bit.
    """
    doy = dt_series.dt.dayofyear.to_numpy(dtype=np.float64)
    hour = (
        dt_series.dt.hour
        + dt_series.dt.minute / 60.0
        + dt_series.dt.second / 3600.0
    ).to_numpy(dtype=np.float64)
    gamma = 2.0 * np.pi / 365.0 * (doy - 1.0 + (hour - 12.0) / 24.0)

    eqtime = 229.18 * (
        0.000075
        + 0.001868 * np.cos(gamma)
        - 0.032077 * np.sin(gamma)
        - 0.014615 * np.cos(2.0 * gamma)
        - 0.040849 * np.sin(2.0 * gamma)
    )

    decl = (
        0.006918
        - 0.399912 * np.cos(gamma)
        + 0.070257 * np.sin(gamma)
        - 0.006758 * np.cos(2.0 * gamma)
        + 0.000907 * np.sin(2.0 * gamma)
        - 0.002697 * np.cos(3.0 * gamma)
        + 0.001480 * np.sin(3.0 * gamma)
    )

    time_offset = eqtime + 4.0 * lons
    tst = (hour * 60.0 + time_offset) % 1440.0
    ha = np.radians((tst / 4.0) - 180.0)
    lat_rad = np.radians(lats)

    cos_zenith = np.sin(lat_rad) * np.sin(decl) + np.cos(lat_rad) * np.cos(decl) * np.cos(ha)
    cos_zenith = np.clip(cos_zenith, -1.0, 1.0)
    return np.degrees(np.arccos(cos_zenith)).astype(np.float32)


class TCNIndiaInferencePipeline:
    """
    Executes India-wide frozen TCN inference for causal sequence embedding generation.
    """

    EXPECTED_PARAMS = 122498
    EXPECTED_DILATIONS = (1, 2, 4, 8, 16)
    EXPECTED_CHANNELS = 8
    EXPECTED_LATENT_DIM = 64
    EXPECTED_T = 16

    REQUIRED_COLUMNS = [
        "detection_id",
        "latitude",
        "longitude",
        "timestamp_utc",
        "acq_datetime_utc",
        "frp",
        "delta_t",
        "scan",
        "track",
        "pixel_area",
        "daynight",
        "h3_res8",
        "partition",
    ]

    def __init__(
        self,
        project_root: Path = PROJECT_ROOT,
        checkpoint_path: Optional[Path] = None,
        scaler_path: Optional[Path] = None,
        device: str = "cpu",
    ):
        self.project_root = Path(project_root)
        self.checkpoint_path = checkpoint_path or (
            self.project_root / "models" / "tcn" / "best_tcn.pt"
        )
        self.scaler_path = scaler_path or (
            self.project_root / "models" / "tcn" / "scaler_params.json"
        )
        self.device = torch.device(device)

        # Record initial checkpoint integrity digest
        with open(self.checkpoint_path, "rb") as f:
            self.initial_ckpt_sha256 = hashlib.sha256(f.read()).hexdigest()

        # Load and verify architecture
        self.model = self._load_and_verify_model()
        self.scaler = self._load_scaler()

    def _load_and_verify_model(self) -> TemporalConvolutionalNetwork:
        """Loads best_tcn.pt, validates architecture and parameter count."""
        assert self.checkpoint_path.exists(), f"Checkpoint missing: {self.checkpoint_path}"
        ckpt = torch.load(self.checkpoint_path, map_location=self.device)

        model = TemporalConvolutionalNetwork(
            in_channels=self.EXPECTED_CHANNELS,
            hidden_channels=64,
            dilations=self.EXPECTED_DILATIONS,
            latent_dim=self.EXPECTED_LATENT_DIM,
            dropout=0.0,
        ).to(self.device)

        model.load_state_dict(ckpt["model_state_dict"])
        model.eval()

        # Strict parameter count verification
        param_count = sum(p.numel() for p in model.parameters())
        assert (
            param_count == self.EXPECTED_PARAMS
        ), f"Parameter count mismatch: expected {self.EXPECTED_PARAMS}, got {param_count}"
        assert model.dilations == self.EXPECTED_DILATIONS
        assert len(model.network) == 5

        return model

    def _load_scaler(self) -> ChannelScaler:
        """Loads train-fitted ChannelScaler parameters."""
        assert self.scaler_path.exists(), f"Scaler params missing: {self.scaler_path}"
        with open(self.scaler_path, "r", encoding="utf-8") as f:
            params_dict = json.load(f)

        scaler = ChannelScaler()
        scaler.load_params(ScalerParams.from_dict(params_dict))
        return scaler

    def verify_checkpoint_immutability(self) -> None:
        """Verifies checkpoint file was NOT modified during inference."""
        with open(self.checkpoint_path, "rb") as f:
            current_hash = hashlib.sha256(f.read()).hexdigest()
        assert (
            current_hash == self.initial_ckpt_sha256
        ), "Checkpoint file was modified during inference execution!"

    def run_inference(
        self,
        input_parquet: Optional[Path] = None,
        output_parquet: Optional[Path] = None,
        chunk_size: int = 50000,
        batch_size: int = 2048,
    ) -> Dict:
        """
        Executes end-to-end India-wide TCN sequence generation and inference.
        Writes results to output_parquet in streaming chunks.
        """
        start_time = time.time()
        input_path = input_parquet or (
            self.project_root / "data" / "interim" / "causal_features_2025.parquet"
        )
        output_path = output_parquet or (
            self.project_root / "data" / "embeddings" / "tcn" / "india_2025_embeddings.parquet"
        )
        output_path.parent.mkdir(parents=True, exist_ok=True)

        print("=" * 80)
        print("STAGE 8.1: INDIA-WIDE FROZEN TCN INFERENCE")
        print("=" * 80)
        print(f"  Input Dataset:    {input_path}")
        print(f"  Output Parquet:   {output_path}")
        print(f"  TCN Checkpoint:   {self.checkpoint_path}")
        print(f"  Device:           {self.device}")
        print(f"  Chunk Size:       {chunk_size:,} detections")
        print(f"  Inference Batch:  {batch_size:,} sequences")

        # 1. Load Data with Column Projection
        t_load_start = time.time()
        print("\n[Step 1/5] Loading causal features with column projection...")
        df = pd.read_parquet(input_path, columns=self.REQUIRED_COLUMNS)
        n_total = len(df)
        print(f"  Loaded {n_total:,} rows x {len(df.columns)} columns in {time.time() - t_load_start:.2f}s")

        # Invariant checks on input dataset
        assert df["detection_id"].nunique() == n_total, "Duplicate detection_id found in input!"
        assert df["timestamp_utc"].is_monotonic_increasing, "Dataset is not temporally sorted!"

        # 2. Vectorized Feature Preparation
        t_prep_start = time.time()
        print("\n[Step 2/5] Computing vectorized instantaneous channel features...")
        lats = df["latitude"].to_numpy(dtype=np.float64)
        lons = df["longitude"].to_numpy(dtype=np.float64)
        timestamps = df["timestamp_utc"].to_numpy(dtype=np.int64)
        frp_arr = df["frp"].to_numpy(dtype=np.float32)
        log1p_frp_arr = np.log1p(frp_arr).astype(np.float32)
        delta_t_arr = df["delta_t"].to_numpy(dtype=np.float32)
        pixel_area_arr = df["pixel_area"].to_numpy(dtype=np.float32)
        daynight_flag_arr = (df["daynight"].to_numpy() == "D").astype(np.float32)
        h3_cells = df["h3_res8"].to_numpy()
        detection_ids = df["detection_id"].to_numpy()
        partitions = df["partition"].to_numpy()
        acq_datetimes = df["acq_datetime_utc"].to_numpy()

        solar_zenith_arr = compute_solar_zenith_vectorized(lats, lons, df["acq_datetime_utc"])
        print(f"  Features prepared in {time.time() - t_prep_start:.2f}s")

        # 3. Spatial Neighborhood Inverted Index
        t_idx_start = time.time()
        print("\n[Step 3/5] Building spatial cell inverted index...")
        cell_to_indices: Dict[str, List[int]] = {}
        for idx, cell in enumerate(h3_cells):
            if cell not in cell_to_indices:
                cell_to_indices[cell] = []
            cell_to_indices[cell].append(idx)
        print(
            f"  Indexed {len(cell_to_indices):,} unique H3 resolution 8 cells in {time.time() - t_idx_start:.2f}s"
        )

        # 4. Chunked Causal Sequence Construction & Model Inference
        print("\n[Step 4/5] Executing streaming chunk sequence construction & TCN inference...")
        t_inf_start = time.time()

        # Define output Parquet schema
        embedding_cols = [f"z_tcn_{i}" for i in range(self.EXPECTED_LATENT_DIM)]
        schema_fields = [
            pa.field("detection_id", pa.string()),
            pa.field("sequence_id", pa.string()),
            pa.field("acq_datetime_utc", pa.timestamp("ns", tz="UTC")),
            pa.field("timestamp_utc", pa.int64()),
            pa.field("partition", pa.string()),
            pa.field("active_timesteps", pa.int16()),
        ] + [pa.field(c, pa.float32()) for c in embedding_cols]
        output_schema = pa.schema(schema_fields)

        writer = pq.ParquetWriter(output_path, output_schema, compression="snappy")

        n_chunks = math.ceil(n_total / chunk_size)
        total_future_violations = 0
        total_nan_inf = 0
        total_processed = 0

        # Memory buffer for 3-ring disk caching
        disk_cache: Dict[str, List[str]] = {}

        for chunk_idx in range(n_chunks):
            c_start = chunk_idx * chunk_size
            c_end = min(c_start + chunk_size, n_total)
            c_len = c_end - c_start

            chunk_tensors = np.zeros((c_len, self.EXPECTED_T, self.EXPECTED_CHANNELS), dtype=np.float32)
            chunk_masks = np.zeros((c_len, self.EXPECTED_T), dtype=bool)
            active_counts = np.zeros(c_len, dtype=np.int16)

            # Sequence building loop for this chunk
            for local_idx, i in enumerate(range(c_start, c_end)):
                t_i = timestamps[i]
                lat_i = lats[i]
                lon_i = lons[i]
                cell_i = h3_cells[i]

                if cell_i not in disk_cache:
                    disk_cache[cell_i] = h3.grid_disk(cell_i, 3)
                disk = disk_cache[cell_i]

                t_min = t_i - 90 * 86400  # 90 days lookback limit
                t_max = t_i - 900          # 15 minutes snapshot exclusion

                candidates = []
                for neighbor in disk:
                    idxs = cell_to_indices.get(neighbor)
                    if not idxs:
                        continue
                    # Binary search on sorted detection indices in neighbor cell
                    r = bisect.bisect_right(idxs, i - 1)
                    if r == 0:
                        continue
                    for k in range(r - 1, -1, -1):
                        j = idxs[k]
                        tj = timestamps[j]
                        if tj > t_max:
                            continue
                        if tj < t_min:
                            break
                        # Strict causality invariant
                        if tj > t_i:
                            total_future_violations += 1
                            continue

                        # Check 2.0 km local causal context radius
                        dist_km = haversine_km(lat_i, lon_i, lats[j], lons[j])
                        if dist_km <= 2.0:
                            candidates.append((tj, j, dist_km))
                            if len(candidates) >= 30:  # Bound max candidates per detection
                                break

                # Sort candidates chronologically
                candidates.sort(key=lambda x: x[0])
                selected_prior = candidates[-15:]  # Up to 15 prior historical detections

                # Total active steps = prior + target observation (step 15)
                k_active = len(selected_prior) + 1
                active_counts[local_idx] = k_active
                pad = self.EXPECTED_T - k_active

                # Sequence start timestamp (earliest active observation)
                t_seq_start = selected_prior[0][0] if selected_prior else t_i

                # Populate historical timesteps (steps pad .. 14)
                for step_rel, (tj, j, dist_km) in enumerate(selected_prior):
                    step = pad + step_rel
                    chunk_tensors[local_idx, step, 0] = (tj - t_seq_start) / 3600.0
                    chunk_tensors[local_idx, step, 1] = dist_km
                    chunk_tensors[local_idx, step, 2] = delta_t_arr[j]
                    chunk_tensors[local_idx, step, 3] = frp_arr[j]
                    chunk_tensors[local_idx, step, 4] = log1p_frp_arr[j]
                    chunk_tensors[local_idx, step, 5] = pixel_area_arr[j]
                    chunk_tensors[local_idx, step, 6] = solar_zenith_arr[j]
                    chunk_tensors[local_idx, step, 7] = daynight_flag_arr[j]
                    chunk_masks[local_idx, step] = True

                # Populate target observation at sequence endpoint (step 15)
                chunk_tensors[local_idx, 15, 0] = (t_i - t_seq_start) / 3600.0
                chunk_tensors[local_idx, 15, 1] = 0.0  # Distance to self
                chunk_tensors[local_idx, 15, 2] = delta_t_arr[i]
                chunk_tensors[local_idx, 15, 3] = frp_arr[i]
                chunk_tensors[local_idx, 15, 4] = log1p_frp_arr[i]
                chunk_tensors[local_idx, 15, 5] = pixel_area_arr[i]
                chunk_tensors[local_idx, 15, 6] = solar_zenith_arr[i]
                chunk_tensors[local_idx, 15, 7] = daynight_flag_arr[i]
                chunk_masks[local_idx, 15] = True

            # Normalize using frozen training scaler
            norm_chunk_tensors = self.scaler.transform(chunk_tensors, chunk_masks)

            # Mini-batch TCN inference
            chunk_embeddings = np.zeros((c_len, self.EXPECTED_LATENT_DIM), dtype=np.float32)
            with torch.no_grad():
                for b_start in range(0, c_len, batch_size):
                    b_end = min(b_start + batch_size, c_len)
                    x_batch = torch.from_numpy(norm_chunk_tensors[b_start:b_end]).to(self.device)
                    m_batch = torch.from_numpy(chunk_masks[b_start:b_end]).to(self.device)
                    z_batch = self.model.encode(x_batch, padding_mask=m_batch).cpu().numpy()
                    chunk_embeddings[b_start:b_end] = z_batch

            # Check for NaN / Inf values
            nan_count = int(np.isnan(chunk_embeddings).sum())
            inf_count = int(np.isinf(chunk_embeddings).sum())
            if nan_count > 0 or inf_count > 0:
                total_nan_inf += nan_count + inf_count

            # Build PyArrow RecordBatch / Table and write
            chunk_seq_ids = [f"SEQ_IND_2025_{idx:07d}" for idx in range(c_start + 1, c_end + 1)]
            table_dict = {
                "detection_id": detection_ids[c_start:c_end],
                "sequence_id": chunk_seq_ids,
                "acq_datetime_utc": acq_datetimes[c_start:c_end],
                "timestamp_utc": timestamps[c_start:c_end],
                "partition": partitions[c_start:c_end],
                "active_timesteps": active_counts,
            }
            for col_idx, col_name in enumerate(embedding_cols):
                table_dict[col_name] = chunk_embeddings[:, col_idx]

            table = pa.Table.from_pydict(table_dict, schema=output_schema)
            writer.write_table(table)

            total_processed += c_len
            elapsed_chunk = time.time() - t_inf_start
            rate = total_processed / max(1.0, elapsed_chunk)
            print(
                f"  Chunk [{chunk_idx + 1:2d}/{n_chunks}] processed: {total_processed:9,d} / {n_total:,} "
                f"({(total_processed / n_total) * 100:5.1f}%) | Rate: {rate:6.0f} det/s"
            )

            # Memory cleanup
            del chunk_tensors, chunk_masks, norm_chunk_tensors, chunk_embeddings, table, table_dict
            if chunk_idx % 4 == 0:
                gc.collect()

        writer.close()
        t_total_end = time.time()

        # 5. Post-Inference Validation
        print("\n[Step 5/5] Running post-inference integrity validations...")
        self.verify_checkpoint_immutability()

        # Verify output parquet metadata
        parquet_meta = pq.read_metadata(output_path)
        out_rows = parquet_meta.num_rows
        out_cols = parquet_meta.num_columns
        out_size_mb = os.path.getsize(output_path) / (1024 * 1024)

        assert out_rows == n_total, f"Row count mismatch: expected {n_total}, got {out_rows}"
        assert (
            out_cols == len(output_schema)
        ), f"Column count mismatch: expected {len(output_schema)}, got {out_cols}"
        assert total_future_violations == 0, f"Future leakage detected: {total_future_violations}"
        assert total_nan_inf == 0, f"NaN or Inf embeddings detected: {total_nan_inf}"

        # Partition breakdown
        df_out_part = pd.read_parquet(output_path, columns=["partition"])
        part_counts = df_out_part["partition"].value_counts().to_dict()

        summary = {
            "input_shape": [n_total, len(self.REQUIRED_COLUMNS)],
            "target_sequences_generated": out_rows,
            "embeddings_generated": out_rows,
            "unique_detection_ids": n_total,
            "partition_counts": part_counts,
            "sequence_length": self.EXPECTED_T,
            "num_channels": self.EXPECTED_CHANNELS,
            "embedding_dim": self.EXPECTED_LATENT_DIM,
            "model_parameters": self.EXPECTED_PARAMS,
            "device": str(self.device),
            "runtime_seconds": round(t_total_end - start_time, 2),
            "future_leakage_violations": total_future_violations,
            "nan_inf_embeddings": total_nan_inf,
            "output_path": str(output_path),
            "output_file_size_mb": round(out_size_mb, 2),
            "checkpoint_sha256": self.initial_ckpt_sha256,
        }

        # Save metadata JSON alongside parquet
        summary_path = output_path.with_name("india_2025_embeddings_summary.json")
        with open(summary_path, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2)

        print("\n" + "=" * 80)
        print("STAGE 8.1 INFERENCE COMPLETED SUCCESSFULLY")
        print("=" * 80)
        print(f"  Total Embeddings:  {out_rows:,} x {self.EXPECTED_LATENT_DIM}")
        print(f"  Parquet File Size: {out_size_mb:.2f} MB")
        print(f"  Future Leakage:    {total_future_violations}")
        print(f"  NaN/Inf Values:    {total_nan_inf}")
        print(f"  Runtime:           {summary['runtime_seconds']} seconds")
        print(f"  Output Parquet:    {output_path}")
        print(f"  Summary JSON:      {summary_path}")

        return summary


if __name__ == "__main__":
    pipeline = TCNIndiaInferencePipeline()
    summary = pipeline.run_inference()
