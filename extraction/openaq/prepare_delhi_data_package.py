
"""
Prepare Delhi PM2.5 data package for team sharing.

Input:
    data/raw/openaq/historical/
    data/processed/openaq/

Outputs:
    data/processed/openaq/delhi_pm25_all_sensors.csv
    data/processed/openaq/delhi_pm25_station_summary.csv
    data/share/delhi_data_package/
    data/share/Delhi_PM25_Data_Package.zip

Includes existing R K Puram data.
"""

from pathlib import Path
import json
import shutil
import zipfile
import pandas as pd


ROOT = Path(__file__).resolve().parents[2]

RAW_DIR = ROOT / "data/raw/openaq/historical"
PROCESSED_DIR = ROOT / "data/processed/openaq"

REGISTRY_FILE = PROCESSED_DIR / "delhi_sensor_registry.csv"

CONSOLIDATED_FILE = (
    PROCESSED_DIR / "delhi_pm25_all_sensors.csv"
)

STATION_SUMMARY_FILE = (
    PROCESSED_DIR / "delhi_pm25_station_summary.csv"
)

SHARE_DIR = ROOT / "data/share"
PACKAGE_DIR = SHARE_DIR / "delhi_data_package"
ZIP_FILE = SHARE_DIR / "Delhi_PM25_Data_Package.zip"


# Important reports to include in the ZIP.
SUPPORTING_FILES = [
    PROCESSED_DIR / "delhi_sensor_registry.csv",
    PROCESSED_DIR / "extraction/delhi_extraction_summary.csv",
    PROCESSED_DIR / "evaluation/delhi_sensor_evaluation.csv",
    PROCESSED_DIR / "evaluation/delhi_sensor_monthly_evaluation.csv",
    PROCESSED_DIR / "quality_audit/pilot_station_quality.csv",
    PROCESSED_DIR / "quality_audit/pilot_monthly_quality.csv",
    PROCESSED_DIR / "quality_audit/pilot_missing_hours.csv",
    PROCESSED_DIR / "delhi_pm25_shortlist_with_coordinates.csv",
]


def normalize_id(value):
    return str(value).strip().replace(".0", "")


def first_existing_column(df, candidates):
    for column in candidates:
        if column in df.columns:
            return column
    return None


def load_registry():
    if not REGISTRY_FILE.exists():
        raise FileNotFoundError(REGISTRY_FILE)

    registry = pd.read_csv(REGISTRY_FILE, dtype={"sensor_id": str})
    registry["sensor_id"] = registry["sensor_id"].map(normalize_id)

    if registry["sensor_id"].duplicated().any():
        raise ValueError("Duplicate sensor IDs in registry.")

    name_col = first_existing_column(
        registry, ["station", "location_name", "name"]
    )
    lat_col = first_existing_column(
        registry, ["latitude", "lat"]
    )
    lon_col = first_existing_column(
        registry, ["longitude", "lon", "long"]
    )
    unit_col = first_existing_column(
        registry, ["parameter_units", "units", "unit"]
    )

    metadata = {}

    for _, row in registry.iterrows():
        sensor_id = row["sensor_id"]

        metadata[sensor_id] = {
            "station": row[name_col] if name_col else sensor_id,
            "latitude": row[lat_col] if lat_col else None,
            "longitude": row[lon_col] if lon_col else None,
            "parameter_units": row[unit_col] if unit_col else None,
        }

    return registry, metadata


def extract_timestamp(df, candidates):
    for column in candidates:
        if column in df.columns:
            return df[column]

    return None


