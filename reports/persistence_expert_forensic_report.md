# DS08 Persistent-source attribution: forensic investigation

## Status

**Persistent Expert investigated but not promoted.** No candidate was trained or evaluated, and no blind-set rerun was performed. The existing Stage 8.36 classifier and its checkpoint remain the baseline.

## 1. Current Persistent failure diagnosis

The archived Stage 8.36 report records four Persistent→Agricultural errors:

| Event | P(Agricultural) | P(Persistent) | Selected current evidence |
|---|---:|---:|---|
| `EVT_825_PER_PER_SRC_03` | 0.3589 | 0.3462 | FRP 7.75 MW; 5 prior detections, 1 calendar month |
| `EVT_825_PER_PER_SRC_06` | 0.3929 | 0.3529 | FRP 4.90 MW; 5 prior detections, 1 calendar month; agricultural-heartland score 1 |
| `EVT_825_PER_PER_SRC_49` | 0.3670 | 0.3515 | FRP 7.36 MW; 5 prior detections, 1 calendar month |
| `EVT_825_PER_PER_SRC_52` | 0.3905 | 0.3558 | FRP 7.66 MW; 5 prior detections, 1 calendar month; agricultural-heartland score 1 |

All four decisions were close: the Persistent probability trails the Agricultural probability by only 0.013–0.040. The archived report's selected feature values point to weak historical coverage (five detections compressed into one month) and, for two events, an agricultural landscape prior. Current FRP is modest and similar across the four. This supports recurrence sparsity and thermal overlap as plausible contributors; it does not establish a causal feature attribution.

The final report does not preserve the four events' full 41-feature vectors or model explanations, so it cannot establish which individual learned weights drove the decisions or compare their TI4/TI5 values with agricultural examples. The requested claim that their *current thermal signature* caused the confusion is therefore **not proven** from the retained forensic artifacts. The reported low/modest FRP and near-tied probabilities are consistent with overlap, but that remains an inference.

## 2. Existing features and the compact persistence block

The frozen 41-feature schema already includes alert-time thermal/prefix features, industrial proximity/baseline, land-cover context, and 18 historical fields. Historical fields include full and recent detection counts, active days/months, FRP mean/max/std/CV, 1/2/5 km counts, spatial dispersion, distinct calendar months, age of latest observation, night ratio, and mean delta-TI. These are causal summaries, but counts and month coverage do not fully describe recurrence regularity or whether detections cluster tightly around the alert location.

An isolated, label-blind builder is in `src/persistence_expert/features.py`. It adds a compact 18-field schema: recurrence counts/active days/months/interarrival regularity; spatial radius ratio and dispersion; historical FRP and delta-TI stability; night ratio and active calendar-month diversity; plus explicit history availability/count. Every input timestamp is checked against `t0`; any future row raises an error. The builder uses no class labels, registries, event duration, or target-linked fields.

| Family | Definition | Alert-time availability | Physical meaning |
|---|---|---|---|
| Recurrence | Counts in 30/90/365 days; active days/months; median gap and gap CV | FIRMS acquisitions no later than `t0` | Recent activity and regularity, not simply lifetime count |
| Spatial | Fraction within 2 km; mean radial distance and RMS dispersion within 5 km | Prior detection coordinates | Repeated localization versus spatially diffuse burning |
| Thermal | Historical FRP mean/CV and delta-TI mean/std | Prior FIRMS thermal measurements | Stability of emitted power and thermal contrast |
| Temporal | Night ratio and distinct calendar months | Prior acquisition timestamp/day-night flag | Day/night behavior and recurrence across the annual cycle |
| Quality | History count and presence bit | Computed from the same prior records | Distinguishes observed zeros from no history |

This schema is a tested feature utility, not a trained or selected feature subset.

## 3. Candidate models

The requested comparisons remain unrun: statistics-only baseline, persistence-feature MLP, small causal TCN plus summaries, and hierarchical variants with a development-selected gate. No 0.5 gate or other threshold is proposed. The existing Stage 8.36 `Architecture1_StaticMLP` remains the reference classifier.

## 4. Development results and data sufficiency

No persistence-expert metrics or ablations are reported because the available expanded development feature artifact fails the source-data integrity check described below. Stage 8.35's own report gives 42 baseline Persistent and 27 baseline Agricultural events in its 131-event cohort, then claims 60 and 43 respectively after expansion. Those counts alone cannot establish independent source diversity or adequacy for a binary expert.

