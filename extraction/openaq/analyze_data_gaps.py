
import csv
import json

from pathlib import Path
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo


PROJECT_ROOT = Path(__file__).resolve().parents[2]

DATA_DIR = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "openaq"
    / "historical"
    / "sensor_12234787"
)

OUTPUT_DIR = DATA_DIR / "quality"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

START = datetime(2025, 10, 31, 18, 30, tzinfo=timezone.utc)
END = datetime(2026, 10, 31, 18, 30, tzinfo=timezone.utc)

IST = ZoneInfo("Asia/Kolkata")


# Load all extracted records
records = []

for file_path in sorted(DATA_DIR.glob("*/*.json")):

    if file_path.name == "manifest.json":
        continue

    with open(file_path, "r", encoding="utf-8") as file:
        payload = json.load(file)

    records.extend(payload.get("results", []))


# Extract timestamps
available = set()

for record in records:

    timestamp = (
        record.get("period", {})
        .get("datetimeFrom", {})
        .get("utc")
    )

    if timestamp:
        dt = datetime.fromisoformat(
            timestamp.replace("Z", "+00:00")
        )
        available.add(dt)


# Generate all expected hourly timestamps
expected = set()

current = START

while current < END:
    expected.add(current)
    current += timedelta(hours=1)


missing = sorted(expected - available)


# Group consecutive missing hours into gaps
gaps = []

for timestamp in missing:

    if not gaps or timestamp != gaps[-1]["end"] + timedelta(hours=1):

        gaps.append({
            "start": timestamp,
            "end": timestamp,
            "hours": 1
        })

    else:
        gaps[-1]["end"] = timestamp
        gaps[-1]["hours"] += 1


# Save individual missing hours
missing_file = OUTPUT_DIR / "missing_hours.csv"

with open(missing_file, "w", newline="", encoding="utf-8") as file:

    writer = csv.writer(file)

    writer.writerow([
        "missing_timestamp_utc",
        "missing_timestamp_ist"
    ])

    for timestamp in missing:

        writer.writerow([
            timestamp.isoformat(),
            timestamp.astimezone(IST).isoformat()
        ])


# Save grouped gaps
gap_file = OUTPUT_DIR / "gap_summary.csv"

with open(gap_file, "w", newline="", encoding="utf-8") as file:

    writer = csv.writer(file)

    writer.writerow([
        "gap_start_ist",
        "gap_end_ist",
        "missing_hours"
    ])

    for gap in gaps:

        writer.writerow([
            gap["start"].astimezone(IST).isoformat(),
            gap["end"].astimezone(IST).isoformat(),
            gap["hours"]
        ])


# Display results
print("\n========== MISSING DATA ANALYSIS ==========")

print("Expected hours:", len(expected))
print("Available hours:", len(available))
print("Missing hours:", len(missing))
print("Continuous gap periods:", len(gaps))

print("\nLONGEST DATA GAPS")

for gap in sorted(
    gaps,
    key=lambda item: item["hours"],
    reverse=True
)[:10]:

    start = gap["start"].astimezone(IST)
    end = gap["end"].astimezone(IST)

    print(
        f"{start} -> {end} | "
        f"{gap['hours']} missing hours"
    )


print("\nSaved reports:")
print(missing_file)
print(gap_file)

print("\n==========================================")