def load_sensor_pages(metadata):
    if not RAW_DIR.exists():
        raise FileNotFoundError(RAW_DIR)

    all_frames = []
    total_files = 0
    total_records = 0
    errors = []

    sensor_dirs = sorted(RAW_DIR.glob("sensor_*"))

    if not sensor_dirs:
        raise RuntimeError("No sensor folders found in historical data.")

    print(f"Found {len(sensor_dirs)} sensor folders.")

    for sensor_dir in sensor_dirs:

        sensor_id = normalize_id(
            sensor_dir.name.replace("sensor_", "")
        )

        station_metadata = metadata.get(sensor_id)

        if station_metadata is None:
            print(f"WARNING: Sensor {sensor_id} not found in registry.")

            station_metadata = {
                "station": sensor_id,
                "latitude": None,
                "longitude": None,
                "parameter_units": None,
            }

        page_files = sorted(sensor_dir.glob("*/page_*.json"))

        print(
            f"\n{station_metadata['station']} "
            f"({sensor_id}): {len(page_files)} page files"
        )

        for page_file in page_files:

            try:
                with page_file.open("r", encoding="utf-8") as file:
                    payload = json.load(file)

                records = payload.get("results", [])

                if not isinstance(records, list):
                    raise ValueError("API results is not a list.")

                if not records:
                    continue

                df = pd.json_normalize(records, sep=".")

                df["sensor_id"] = sensor_id
                df["station"] = station_metadata["station"]
                df["latitude"] = station_metadata["latitude"]
                df["longitude"] = station_metadata["longitude"]
                df["parameter_units"] = station_metadata["parameter_units"]
                df["pollutant"] = "pm25"
                df["city"] = "Delhi"
                df["source_month"] = page_file.parent.name
                df["source_file"] = str(
                    page_file.relative_to(ROOT)
                )

                # Preserve original nested API fields.
                utc_timestamp = extract_timestamp(
                    df,
                    [
                        "period.datetimeFrom.utc",
                        "datetimeFrom.utc",
                        "datetime.utc",
                        "timestamp",
                    ],
                )

                local_timestamp = extract_timestamp(
                    df,
                    [
                        "period.datetimeFrom.local",
                        "datetimeFrom.local",
                        "datetime.local",
                    ],
                )

                if utc_timestamp is not None:
                    df["timestamp_utc"] = utc_timestamp

                if local_timestamp is not None:
                    df["timestamp_local"] = local_timestamp

                all_frames.append(df)

                total_files += 1
                total_records += len(df)

            except Exception as error:
                errors.append({
                    "file": str(page_file),
                    "error": str(error),
                })

                print(f"ERROR reading {page_file}: {error}")

        print(f"  Total records loaded so far: {total_records:,}")

    if not all_frames:
        raise RuntimeError("No hourly records could be loaded.")

    print("\nCombining dataframes...")
    combined = pd.concat(
        all_frames,
        ignore_index=True,
        sort=False
    )

    print(f"JSON page files read: {total_files}")
    print(f"Combined records: {len(combined):,}")

    return combined, errors


def create_station_summary(df):
    if "value" not in df.columns:
        print(
            "WARNING: No 'value' column found. "
            "Station statistics cannot be calculated."
        )
        return None

    df["value"] = pd.to_numeric(df["value"], errors="coerce")

    summary = (
        df.groupby(["sensor_id", "station"], dropna=False)
        .agg(
            total_records=("value", "size"),
            valid_values=("value", "count"),
            average_pm25=("value", "mean"),
            median_pm25=("value", "median"),
            minimum_pm25=("value", "min"),
            maximum_pm25=("value", "max"),
            latitude=("latitude", "first"),
            longitude=("longitude", "first"),
            unit=("parameter_units", "first"),
        )
        .reset_index()
    )

    summary.to_csv(STATION_SUMMARY_FILE, index=False)

    return summary


def create_readme(df, errors):
    readme = f"""# Delhi PM2.5 Historical Dataset

## Project scope

- City: Delhi, India
- Pollutant: PM2.5
- Source: OpenAQ API v3
- Historical period: 1 November 2025 to 31 October 2026
- Data frequency: Hourly

## Dataset contents

- Consolidated hourly records: {len(df):,}
- Sensors represented: {df['sensor_id'].nunique()}
- JSON page files successfully read: Original source files are included.
- Consolidation errors: {len(errors)}

## Primary pipeline input

`delhi_pm25_all_sensors.csv`

## Important columns

- sensor_id: OpenAQ sensor ID
- station: Monitoring station name
- timestamp_utc / timestamp_local: Available measurement period timestamps
- value: PM2.5 measurement value
- parameter_units: Unit from sensor registry, where available
- latitude / longitude: Sensor coordinates
- pollutant: pm25
- city: Delhi
- source_month: Source month folder
- source_file: Original JSON page path

Original API fields are preserved as flattened columns where available.

## Important caution

Missing hourly observations are not fabricated or interpolated.
The consolidated dataset contains records returned by the API.
Check timestamps and units before analysis or joining weather data.

OpenAQ hourly measurements are not automatically equivalent to official AQI.

## Folder structure

- `csv/`: Consolidated data, registry and reports
- `raw_historical/`: Original monthly JSON API responses and manifests

## Pipeline recommendation

Use `delhi_pm25_all_sensors.csv` as the initial input for Databricks Bronze ingestion.
Retain `raw_historical/` for source traceability and reproducibility.
"""

    (PACKAGE_DIR / "README.md").write_text(
        readme,
        encoding="utf-8"
    )


