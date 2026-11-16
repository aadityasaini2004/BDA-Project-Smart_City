
import json
from pathlib import Path
from collections import Counter
from datetime import datetime, timezone

PROJECT_ROOT = Path(__file__).resolve().parents[2]

DATA_DIR = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "openaq"
    / "historical"
    / "sensor_12234787"
)

START = datetime(2025, 10, 31, 18, 30, tzinfo=timezone.utc)
END = datetime(2026, 10, 31, 18, 30, tzinfo=timezone.utc)

records = []

for page_file in sorted(DATA_DIR.glob("*/*.json")):

    if page_file.name == "manifest.json":
        continue

    with open(page_file, "r", encoding="utf-8") as file:
        payload = json.load(file)

    records.extend(payload.get("results", []))


timestamps = []
invalid_timestamps = 0
out_of_range = 0
invalid_values = 0
flagged_records = 0
coverage_values = []
monthly_counts = Counter()

for record in records:

    period = record.get("period", {})
    date_info = period.get("datetimeFrom", {})
    timestamp = date_info.get("utc")

    if not timestamp:
        invalid_timestamps += 1
        continue

    try:
        dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    except ValueError:
        invalid_timestamps += 1
        continue

    if not (START <= dt < END):
        out_of_range += 1
        continue

    timestamps.append(dt)

    local_timestamp = date_info.get("local")

    if local_timestamp:
        month = local_timestamp[:7]
        monthly_counts[month] += 1

    value = record.get("value")

    if not isinstance(value, (int, float)):
        invalid_values += 1

    flag_info = record.get("flagInfo", {})

    if flag_info.get("hasFlags", False):
        flagged_records += 1

    coverage = record.get("coverage", {})

    percent = coverage.get("percentCoverage")

    if isinstance(percent, (int, float)):
        coverage_values.append(percent)


unique_timestamps = set(timestamps)
duplicate_count = len(timestamps) - len(unique_timestamps)

expected_records = 8760
missing_records = expected_records - len(unique_timestamps)

print("\n========== DATA QUALITY REPORT ==========")

print("Total records:", len(records))
print("Valid timestamps:", len(timestamps))
print("Unique hourly timestamps:", len(unique_timestamps))
print("Duplicate timestamps:", duplicate_count)
print("Invalid timestamps:", invalid_timestamps)
print("Out-of-range records:", out_of_range)
print("Invalid values:", invalid_values)
print("Flagged records:", flagged_records)

print("\nExpected hourly records:", expected_records)
print("Missing hourly timestamps:", missing_records)

if coverage_values:
    average_coverage = sum(coverage_values) / len(coverage_values)
    print(
        "Average API coverage metadata:",
        round(average_coverage, 2), "%"
    )

print("\nMONTHLY RECORD COUNTS")

for month in sorted(monthly_counts):
    print(f"{month}: {monthly_counts[month]}")

print("\n=========================================")