**Critical integrity finding:** `src/stage8_35/feature_builder.py` assigns fixed thermal values and fixed high recurrence summaries to each newly added Persistent event (for example, FRP 22.5 MW, `hist_count_full=48`, `hist_active_days_full=42`, and `hist_active_months_full=18`). These are not computed from pre-alert FIRMS rows. This directly conflicts with the instruction against fabricated persistence signals and means the Stage 8.35 expanded features cannot be used to select/train/evaluate a persistence expert. The separately authored report calls the additions genuine and non-synthetic, but the feature-builder implementation contradicts that claim for these fields. I did not use those feature values for model development.

The event provenance report names source categories and years, but a verified table of Persistent events by source subtype, region, season, and independently held-out location was not established in this investigation. Thus data sufficiency for generalization is **not demonstrated**. The 2025 holdout may be reported by the prior pipeline, but it is not a substitute for rebuilding valid features from source FIRMS records.

## 5. Ablation results

Not run. Recurrence-only, recurrence+spatial, recurrence+thermal, recurrence+temporal, and leave-family-out ablations would all be misleading if they use the contaminated Stage 8.35 expansion.

## 6. Error analysis

The four errors have the same archived recurrence pattern: five prior detections in one calendar month. Two occur in locations with an agricultural-heartland score of 1; the other two have score 0. Their FRP values are 4.90–7.75 MW, and their probabilities are weakly separated between Agricultural and Persistent. This suggests that the existing annual/month recurrence summaries did not distinguish these cases from seasonal burns. The artifacts do not provide exact interarrival gaps, prior centroid movement, or a reliable per-event thermal explanation.

Hard-negative checks for strong/nearby/short-period agricultural events were not conducted, because a valid development-only candidate cohort and complete raw event feature vectors were not assembled.

## 7. Causality audit

The Stage 8.30 builder documents a pre-alert history cutoff of `t0 - 7 days`, asserts its latest historical record is at/before that cutoff, and asserts target-event detections are absent from the history. The 41-feature provenance table labels all selected historical features with the same cutoff. These design/code checks support causal availability for the original Stage 8.30 features, subject to correct upstream timestamps and source-row lineage.

The new isolated feature utility asserts `historical_timestamp <= t0` directly and rejects a future row. The feature unit tests cover cutoff rejection, empty history, one record, irregular recurrence, spatial stability, thermal summaries, and schema groups. They passed (6 tests). This does not retroactively validate the hard-coded Stage 8.35 features.

## 8. Spatial leakage audit

Existing Stage 8.35 materials describe four broad macro-region folds. This investigation did not verify nearest cross-fold distances, event-group separation, or buffers for the exact cohort used in each model run. A macro-region label alone does not prove that nearby locations cannot cross a boundary. Spatial leakage validity for any new model remains **unverified** and must be checked before fitting.

## 9. Comparison against frozen baseline

The archived, one-time Stage 8.36 result remains: accuracy 78.57%, macro-F1 0.8021, balanced accuracy 81.67%; Persistent recall 60% (6/10), F1 0.75; Agricultural recall 83.33% (5/6), F1 0.625. The persistent-to-agricultural errors and class metrics above are quoted from the saved terminal report. The counter remains at 1; the evaluation script was not run.

## 10. Final recommendation

Do not promote a persistence expert and do not modify production. Rebuild the candidate development table from observed FIRMS detections, preserve source-record provenance, derive every persistence summary from records at/before `t0`, and attach validated event-grouped spatial/chronological splits. Then compare a statistics-only classifier first; only add an MLP or small causal TCN if those splits and sample counts support them. Freeze the gate on development validation before any independent evaluation.

## 11. Additional data required

**Data-limited for the requested model comparison until the expanded feature artifact is repaired and audited.** Required data are observed pre-alert FIRMS histories for Persistent and hard-negative Agricultural events across multiple years, additional independent persistent facilities/source types and regions, and enough site-separated examples to reserve spatially valid validation data. No synthetic recurrence values should be used.

## 12. Foundation-model visual branch

Not justified yet. The FIRMS-only persistence experiment has not been validly evaluated, and the available artifacts do not establish enough independently linked FIRMS–Sentinel-2 training examples to support a foundation-model fusion claim. Revisit only after source-derived persistence features and a valid cohort are established.

## Preservation record

- Frozen checkpoint expected SHA-256: `5bdbfbd503a3c0acbd50caefd2b1c88b5e0190a7176d70a517165814722bcff2`.
- Frozen test evaluation counter observed before/after this work: `1`.
- No blind evaluator invocation, model training, threshold tuning, or Stage 8.36 artifact modification was performed.
- Candidate checkpoints and their version manifests were not created because no candidate was trained.
