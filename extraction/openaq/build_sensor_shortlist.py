
import csv
import json
from pathlib import Path
from datetime import datetime, timezone


PROJECT_ROOT = Path(__file__).resolve().parents[2]

SENSOR_FILE = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "openaq"
    / "delhi_sensors.json"
)

OUTPUT_DIR = PROJECT_ROOT / "data" / "processed" / "openaq"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Project period in UTC:
# 1 Nov 2025 00:00 IST through 31 Oct 2026 23:00 IST
START = datetime(2025, 10, 31, 18, 30, tzinfo=timezone.utc)
LAST_HOUR = datetime(2026, 10, 31, 17, 30, tzinfo=timezone.utc)

# Explicitly exclude surrounding NCR locations from Delhi proper.
NCR_TERMS = [
    "gurugram",
    "gurgaon",
    "noida",
    "faridabad",
    "ghaziabad",
    "bahadurgarh",
    "loni",
    "khora",
]


def parse_utc(value):
    if not value:
        return None

    try:
        return datetime.fromisoformat(
            value.replace("Z", "+00:00")
        )
    except (ValueError, AttributeError):
        return None


def is_ncr_location(name):
    name = name.lower()
    return any(term in name for term in NCR_TERMS)


def main():

    with open(SENSOR_FILE, "r", encoding="utf-8") as file:
        sensors = json.load(file)

    pm25_sensors = [
        item for item in sensors
        if item.get("parameter_name", "").lower() == "pm25"
    ]

    full_period_candidates = []

    for item in pm25_sensors:

        first = item.get("sensor_datetime_first") or {}
        last = item.get("sensor_datetime_last") or {}

        first_utc = parse_utc(first.get("utc"))
        last_utc = parse_utc(last.get("utc"))

        if not first_utc or not last_utc:
            continue

        if first_utc <= START and last_utc >= LAST_HOUR:

            location_name = item.get("location_name", "")

            full_period_candidates.append({
                "location_id": item.get("location_id"),
                "location_name": location_name,
                "sensor_id": item.get("sensor_id"),
                "parameter": "pm25",
                "units": item.get("parameter_units"),
                "first_record_utc": first.get("utc"),
                "last_record_utc": last.get("utc"),
                "ncr_location": is_ncr_location(location_name),
            })

    full_period_candidates.sort(
        key=lambda x: (x["location_name"], x["sensor_id"])
    )

    delhi_candidates = [
        item for item in full_period_candidates
        if not item["ncr_location"]
    ]

    fields = [
        "location_id",
        "location_name",
        "sensor_id",
        "parameter",
        "units",
        "first_record_utc",
        "last_record_utc",
        "ncr_location",
    ]

    def save_csv(filename, rows):
        path = OUTPUT_DIR / filename

        with open(path, "w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)

        print(f"Saved: {path}")

    save_csv("pm25_full_period_candidates.csv", full_period_candidates)
    save_csv("delhi_pm25_shortlist.csv", delhi_candidates)

    print("\n========== SENSOR SHORTLIST ==========")
    print("Total sensors in inventory:", len(sensors))
    print("PM2.5 sensors:", len(pm25_sensors))
    print("Full-period metadata candidates:", len(full_period_candidates))
    print("Delhi shortlist after NCR name exclusion:", len(delhi_candidates))
    print("NCR candidates separated:", len(full_period_candidates) - len(delhi_candidates))

    print("\nDELHI PM2.5 CANDIDATES")

    for item in delhi_candidates:
        print(
            f"{item['location_name']} | "
            f"Sensor ID: {item['sensor_id']}"
        )

    print("\n======================================")


if __name__ == "__main__":
    main()
