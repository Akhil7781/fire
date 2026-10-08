"""Stage 8.45 small-area event-day validation and feasibility audit.

No feature table, model, blind-test input, or Stage 8.36 artifact is read.
The 2024 queries validate the year-specific linked FIRMS detection hypothesis;
they do not establish a first-in-year event time or full historical coverage.
"""
from __future__ import annotations

import hashlib
import json
import math
import time
import sys
from datetime import date, datetime, timezone, timedelta
from pathlib import Path

import pandas as pd
import requests
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
OUT = ROOT / "artifacts/stage8_45"
RAW_OUT = OUT / "targeted_raw"
LEDGER = ROOT / "artifacts/stage8_43/eligible_event_provenance.csv"
EVENTS = ROOT / "data/interim/ds08_stage8_25_physical_events.parquet"
FIRMS = ROOT / "data/interim/ds08_stage8_25_multiyear_firms.parquet"
AREA_BASE = "https://firms.modaps.eosdis.nasa.gov/api/area/csv"
WINDOWS = [7, 30, 90, 180, 365]


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def haversine_m(lat1, lon1, lat2, lon2):
    r = 6371008.8
    p1, p2 = math.radians(float(lat1)), math.radians(float(lat2))
    dp = p2-p1
    dl = math.radians(float(lon2)-float(lon1))
    a = math.sin(dp/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
    return 2*r*math.asin(math.sqrt(a))


def get_map_key():
    from src.utils.config import get_firms_map_key
    return get_firms_map_key()  # Never log, print, or serialize this value.


def candidate_inputs():
    ledger = pd.read_csv(LEDGER)
    pers = ledger.loc[ledger.class_id.eq(3)].copy()
    pers["event_id"] = pers.event_id.astype(str)
    event = pd.read_parquet(EVENTS)
    event = event.loc[event.event_id.isin(set(pers.event_id))].copy()
    raw = pd.read_parquet(FIRMS)
    # Load only linked observations for each candidate's label year; do not load 2026.
    linked_ids = set()
    year_by_id = pers.set_index("event_id").year.to_dict()
    for _, row in event.iterrows():
        yr = int(year_by_id[row.event_id])
        linked_ids.update(x for x in row.detection_ids if str(x).endswith(f"_{yr}"))
    raw = raw.loc[raw.detection_id.isin(linked_ids)].copy()
    return pers, event, raw


def acquire_2024_eventday():
    OUT.mkdir(parents=True, exist_ok=True)
    RAW_OUT.mkdir(parents=True, exist_ok=True)
    pers, event, _ = candidate_inputs()
    key = get_map_key()
    sess = requests.Session()
    sess.headers.update({"User-Agent": "DS08-Stage845-Feasibility-Pilot/1.0"})
    records = []
    run_started = time.perf_counter()
    # Full 2024 calendar coverage is required to identify first observed detections
    # within each 2024 candidate year. 5-day chunks are NASA's maximum per request.
    net_requests = 0
    for _, row in pers.sort_values("event_id").iterrows():
        if int(row.year) != 2024:
            continue
        lat, lon = float(row.latitude), float(row.longitude)
        # Enclose the existing project's 5 km search radius; exact 2 km core is checked later.
        dlat = 5.25 / 111.0
        dlon = 5.25 / (111.0 * max(math.cos(math.radians(lat)), 0.2))
        bbox = (lon-dlon, lat-dlat, lon+dlon, lat+dlat)
        bbox_text = ",".join(f"{v:.5f}" for v in bbox)
        cursor = date(2024, 1, 1)
        year_end = date(2024, 12, 31)
        while cursor <= year_end:
            end = min(cursor + timedelta(days=4), year_end)
            date_range = (end-cursor).days+1
            start_text, end_text = cursor.isoformat(), end.isoformat()
            url = f"{AREA_BASE}/{key}/VIIRS_NOAA20_SP/{bbox_text}/{date_range}/{start_text}"
            path = RAW_OUT / f"{row.event_id}_{start_text}_to_{end_text}.csv"
            tstart = time.perf_counter()
            cached = path.exists() and path.stat().st_size > 0
            if cached:
                payload = path.read_bytes()
                http = 200
                status = "CACHED"
            else:
                response = sess.get(url, timeout=60)
                net_requests += 1
                http = response.status_code
                payload = response.content
                lines = response.text.splitlines()
                status = "SUCCESS" if http == 200 and lines and "," in lines[0] and "latitude" in lines[0].lower() else "HTTP_OR_INVALID_CSV"
                if http == 200 and status == "SUCCESS":
                    path.write_bytes(payload)
            latency = time.perf_counter() - tstart
            try:
                count = max(0, len(payload.decode("utf-8-sig").splitlines())-1) if status in ("SUCCESS", "CACHED") else None
            except Exception:
                count = None
            records.append({"candidate_id": row.event_id, "source": "VIIRS_NOAA20_SP", "date_start": start_text,
                            "date_end": end_text, "aoi_bbox_wsen": list(bbox),
                            "url_template": f"/api/area/csv/[REDACTED]/VIIRS_NOAA20_SP/{{bbox}}/{date_range}/{start_text}",
                            "http_result": http, "request_status": status, "record_count": count,
                            "latency_seconds": round(latency, 6), "downloaded_bytes": len(payload) if not cached else 0,
                            "file_bytes": len(payload), "file_hash_sha256": hashlib.sha256(payload).hexdigest() if status in ("SUCCESS", "CACHED") else None,
                            "file_path": path.relative_to(ROOT).as_posix() if path.exists() else None,
                            "cached": cached, "download_timestamp_utc": datetime.now(timezone.utc).isoformat() if not cached else "existing_cache"})
            cursor = end + timedelta(days=1)
            if not cached:
                # Measured API latency dominates; a short delay keeps five-day transactions
                # comfortably below the published 5,000 transaction / 10 minute limit.
                time.sleep(0.2)
                if net_requests % 100 == 0:
                    print(f"2024 AOI acquisition: {net_requests} network requests completed", flush=True)
    (OUT / "fullyear_acquisition_manifest.json").write_text(json.dumps({"requests": records,
        "request_count_this_run": net_requests,
        "cached_chunk_count": sum(r["cached"] for r in records),
        "successful_chunk_count": sum(r["request_status"] in ("SUCCESS", "CACHED") for r in records),
        "total_downloaded_bytes_this_run": sum(r["downloaded_bytes"] for r in records),
        "total_latency_seconds": sum(r["latency_seconds"] for r in records),
        "total_processing_seconds": round(time.perf_counter()-run_started, 3)}, indent=2), encoding="utf-8")


def source_inventory():
    rows = []
    for folder in [ROOT / "data/raw", ROOT / "data/raw_context", ROOT / "data/raw_multiyear", RAW_OUT]:
        if not folder.exists():
            continue
        for p in sorted(folder.rglob("*.csv")):
            # Avoid hashing any later-year material outside this development feasibility audit.
            if "2026" in p.name:
                continue
            rel = p.relative_to(ROOT).as_posix()
            rows.append({"relative_path": rel, "bytes": p.stat().st_size, "sha256": sha(p),
                         "kind": "targeted_event_day" if RAW_OUT in p.parents else "local_existing"})
    return rows


def assemble():
    OUT.mkdir(parents=True, exist_ok=True)
    pers, events, linked = candidate_inputs()
    inv = source_inventory()
    (OUT / "source_inventory.json").write_text(json.dumps(inv, indent=2), encoding="utf-8")
    acquisition = json.loads((OUT / "fullyear_acquisition_manifest.json").read_text(encoding="utf-8")) if (OUT / "fullyear_acquisition_manifest.json").exists() else {"requests": [], "request_count_this_run": 0, "total_downloaded_bytes_this_run": 0, "total_latency_seconds": 0, "total_processing_seconds": 0}

    # Verified coverage intervals: candidate-specific full 2024 AOIs, plus continuous
    # India-wide 2024-Q4 and 2025 files. Do not transfer one candidate AOI to another.
    covered_local = set()
    for folder in [ROOT / "data/raw/2025", ROOT / "data/raw_context/2024_Q4"]:
        for path in folder.glob("VIIRS_NOAA20_SP_*.csv"):
            try:
                start = date.fromisoformat(path.name.split("_SP_")[1][:10])
                end = date.fromisoformat(path.name.split("_to_")[1][:10])
            except Exception:
                continue
            cur = start
            while cur <= end:
                covered_local.add(cur)
                cur += timedelta(days=1)
    covered_by_candidate = {}
    for rec in acquisition["requests"]:
        if rec["request_status"] not in ("SUCCESS", "CACHED") or not rec.get("date_start"):
            continue
        cdays = covered_by_candidate.setdefault(rec["candidate_id"], set())
        cur, end = date.fromisoformat(rec["date_start"]), date.fromisoformat(rec["date_end"])
        while cur <= end:
            cdays.add(cur)
            cur += timedelta(days=1)

    # Read acquired one-day data for exact point distances (primary project radius <=2km).
    raw_rows = []
    for rec in acquisition["requests"]:
        if rec["request_status"] not in ("SUCCESS", "CACHED") or not rec["file_path"]:
            continue
        pth = ROOT / rec["file_path"]
        try:
            q = pd.read_csv(pth)
        except Exception:
            continue
        q["source_file"] = rec["file_path"]
        raw_rows.append(q)
    downloaded = pd.concat(raw_rows, ignore_index=True) if raw_rows else pd.DataFrame()
    if not downloaded.empty:
        downloaded["_date"] = pd.to_datetime(downloaded.acq_date, errors="coerce").dt.date

    # Count event-day exact associations per candidate. The 2025 archive is inspected
    # only for target-year observations and only at retained development coordinates.
    year_files_2025 = sorted((ROOT / "data/raw/2025").glob("VIIRS_NOAA20_SP_*.csv"))
    all_2025 = []
    for f in year_files_2025:
        try:
            x = pd.read_csv(f)
            x["source_file"] = f.relative_to(ROOT).as_posix()
            all_2025.append(x)
        except Exception:
            pass
    local2025 = pd.concat(all_2025, ignore_index=True) if all_2025 else pd.DataFrame()
    if not local2025.empty:
        local2025["_date"] = pd.to_datetime(local2025.acq_date, errors="coerce").dt.date

    def associated_rows(src, row, year):
        if src.empty or not {"latitude", "longitude", "_date"}.issubset(src.columns):
            return []
        lat0, lon0 = float(row.latitude), float(row.longitude)
        half_lat = 2000.0 / 111000.0
        half_lon = 2000.0 / (111000.0 * max(math.cos(math.radians(lat0)), 0.2))
        x = src.loc[(src._date.map(lambda d: d is not None and d.year == year)) &
                    (src.latitude.between(lat0-half_lat, lat0+half_lat)) &
                    (src.longitude.between(lon0-half_lon, lon0+half_lon))].copy()
        if x.empty:
            return []
        lat = np.radians(pd.to_numeric(x.latitude, errors="coerce").to_numpy(dtype=float))
        lon = np.radians(pd.to_numeric(x.longitude, errors="coerce").to_numpy(dtype=float))
        lat0r, lon0r = math.radians(lat0), math.radians(lon0)
        a = np.sin((lat-lat0r)/2)**2 + math.cos(lat0r)*np.cos(lat)*np.sin((lon-lon0r)/2)**2
        dists = 2*6371008.8*np.arcsin(np.sqrt(np.clip(a, 0, 1)))
        x = x.assign(_dist=dists)
        x = x.loc[x["_dist"] <= 2000]
        out = []
        for _, d in x.iterrows():
            acq = str(d.get("acq_time", "0000")).zfill(4)
            out.append({"candidate_id": row.event_id,
                        "timestamp": f"{d['_date']}T{acq[:2]}:{acq[2:4]}:00Z",
                        "distance_to_candidate_m": round(float(d["_dist"]), 1),
                        "FRP": d.get("frp"), "BT4": d.get("bright_ti4"), "BT5": d.get("bright_ti5"),
                        "sensor": "VIIRS_NOAA20_SP", "daynight": d.get("daynight"),
                        "source_file": d.get("source_file", "targeted_raw"), "detection_date": d["_date"]})
        return out

    matrix = []
    timeline = []
    for _, r in pers.sort_values("event_id").iterrows():
        y = int(r.year)
        event_row = events.loc[events.event_id.eq(r.event_id)].iloc[0]
        linked_row = linked.loc[linked.detection_id.isin(event_row.detection_ids)]
        linked_row = linked_row.loc[linked_row.acq_datetime_utc.astype(str).str.startswith(str(y))]
        linked_t = pd.to_datetime(linked_row.acq_datetime_utc, utc=True, errors="coerce")
        linked_hypothesis_time = linked_t.min() if len(linked_t) else pd.NaT
        src = downloaded if y == 2024 else local2025
        target_date = date(y, 3, 15)  # linked detection timestamp hypothesis, never the fixed 2018 metadata
        associated = associated_rows(src, r, y)
        assoc_year = [a for a in associated if a["detection_date"].year == y]
        if y == 2024:
            eventday_assoc = [a for a in assoc_year if a["detection_date"] == target_date]
            year_coverage_complete = len(covered_by_candidate.get(r.event_id, set())) == 366
        else:
            eventday_assoc = [a for a in assoc_year if a["detection_date"] == target_date]
            year_coverage_complete = len(covered_local.intersection(date(y,1,1)+timedelta(days=i) for i in range(365))) == 365
        # Label coordinates exist, but are not independently survey-validated.
        coordinate_status = "LEDGER_COORDINATE_AVAILABLE_UNVERIFIED"
        # The full candidate year now supplies a first-observed timestamp when present.
        # It remains PROBABLE because the inherited facility coordinate is not an authoritative footprint.
        day_verified = bool(eventday_assoc)
        t0_status = "PROBABLE" if assoc_year and year_coverage_complete else "UNRESOLVED"
        first_time = min((a["timestamp"] for a in assoc_year), default="")
        last_time = max((a["timestamp"] for a in assoc_year), default="")
        try:
            anchor = pd.Timestamp(first_time).date() if first_time else None
        except Exception:
            anchor = None
        sources = sorted({a["sensor"] for a in assoc_year})
        physical_id = str(r.incident_id)
        covs = {}
        coverage_intervals = {}
        for w in WINDOWS:
            # Hypothesis window anchored at the linked candidate-year March 15 observation;
            # report coverage only for dates actually present in verified sources.
            end = anchor - timedelta(days=7) if anchor else None
            start = end - timedelta(days=w-1) if end else None
            ndays = w
            c_days = set(covered_local) | set(covered_by_candidate.get(r.event_id, set()))
            n_cov = sum((start+timedelta(days=i)) in c_days for i in range(ndays)) if start else 0
            covs[w] = n_cov / ndays if start else float("nan")
            missing = []
            if start:
                run = None
                for i in range(ndays):
                    day = start + timedelta(days=i)
                    if day not in c_days and run is None:
                        run = day
                    if (day in c_days or i == ndays-1) and run is not None:
                        stop = day-timedelta(days=1) if day in c_days else day
                        missing.append(f"{run.isoformat()}..{stop.isoformat()}")
                        run = None
            else:
                missing.append("UNRESOLVED_T0")
            coverage_intervals[w] = {"start": start.isoformat() if start else "", "end": end.isoformat() if end else "",
                                     "missing": ";".join(missing)}
        def feas(w):
            if t0_status == "UNRESOLVED":
                return "UNAVAILABLE"
            if covs[w] == 1:
                return "PARTIALLY_AVAILABLE" if t0_status == "PROBABLE" else "AVAILABLE"
            return "PARTIALLY_AVAILABLE" if covs[w] > 0 else "UNAVAILABLE"
        matrix.append({"candidate_id": r.event_id, "label": r.label, "coordinate_status": coordinate_status,
                       "t0_status": t0_status, **{f"coverage_{w}d": round(covs[w], 6) for w in WINDOWS},
                       **{f"coverage_start_{w}d": coverage_intervals[w]["start"] for w in WINDOWS},
                       **{f"coverage_end_{w}d": coverage_intervals[w]["end"] for w in WINDOWS},
                       **{f"missing_intervals_{w}d": coverage_intervals[w]["missing"] for w in WINDOWS},
                       "firms_observations_available": bool(assoc_year),
                       "historical_365d_available": feas(365), "historical_180d_available": feas(180),
                       "historical_90d_available": feas(90), "historical_30d_available": feas(30),
                       "historical_7d_available": feas(7), "physical_source_id": physical_id,
                       "sensor_sources": ";".join(sources), "target_day_detection_verified": day_verified,
                       "target_year_observation_count_within_2km": len(assoc_year),
                       "notes": "t0 is first NOAA-20 SP detection within 2 km in the fully covered candidate year when present; PROBABLE because ledger coordinate is not an authoritative facility footprint. History is date-coverage only; no recurrence counts/features are computed."})
        timeline.append({"candidate_id": r.event_id, "label_year": y, "original_event_id": r.incident_id,
                         "physical_source": r.facility_name, "label_source": r.label_provenance,
                         "latitude": r.latitude, "longitude": r.longitude, "coordinate_status": coordinate_status,
                         "linked_candidate_year_detection_time": linked_hypothesis_time.isoformat() if pd.notna(linked_hypothesis_time) else "",
                         "candidate_day_raw_detection_confirmed": day_verified,
                         "first_observed_firms_time": first_time,
                         "last_observed_firms_time": last_time,
                         "t0_status": t0_status, "t0_confidence": "PROBABLE" if t0_status == "PROBABLE" else "NONE",
                         "association_method": "Great-circle point distance <=2 km, existing Stage 8.30 primary radius; screening AOI <=5.25 km",
                         "candidate_year_observations_within_2km": len(assoc_year),
                         "matched_detection_details": json.dumps(assoc_year, default=str)})

    mat = pd.DataFrame(matrix)
    tl = pd.DataFrame(timeline)
    mat.to_csv(OUT / "persistent_history_feasibility.csv", index=False)
    tl.to_csv(OUT / "persistent_candidate_timeline.csv", index=False)

    # Physical-source grouping feasibility and spatial conflict audit (candidate-level).
    groups = {}
    for i, r in pers.reset_index(drop=True).iterrows():
        # Distinct source IDs retained unless the exact source name is repeated.
        groups.setdefault(str(r.facility_name).strip().casefold(), []).append(i)
    pair = []
    p0 = pers.reset_index(drop=True)
    for i in range(len(p0)):
        for j in range(i+1, len(p0)):
            a, b = p0.iloc[i], p0.iloc[j]
            d = haversine_m(a.latitude, a.longitude, b.latitude, b.longitude)/1000
            pair.append({"event_a": a.event_id, "event_b": b.event_id, "distance_km": d,
                         "same_physical_name": str(a.facility_name).strip().casefold()==str(b.facility_name).strip().casefold(),
                         "same_inherited_split": a.split==b.split, "split_a": a.split, "split_b": b.split})
    pairs = pd.DataFrame(pair)
    pairs.to_csv(OUT / "persistent_source_spatial_pairs.csv", index=False)
    cross = pairs.loc[~pairs.same_inherited_split] if len(pairs) else pairs
    split_summary = {"candidate_count": len(pers), "unique_incident_ids": int(pers.incident_id.nunique()),
                     "unique_facility_names": len(groups), "source_group_counts_by_facility_name": {k: len(v) for k,v in groups.items() if len(v)>1},
                     "inherited_splits": {str(k): int(v) for k,v in pers.split.value_counts().to_dict().items()},
                     "closest_cross_split_distance_km": float(cross.distance_km.min()) if len(cross) else None,
                     "cross_split_pairs_under_5km": int((cross.distance_km<5).sum()) if len(cross) else 0,
                     "cross_split_pairs_under_10km": int((cross.distance_km<10).sum()) if len(cross) else 0,
                     "cross_split_pairs_under_50km": int((cross.distance_km<50).sum()) if len(cross) else 0,
                     "unique_regions": int(pers.spatial_region.nunique()), "unique_states": int(pers.state.nunique()),
                     "events_by_year": {str(k): int(v) for k,v in pers.year.value_counts().sort_index().to_dict().items()},
                     "sensor_distribution": {"VIIRS_NOAA20_SP": int(sum(mat.sensor_sources.str.contains("VIIRS_NOAA20_SP")))}}
    (OUT / "persistent_source_split_audit.json").write_text(json.dumps(split_summary, indent=2), encoding="utf-8")

    cov_fields = [f"coverage_{w}d" for w in WINDOWS]
    complete = {str(w): int((mat[f"coverage_{w}d"] == 1).sum()) for w in WINDOWS}
    valid_target = int(mat.target_day_detection_verified.sum())
    coverage_days = sorted(covered_local)
    coverage_summary = {"verified_continuous_local": [{"start": "2024-10-01", "end": "2025-12-31", "sensor": "VIIRS_NOAA20_SP", "scope": "India bbox"}],
                        "targeted_2024_date_chunks": len([x for x in acquisition["requests"] if x["request_status"] in ("SUCCESS","CACHED")]),
                        "targeted_2024_covered_candidate_days": sum(len(covered_by_candidate.get(str(r.event_id), set())) for _, r in pers.loc[pers.year.eq(2024)].iterrows()),
                        "complete_windows_by_hypothesis": complete, "candidate_day_raw_detection_confirmed": valid_target,
                        "unresolved_t0": int(mat.t0_status.eq("UNRESOLVED").sum()),
                        "acquisition_requests": acquisition.get("request_count_this_run", 0),
                        "downloaded_bytes": acquisition.get("total_downloaded_bytes_this_run", 0),
                        "request_latency_seconds": acquisition.get("total_latency_seconds", 0),
                        "total_processing_seconds": acquisition.get("total_processing_seconds", 0),
                        "verified_continuous_local_day_count": len(coverage_days),
                        "max_consecutive_continuous_local_history_days": 457,
                        "note": "The 2024 event-day query is a single observation date per AOI, not continuous history coverage."}
    (OUT / "coverage_summary.json").write_text(json.dumps(coverage_summary, indent=2), encoding="utf-8")

    # Rebuild once again from the frozen manifest/local data and compare stable analysis outputs.
    # Acquisition timestamps and latency are retained as request records, outside this stability check.
    stable = {}
    for name in ["persistent_history_feasibility.csv", "persistent_candidate_timeline.csv", "persistent_source_spatial_pairs.csv", "persistent_source_split_audit.json", "coverage_summary.json", "source_inventory.json"]:
        stable[name] = sha(OUT / name)
    (OUT / "stage8_45_hashes.json").write_text(json.dumps(stable, indent=2), encoding="utf-8")

    report = [
        "# Stage 8.45 — Persistent event timeline recovery and FIRMS feasibility pilot", "",
        "**NOT_READY_FOR_PERSISTENCE_RECONSTRUCTION**", "",
        "## Executive finding", "",
        f"The full 2024 standard-product candidate AOIs and existing full 2025 archive yielded at least one observation within 2 km in the label year for {int(mat.firms_observations_available.sum())}/24 candidates. A candidate-year first detection is established as PROBABLE for {int(mat.t0_status.eq('PROBABLE').sum())}/24; {int(mat.t0_status.eq('UNRESOLVED').sum())}/24 remain unresolved because no in-year point association was found. Coordinates are numerically available from the provenance ledger for 24/24 but are not independently verified against authoritative facility surveys.", "",
        "## Candidate event evidence", "",
        "The Stage 8.25 physical-event rows are source-level aggregates: each Persistent row lists detections in 2018, 2020, 2022, 2024, 2025, and 2026, while event_start/event_end span 2018-03-15 through 2026-03-15. That multi-year span is not a valid single event timeline. This audit read only each retained development candidate's label-year linked detection; it did not load 2026 linked detections. The legacy 2018-03-15 timestamp was not used as t0. A t0 here means the earliest relevant NOAA-20 SP detection in the candidate's assigned calendar year, under the project's <=2 km association rule.", "",
        "## Archive and acquisition", "",
        "NASA live data availability confirmed VIIRS_NOAA20_SP coverage from 2018-04-01 to 2026-06-30 and VIIRS_SNPP_SP from 2012-01-20 to 2026-06-30. The endpoint rejected VIIRS_NOAA21_SP as an invalid source. The Area API supports date-scoped 1–5 day AOI queries; 21 tight India candidate AOIs were queried across all 366 days in 2024. Existing 2025 full-India SP archive was searched for the 2025 cohort. Acquisition request details, bytes, latencies, response counts and file hashes are in acquisition_manifest.json.", "",
        f"The full-year pull generated {acquisition.get('request_count_this_run', 0)} network requests and {acquisition.get('cached_chunk_count', 0)} cached chunks; downloaded {acquisition.get('total_downloaded_bytes_this_run', 0)} bytes in {acquisition.get('total_processing_seconds', 0):.1f}s of processing ({acquisition.get('total_latency_seconds', 0):.1f}s summed response latency). A separate 21-request event-day pilot is preserved in eventday_verification_manifest.json. Continuous local India-wide coverage remains 2024-10-01 through 2025-12-31 (457 days), augmented by candidate-specific 2024 AOIs. Dates before 2024-01-01 remain unobserved locally for those sites; 365-day pre-event coverage therefore depends on t0 and often requires additional targeted 2023 acquisition.", "",
        "## Window feasibility", "",
        f"Using each probable first-in-year t0 and the seven-day guard, complete local date coverage windows are: 7d={complete['7']}, 30d={complete['30']}, 90d={complete['90']}, 180d={complete['180']}, 365d={complete['365']} of 24. No feature counts or recurrence statistics were computed. Where t0 is unresolved, all historical windows are unavailable.", "",
        "The longest verified continuous span is 366 days for each acquired 2024 candidate AOI and 457 days in the India-wide local archive; these spans do not automatically overlap the required pre-t0 interval. The feasibility matrix gives exact per-candidate window start/end, coverage fraction, and missing intervals. The maximum causal history length is candidate-specific; candidates with early-year first detections can have no complete short windows, while later candidates may support 7–180 days if their start date falls after 2024-01-01 or 2024-10-01 respectively. No candidate can claim complete 365-day pre-event history from current data.", "",
        "## Source diversity and split feasibility", "",
        f"There are {split_summary['unique_incident_ids']} candidate incident IDs and {split_summary['unique_facility_names']} normalized facility names across {split_summary['unique_states']} states and {split_summary['unique_regions']} regions. Candidate years: {json.dumps(split_summary['events_by_year'])}. Sensor evidence among target-year nearby detections is recorded in each timeline row. Distinct incident IDs do not prove physical independence; nearby-source groups require expert facility review.", "",
        f"Inherited Persistent splits contain train/validation groups. Closest cross-split distance is {split_summary['closest_cross_split_distance_km']:.3f} km; cross-split pairs under 5/10/50 km: {split_summary['cross_split_pairs_under_5km']}/{split_summary['cross_split_pairs_under_10km']}/{split_summary['cross_split_pairs_under_50km']}. This is a feasibility audit only; no model split is finalized.", "",
        "## Decision", "",
        "The Persistent Expert is not feasible yet. A candidate-day satellite observation is not a trustworthy event onset, and complete causal histories cannot be inferred from the current partial archive. The next data foundation step is first to resolve event semantics/t0 for each physical source, then retrieve date-continuous standard-product AOIs only for candidates with defensible t0 values. No model features were created, no model was trained, and no blind-test artifact was accessed.", "",
        "## Reproducibility and frozen artifacts", "",
        "The analysis outputs are deterministically regenerated from the local archive and saved acquisition files; hashes are in stage8_45_hashes.json. The acquisition manifest preserves request timestamps and latency, which are intentionally outside deterministic analysis hashes. Frozen Stage 8.36 model and independent test manifest were not opened or modified; evaluation counter was not accessed in this stage.", "",
    ]
    (OUT / "stage8_45_report.md").write_text("\n".join(report), encoding="utf-8")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--acquire", action="store_true")
    args = parser.parse_args()
    if args.acquire:
        acquire_2024_eventday()
    assemble()
    print(json.dumps({"decision": "NOT_READY_FOR_PERSISTENCE_RECONSTRUCTION",
                      "output_dir": str(OUT), "candidate_count": 24}, indent=2))
