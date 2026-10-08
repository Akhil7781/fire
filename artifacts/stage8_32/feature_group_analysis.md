# Stage 8.32 Feature Group Analysis

**Date:** October 4, 2026  
**Auditor:** Autonomous Agentic AI (Advanced Coding & Scientific Audit Team)  

---

## 1. Physical Modality Breakdown and Encoder Architecture

The Stage 8.32 deep-learning architecture processes features through distinct, modular encoders:

1. **CURRENT THERMAL ENCODER (14 Features):**
   - Features: `current_frp`, `current_bright_ti4`, `current_bright_ti5`, `current_delta_ti`, `current_is_night`, `detections_observed_so_far`, `elapsed_observation_hours`, `mean_frp_observed_so_far`, `max_frp_observed_so_far`, `std_frp_observed_so_far`, `night_ratio_observed_so_far`, `spatial_extent_observed_so_far`, `frp_trend_observed_so_far`, `time_since_prev_h`.
   - Role: Captures alert-time combustion intensity, atmospheric delta temperature, and initial plume spread.

2. **HISTORICAL RECURRENCE ENCODER (104 Features):**
   - Features: Multi-scale nested counts (1km, 2km, 5km), active calendar days/months, FRP percentiles, temporal gap statistics across 30d, 90d, 180d, 365d, 3y, 5y, and full history.
   - Role: Provides the primary physical separation for Persistent Thermal Sources (smelters, flaring, refineries) vs Acute Biomass/Industrial fires.

3. **INDUSTRIAL CONTEXT ENCODER (6 Features):**
   - Features: `dist_to_fac_km`, `within_1km_fac`, `within_5km_fac`, `facility_baseline_frp`, `frp_deviation`, `facility_frp_zscore`.
   - Role: Statutory facility proximity and pre-alert baseline FRP. Completely excludes test labels and persistent manifests.

4. **LAND-COVER & ECOREGION ENCODER (3 Features):**
   - Features: `forest_biome_score`, `agri_heartland_score`, `s2_available`.
   - Role: Delineates macro-biomes (Himalayas/Ghats forests vs Indo-Gangetic/Cauvery croplands).

5. **GEOGRAPHIC ENCODER (2 Features):**
   - Features: `centroid_lat`, `centroid_lon`.
   - Role: Spatial coordinates (evaluated under Model A and ablated in Models B-E).

---

## 2. Gated Multimodal Fusion

Instead of a flat concatenation, each encoder outputs a normalized latent embedding ($H=64$). A gated fusion network applies modality-specific gating:
$$g_k = \sigma(W_k h_k + b_k)$$
$$h_{\text{fused}} = \text{LayerNorm}\left(\sum_k g_k \odot h_k\right)$$
followed by residual MLP blocks.
