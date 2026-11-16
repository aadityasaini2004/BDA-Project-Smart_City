
import os
import csv
import time
import requests

from pathlib import Path
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from dotenv import load_dotenv


# --------------------------------------------------
# CONFIGURATION
# --------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[2]

load_dotenv(PROJECT_ROOT / ".env")

API_KEY = os.getenv("OPENAQ_API_KEY")

BASE_URL = "https://api.openaq.org/v3"

IST = ZoneInfo("Asia/Kolkata")

START_DATE = datetime(2025, 11, 1, 0, 0, tzinfo=IST)
END_DATE = datetime(2026, 11, 1, 0, 0, tzinfo=IST)

LIMIT = 1000
MIN_AVAILABILITY = 80.0

OUTPUT_DIR = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "openaq"
)

OUTPUT_FILE = OUTPUT_DIR / "pilot_sensor_coverage.csv"

SENSORS = [
    {
        "name": "Anand Vihar",
        "sensor_id": 12235610
    },
    {
        "name": "Punjabi Bagh",
        "sensor_id": 12234796
    },
    {
        "name": "ITO",
        "sensor_id": 12234753
    },
    {
        "name": "Dwarka Sector 8",
        "sensor_id": 12235020
    }
]


# --------------------------------------------------
# API REQUEST
# --------------------------------------------------

def fetch_sensor_month(sensor_id, start_utc, end_utc):
    url = f"{BASE_URL}/sensors/{sensor_id}/hours"

    headers = {
        "X-API-Key": API_KEY
    }

    params = {
        "datetime_from": start_utc.isoformat().replace("+00:00", "Z"),
        "datetime_to": end_utc.isoformat().replace("+00:00", "Z"),
        "limit": LIMIT,
        "page": 1
    }

    records = []

    while True:
        response = requests.get(
            url,
            headers=headers,
            params=params,
            timeout=60
        )

        response.raise_for_status()

        payload = response.json()
        results = payload.get("results", [])

        records.extend(results)

        if len(results) < LIMIT:
            break

        params["page"] += 1
        time.sleep(0.2)

    return records


# --------------------------------------------------
# MONTHLY EXTRACTION
# --------------------------------------------------

def test_sensor(sensor):
    sensor_id = sensor["sensor_id"]
    sensor_name = sensor["name"]

    print(f"\nTesting: {sensor_name} ({sensor_id})")

    all_records = []

    month_start = START_DATE

    while month_start < END_DATE:

        if month_start.month == 12:
            next_month = month_start.replace(
                year=month_start.year + 1,
                month=1
            )
        else:
            next_month = month_start.replace(
                month=month_start.month + 1
            )

        utc_start = month_start.astimezone(timezone.utc)
        utc_end = next_month.astimezone(timezone.utc)

        print(
            f"  Fetching {month_start.strftime('%Y-%m')}...",
            end=" "
        )

        try:
            records = fetch_sensor_month(
                sensor_id,
                utc_start,
                utc_end
            )

            all_records.extend(records)

            print(f"{len(records)} records")

        except requests.RequestException as error:
            print(f"FAILED: {error}")

        month_start = next_month

    return all_records


# --------------------------------------------------
# COVERAGE ANALYSIS
# --------------------------------------------------

def analyze_sensor(sensor, records):

    timestamps = set()
    valid_values = 0
    coverage_values = []

    for record in records:

        period = record.get("period", {})
        datetime_info = period.get("datetimeFrom", {})

        timestamp = datetime_info.get("utc")

        if timestamp:
            try:
                parsed = datetime.fromisoformat(
                    timestamp.replace("Z", "+00:00")
                )

                timestamps.add(parsed.astimezone(IST))

            except ValueError:
                pass

        value = record.get("value")

        if isinstance(value, (int, float)):
            valid_values += 1

        coverage = record.get("coverage", {})
        percent = coverage.get("percentCoverage")

        if isinstance(percent, (int, float)):
            coverage_values.append(percent)

    expected_hours = int(
        (END_DATE - START_DATE).total_seconds() / 3600
    )

    available_hours = len(timestamps)

    missing_hours = max(
        0,
        expected_hours - available_hours
    )

    availability = (
        available_hours / expected_hours * 100
        if expected_hours else 0
    )

    avg_coverage = (
        sum(coverage_values) / len(coverage_values)
        if coverage_values else None
    )

    status = (
        "PASS"
        if availability >= MIN_AVAILABILITY
        else "REVIEW"
    )

    return {
        "station": sensor["name"],
        "sensor_id": sensor["sensor_id"],
        "total_records": len(records),
        "unique_timestamps": available_hours,
        "expected_hours": expected_hours,
        "missing_hours": missing_hours,
        "availability_percent": round(availability, 2),
        "valid_numeric_values": valid_values,
        "avg_api_coverage_percent": (
            round(avg_coverage, 2)
            if avg_coverage is not None else ""
        ),
        "status": status
    }


# --------------------------------------------------
# MAIN
# --------------------------------------------------

def main():

    if not API_KEY:
        raise RuntimeError(
            "OPENAQ_API_KEY missing. Check your .env file."
        )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    results = []

    print("=" * 65)
    print("OPENAQ PILOT SENSOR COVERAGE TEST")
    print("Period: November 2025 - October 2026")
    print("=" * 65)

    for sensor in SENSORS:

        records = test_sensor(sensor)

        result = analyze_sensor(sensor, records)

        results.append(result)

        print(
            f"\n{result['station']}: "
            f"{result['availability_percent']}% availability "
            f"| {result['status']}"
        )

    fieldnames = list(results[0].keys())

    with open(
        OUTPUT_FILE,
        "w",
        newline="",
        encoding="utf-8"
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames
        )

        writer.writeheader()
        writer.writerows(results)

    print("\n" + "=" * 65)
    print("FINAL PILOT SUMMARY")
    print("=" * 65)

    for result in results:
        print(
            f"{result['station']:<20} "
            f"{result['availability_percent']:>7}% "
            f"{result['status']}"
        )

    print(f"\nSaved report: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
