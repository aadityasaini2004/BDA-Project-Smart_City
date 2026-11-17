
"""
Build the authoritative Delhi PM2.5 sensor registry.

Inputs:
1. data/processed/openaq/delhi_pm25_shortlist_with_coordinates.csv
2. data/processed/openaq/evaluation/delhi_sensor_evaluation.csv
3. data/processed/openaq/quality_audit/pilot_station_quality.csv

Output:
data/processed/openaq/delhi_sensor_registry.csv
"""

from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]

SHORTLIST_FILE = (
    ROOT / "data/processed/openaq/delhi_pm25_shortlist_with_coordinates.csv"
)
EVALUATION_FILE = (
    ROOT / "data/processed/openaq/evaluation/delhi_sensor_evaluation.csv"
)
PILOT_FILE = (
    ROOT / "data/processed/openaq/quality_audit/pilot_station_quality.csv"
)
OUTPUT_FILE = ROOT / "data/processed/openaq/delhi_sensor_registry.csv"

REJECTED_SENSOR_IDS = {"12236376"}
MIN_AVAILABILITY = 80.0


def read_csv(path):
    if not path.exists():
        raise FileNotFoundError(f"Required file not found: {path}")

    df = pd.read_csv(path)
    if df.empty:
        raise ValueError(f"File is empty: {path}")

    return df


def normalize_sensor_id(series):
    return (
        series.astype(str)
        .str.strip()
        .str.replace(r"\.0$", "", regex=True)
    )


def find_column(df, candidates, file_label):
    for col in candidates:
        if col in df.columns:
            return col

    raise ValueError(
        f"Could not find any of {candidates} in {file_label}.\n"
        f"Available columns: {list(df.columns)}"
    )


def standardize_report(df, file_label, is_pilot):
    sensor_col = find_column(df, ["sensor_id"], file_label)
    station_col = find_column(
        df, ["station", "location_name", "name"], file_label
    )
    availability_col = find_column(
        df, ["availability_percent"], file_label
    )

    result = pd.DataFrame({
        "sensor_id": normalize_sensor_id(df[sensor_col]),
        "station": df[station_col].astype(str).str.strip(),
        "availability_percent": pd.to_numeric(
            df[availability_col], errors="coerce"
        ),
        "duplicate_records": pd.to_numeric(
            df["duplicate_records"], errors="coerce"
        ) if "duplicate_records" in df.columns else 0,
        "invalid_timestamps": pd.to_numeric(
            df["invalid_timestamps"], errors="coerce"
        ) if "invalid_timestamps" in df.columns else 0,
        "invalid_numeric_values": pd.to_numeric(
            df["invalid_numeric_values"], errors="coerce"
        ) if "invalid_numeric_values" in df.columns else 0,
        "successful_months": pd.to_numeric(
            df["successful_months"], errors="coerce"
        ) if "successful_months" in df.columns else 0,
        "failed_months": pd.to_numeric(
            df["failed_months"], errors="coerce"
        ) if "failed_months" in df.columns else 0,
    })

    result["is_pilot"] = is_pilot
    return result


