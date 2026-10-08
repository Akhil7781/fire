# Quality Audit Report: Satellite Thermal Anomaly Label Construction

**Audit Execution Timestamp**: 2026-09-23T18:27:29.519995+00:00

**Total Records Evaluated**: 1,175,795

**Overall Verdict**: **PASS**

## 18-Point Quality Criteria Results

| # | Criterion Name | Status | Verification Detail |
|---|---|---|---|
| 01 | `duplicate_detection_id` | **PASS** | 0 duplicates found |
| 02 | `duplicate_evidence_id` | **PASS** | 0 duplicate evidence IDs found across 41 reference records |
| 03 | `invalid_labels` | **PASS** | Classes present: {np.int64(0), np.int64(1), np.int64(2), np.int64(4)}, invalid: set() |
| 04 | `missing_confidence` | **PASS** | 0 null confidence scores |
| 05 | `invalid_confidence_range` | **PASS** | Confidence range: [0.0000, 0.8500] |
| 06 | `tier_confidence_consistency` | **PASS** | Tier D non-zero: 0, Tier A low: 0 |
| 07 | `labeled_with_zero_evidence` | **PASS** | 0 labeled detections have 0 evidence |
| 08 | `evidence_without_provenance` | **PASS** | 0 labeled detections missing primary_source |
| 09 | `impossible_timestamps` | **PASS** | 0 evidence records where start > end |
| 10 | `invalid_coordinates` | **PASS** | All coordinates within India bounding box (68-98 E, 8-37 N) |
| 11 | `conflict_resolution_violations` | **PASS** | 0 unresolved conflicts forced into positive classes |
| 12 | `class_source_rule_violations` | **PASS** | 0 industrial labels sourced from forestry/agricultural bulletins |
| 13 | `accidental_use_of_firms_type` | **PASS** | FIRMS type=2 count (108477) != Label Class 1 count (2). Zero leakage. |
| 14 | `test_set_leakage_into_parameters` | **PASS** | Matching parameters are defined in label_config.yaml. Zero test set fitting. |
| 15 | `train_val_test_id_integrity` | **PASS** | All 578,465 Train, 29,409 Val, and 47,881 Test IDs are present in label table |
| 16 | `label_table_row_integrity` | **PASS** | 1175795 label rows exactly match 1175795 FIRMS rows (1:1 preservation) |
| 17 | `unexplained_forced_labels` | **PASS** | 0 unexplained forced labels found |
| 18 | `unlabeled_mapped_to_class_4` | **PASS** | 0 detections with zero evidence mapped to Class 4 |