def prepare_package(df, errors):
    SHARE_DIR.mkdir(parents=True, exist_ok=True)

    csv_dir = PACKAGE_DIR / "csv"
    csv_dir.mkdir(parents=True, exist_ok=True)

    # Main consolidated dataset.
    shutil.copy2(
        CONSOLIDATED_FILE,
        csv_dir / CONSOLIDATED_FILE.name
    )

    # Station summary.
    if STATION_SUMMARY_FILE.exists():
        shutil.copy2(
            STATION_SUMMARY_FILE,
            csv_dir / STATION_SUMMARY_FILE.name
        )

    # Supporting CSVs.
    copied = []

    for source in SUPPORTING_FILES:
        if source.exists():
            shutil.copy2(source, csv_dir / source.name)
            copied.append(source.name)
        else:
            print(f"OPTIONAL FILE NOT FOUND: {source}")

    # Copy original JSON data and manifests.
    raw_destination = PACKAGE_DIR / "raw_historical"

    if raw_destination.exists():
        shutil.rmtree(raw_destination)

    shutil.copytree(RAW_DIR, raw_destination)

    # Consolidation error report, if required.
    if errors:
        pd.DataFrame(errors).to_csv(
            csv_dir / "consolidation_errors.csv",
            index=False
        )

    create_readme(df, errors)

    # Replace previous ZIP to avoid stale files.
    if ZIP_FILE.exists():
        ZIP_FILE.unlink()

    print("\nCreating ZIP package...")

    with zipfile.ZipFile(
        ZIP_FILE,
        "w",
        compression=zipfile.ZIP_DEFLATED,
        compresslevel=6
    ) as archive:

        for file_path in PACKAGE_DIR.rglob("*"):
            if file_path.is_file():
                archive.write(
                    file_path,
                    file_path.relative_to(SHARE_DIR)
                )

    print(f"Supporting CSVs copied: {len(copied)}")


def main():
    print("\n========== DELHI DATA PACKAGE BUILDER ==========\n")

    registry, metadata = load_registry()

    print(f"Registry sensors: {len(registry)}")

    df, errors = load_sensor_pages(metadata)

    # Keep all original API rows. Do not silently drop duplicates.
    if "sensor_id" not in df.columns:
        raise ValueError("Consolidated data has no sensor_id.")

    if "value" in df.columns:
        df["value"] = pd.to_numeric(
            df["value"], errors="coerce"
        )

    # Add duplicate indicator without deleting records.
    if "timestamp_utc" in df.columns:
        df["duplicate_sensor_timestamp"] = df.duplicated(
            subset=["sensor_id", "timestamp_utc"],
            keep=False
        )

    df.to_csv(CONSOLIDATED_FILE, index=False)

    print("\nConsolidated CSV saved:")
    print(CONSOLIDATED_FILE)

    summary = create_station_summary(df)

    if summary is not None:
        print("\nStation summary:")
        print(summary.head(10).to_string(index=False))

    prepare_package(df, errors)

    print("\n========== PACKAGE COMPLETE ==========")
    print(f"Total records: {len(df):,}")
    print(f"Unique sensors: {df['sensor_id'].nunique()}")
    print(f"JSON read errors: {len(errors)}")
    print(f"Consolidated CSV: {CONSOLIDATED_FILE}")
    print(f"Station summary: {STATION_SUMMARY_FILE}")
    print(f"ZIP package: {ZIP_FILE}")

    if errors:
        print(
            "\nWARNING: Some JSON pages could not be read. "
            "Check consolidation_errors.csv before sharing."
        )


if __name__ == "__main__":
    main()