def main():
    print("Loading Delhi sensor files...")

    shortlist = read_csv(SHORTLIST_FILE)
    evaluation = read_csv(EVALUATION_FILE)
    pilot = read_csv(PILOT_FILE)

    # Validate and standardize shortlist.
    shortlist_sensor_col = find_column(
        shortlist, ["sensor_id"], "Delhi shortlist"
    )
    shortlist["sensor_id"] = normalize_sensor_id(
        shortlist[shortlist_sensor_col]
    )

    if shortlist["sensor_id"].duplicated().any():
        duplicates = shortlist.loc[
            shortlist["sensor_id"].duplicated(), "sensor_id"
        ].tolist()
        raise ValueError(f"Duplicate sensor IDs in shortlist: {duplicates}")

    # Normalize the two quality reports.
    evaluation_std = standardize_report(
        evaluation, "Sensor evaluation", is_pilot=False
    )
    pilot_std = standardize_report(
        pilot, "Pilot quality audit", is_pilot=True
    )

    if evaluation_std["sensor_id"].duplicated().any():
        raise ValueError("Duplicate sensor IDs in evaluation report.")

    if pilot_std["sensor_id"].duplicated().any():
        raise ValueError("Duplicate sensor IDs in pilot report.")

    # Five pilot sensors and 37 additional evaluated sensors.
    if len(pilot_std) != 5:
        raise ValueError(
            f"Expected 5 pilot sensors, found {len(pilot_std)}."
        )

    if len(evaluation_std) != 37:
        raise ValueError(
            f"Expected 37 evaluated sensors, found {len(evaluation_std)}."
        )

    overlap = set(evaluation_std["sensor_id"]) & set(pilot_std["sensor_id"])
    if overlap:
        raise ValueError(
            f"Pilot sensors unexpectedly appear in evaluation: {sorted(overlap)}"
        )

    reports = pd.concat(
        [evaluation_std, pilot_std],
        ignore_index=True
    )

    if reports["sensor_id"].duplicated().any():
        raise ValueError("Duplicate sensor IDs found across reports.")

    # Every shortlisted sensor must have a quality report.
    shortlist_ids = set(shortlist["sensor_id"])
    report_ids = set(reports["sensor_id"])

    missing_reports = shortlist_ids - report_ids
    unexpected_reports = report_ids - shortlist_ids

    if missing_reports or unexpected_reports:
        raise ValueError(
            f"Sensor mismatch.\n"
            f"Missing reports: {sorted(missing_reports)}\n"
            f"Unexpected report IDs: {sorted(unexpected_reports)}"
        )

    # Merge shortlist metadata and quality results.
    registry = shortlist.merge(
        reports,
        on="sensor_id",
        how="left",
        validate="one_to_one",
        suffixes=("", "_report")
    )

    # Prefer the station name from the quality report when available.
    if "station" in registry.columns:
        name_col = next(
            (c for c in ["location_name", "name", "location"] if c in registry.columns),
            None
        )
        if name_col:
            registry["station"] = registry["station"].fillna(
                registry[name_col]
            )

    # Mark eligibility. Rejected sensor remains in the registry.
    registry["evaluation_status"] = "PASS"
    registry.loc[
        registry["availability_percent"] < MIN_AVAILABILITY,
        "evaluation_status"
    ] = "REJECT"

    registry.loc[
        registry["sensor_id"].isin(REJECTED_SENSOR_IDS),
        "evaluation_status"
    ] = "REJECT"

    registry["eligible_for_extraction"] = (
        (registry["evaluation_status"] == "PASS")
        & (registry["availability_percent"] >= MIN_AVAILABILITY)
    )

    registry["rejection_reason"] = ""
    registry.loc[
        registry["sensor_id"].isin(REJECTED_SENSOR_IDS),
        "rejection_reason"
    ] = "Very low historical timestamp availability"

    registry["quality_threshold_percent"] = MIN_AVAILABILITY
    registry["historical_start_date"] = "2025-11-01"
    registry["historical_end_date"] = "2026-10-31"

    # Check coordinates exist.
    lat_col = find_column(
        registry, ["latitude", "lat"], "Merged registry"
    )
    lon_col = find_column(
        registry, ["longitude", "lon", "long"], "Merged registry"
    )

    registry[lat_col] = pd.to_numeric(
        registry[lat_col], errors="coerce"
    )
    registry[lon_col] = pd.to_numeric(
        registry[lon_col], errors="coerce"
    )

    if registry[[lat_col, lon_col]].isna().any().any():
        raise ValueError("Some sensors are missing valid coordinates.")

    # Final integrity checks.
    if len(registry) != 42:
        raise ValueError(
            f"Expected 42 registry rows, got {len(registry)}."
        )

    if registry["sensor_id"].nunique() != 42:
        raise ValueError("Registry does not contain 42 unique sensor IDs.")

    eligible_count = int(registry["eligible_for_extraction"].sum())
    rejected_count = len(registry) - eligible_count

    if eligible_count != 41 or rejected_count != 1:
        raise ValueError(
            f"Expected 41 eligible and 1 rejected; got "
            f"{eligible_count} eligible and {rejected_count} rejected."
        )

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    registry = registry.sort_values(
        ["eligible_for_extraction", "availability_percent"],
        ascending=[False, False]
    )

    registry.to_csv(OUTPUT_FILE, index=False)

    print("\n========== REGISTRY BUILD SUCCESS ==========")
    print(f"Total sensors       : {len(registry)}")
    print(f"Pilot sensors       : {int(registry['is_pilot'].sum())}")
    print(f"Eligible sensors    : {eligible_count}")
    print(f"Rejected sensors    : {rejected_count}")
    print(f"Rejected sensor IDs : {', '.join(REJECTED_SENSOR_IDS)}")
    print(f"Output              : {OUTPUT_FILE}")

    print("\nTop 10 eligible sensors:")
    print(
        registry.loc[
            registry["eligible_for_extraction"],
            ["sensor_id", "station", "availability_percent"]
        ].head(10).to_string(index=False)
    )


if __name__ == "__main__":
    main()
