
import os
import csv
import time
import math
import requests

from pathlib import Path
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from dotenv import load_dotenv


# ==================================================
# CONFIGURATION
# ==================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

load_dotenv(PROJECT_ROOT / ".env")

API_KEY = os.getenv("OPENAQ_API_KEY")

BASE_URL = "https://api.openaq.org/v3"
IST = ZoneInfo("Asia/Kolkata")

START_DATE = datetime(2025, 11, 1, 0, 0, tzinfo=IST)
END_DATE = datetime(2026, 11, 1, 0, 0, tzinfo=IST)

LIMIT = 1000
MAX_RETRIES = 3

OUTPUT_DIR = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "openaq"
    / "quality_audit"
)

SENSORS = [
    {"name": "R K Puram", "sensor_id": 12234787},
    {"name": "Anand Vihar", "sensor_id": 12235610},
    {"name": "Punjabi Bagh", "sensor_id": 12234796},
    {"name": "ITO", "sensor_id": 12234753},
    {"name": "Dwarka Sector 8", "sensor_id": 12235020},
]


# ==================================================
# DATE HELPERS
# ==================================================

def generate_months():

    months = []
    current = START_DATE

    while current < END_DATE:

        if current.month == 12:
            next_month = current.replace(
                year=current.year + 1,
                month=1
            )
        else:
            next_month = current.replace(
                month=current.month + 1
            )

        months.append((current, next_month))
        current = next_month

    return months


def expected_timestamps(start, end):

    current = start.astimezone(timezone.utc)
    finish = end.astimezone(timezone.utc)

    timestamps = set()

    while current < finish:
        timestamps.add(current)
        current = current.replace(
            hour=current.hour + 1
        ) if current.hour < 23 else current.replace(
            day=current.day,
            hour=0
        )

        # Advance correctly across day and month boundaries.
        # This assignment is replaced below by timedelta.
        # Kept outside the loop in the final implementation.

    return timestamps


def build_expected_timestamps(start, end):

    from datetime import timedelta

    current = start.astimezone(timezone.utc)
    finish = end.astimezone(timezone.utc)

    timestamps = set()

    while current < finish:
        timestamps.add(current)
        current += timedelta(hours=1)

    return timestamps


def parse_timestamp(record):

    period = record.get("period", {})
    datetime_info = period.get("datetimeFrom", {})

    timestamp = datetime_info.get("utc")

    if not timestamp:
        return None

    try:
        parsed = datetime.fromisoformat(
            timestamp.replace("Z", "+00:00")
        )

        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)

        return parsed.astimezone(timezone.utc)

    except (ValueError, TypeError):
        return None


# ==================================================
# API EXTRACTION
# ==================================================

def fetch_month(sensor_id, start, end):

    url = f"{BASE_URL}/sensors/{sensor_id}/hours"

    headers = {
        "X-API-Key": API_KEY
    }

    params = {
        "datetime_from": (
            start.astimezone(timezone.utc)
            .isoformat()
            .replace("+00:00", "Z")
        ),
        "datetime_to": (
            end.astimezone(timezone.utc)
            .isoformat()
            .replace("+00:00", "Z")
        ),
        "limit": LIMIT,
        "page": 1
    }

    records = []

    while True:

        for attempt in range(MAX_RETRIES):

            try:
                response = requests.get(
                    url,
                    headers=headers,
                    params=params,
                    timeout=60
                )

                response.raise_for_status()
                break

            except requests.RequestException:

                if attempt == MAX_RETRIES - 1:
                    raise

                time.sleep(2 ** attempt)

        payload = response.json()
        results = payload.get("results", [])

        records.extend(results)

        if len(results) < LIMIT:
            break

        params["page"] += 1
        time.sleep(0.2)

    return records


# ==================================================
# GAP ANALYSIS
# ==================================================

def find_missing_timestamps(expected, available):

    return sorted(expected - available)


def find_longest_gap(missing):

    if not missing:
        return 0, None, None

    from datetime import timedelta

    longest_start = missing[0]
    longest_end = missing[0]

    current_start = missing[0]
    current_end = missing[0]

    longest_hours = 1
    current_hours = 1

    for timestamp in missing[1:]:

        if timestamp - current_end == timedelta(hours=1):

            current_end = timestamp
            current_hours += 1

        else:

            if current_hours > longest_hours:
                longest_hours = current_hours
                longest_start = current_start
                longest_end = current_end

            current_start = timestamp
            current_end = timestamp
            current_hours = 1

    if current_hours > longest_hours:
        longest_hours = current_hours
        longest_start = current_start
        longest_end = current_end

    return longest_hours, longest_start, longest_end


# ==================================================
# MAIN AUDIT
# ==================================================

def audit_sensor(sensor, months):

    sensor_name = sensor["name"]
    sensor_id = sensor["sensor_id"]

    print("\n" + "=" * 60)
    print(f"AUDITING: {sensor_name} ({sensor_id})")
    print("=" * 60)

    all_available = set()
    all_missing = []

    total_records = 0
    duplicate_records = 0
    invalid_timestamps = 0
    valid_numeric_values = 0
    invalid_numeric_values = 0
    coverage_values = []

    tested_expected_hours = 0
    successful_months = 0
    failed_months = 0

    monthly_results = []

    for month_start, month_end in months:

        month_name = month_start.strftime("%Y-%m")

        print(f"Checking {month_name}...", end=" ")

        try:

            records = fetch_month(
                sensor_id,
                month_start,
                month_end
            )

            expected = build_expected_timestamps(
                month_start,
                month_end
            )

            available = set()

            for record in records:

                timestamp = parse_timestamp(record)

                if timestamp is None:
                    invalid_timestamps += 1
                else:
                    available.add(timestamp)

                value = record.get("value")

                if (
                    isinstance(value, (int, float))
                    and not isinstance(value, bool)
                    and math.isfinite(value)
                ):
                    valid_numeric_values += 1
                else:
                    invalid_numeric_values += 1

                coverage = record.get("coverage", {})
                percent = coverage.get("percentCoverage")

                if (
                    isinstance(percent, (int, float))
                    and math.isfinite(percent)
                ):
                    coverage_values.append(percent)

            # Restrict timestamps to the expected month.
            available = available.intersection(expected)

            missing = find_missing_timestamps(
                expected,
                available
            )

            total_records += len(records)
            duplicate_records += max(
                0,
                len(records) - len(available)
            )

            all_available.update(available)
            all_missing.extend(missing)

            expected_count = len(expected)
            available_count = len(available)

            availability = (
                available_count / expected_count * 100
                if expected_count else 0
            )

            tested_expected_hours += expected_count
            successful_months += 1

            monthly_results.append({
                "station": sensor_name,
                "sensor_id": sensor_id,
                "month": month_name,
                "status": "SUCCESS",
                "records_received": len(records),
                "unique_available_hours": available_count,
                "expected_hours": expected_count,
                "missing_hours": len(missing),
                "availability_percent": round(
                    availability, 2
                )
            })

            print(
                f"{available_count}/{expected_count} hours "
                f"({availability:.2f}%)"
            )

        except requests.RequestException as error:

            failed_months += 1

            monthly_results.append({
                "station": sensor_name,
                "sensor_id": sensor_id,
                "month": month_name,
                "status": "FAILED",
                "records_received": 0,
                "unique_available_hours": 0,
                "expected_hours": "",
                "missing_hours": "",
                "availability_percent": ""
            })

            print(f"FAILED: {error}")

    missing_hours, gap_start, gap_end = find_longest_gap(
        sorted(set(all_missing))
    )

    availability = (
        len(all_available) / tested_expected_hours * 100
        if tested_expected_hours else 0
    )

    avg_coverage = (
        sum(coverage_values) / len(coverage_values)
        if coverage_values else None
    )

    summary = {
        "station": sensor_name,
        "sensor_id": sensor_id,
        "total_records": total_records,
        "unique_available_hours": len(all_available),
        "tested_expected_hours": tested_expected_hours,
        "missing_hours": len(set(all_missing)),
        "availability_percent": round(availability, 2),
        "duplicate_records": duplicate_records,
        "invalid_timestamps": invalid_timestamps,
        "valid_numeric_values": valid_numeric_values,
        "invalid_numeric_values": invalid_numeric_values,
        "avg_api_coverage_percent": (
            round(avg_coverage, 2)
            if avg_coverage is not None else ""
        ),
        "successful_months": successful_months,
        "failed_months": failed_months,
        "longest_gap_hours": missing_hours,
        "longest_gap_start_ist": (
            gap_start.astimezone(IST).isoformat()
            if gap_start else ""
        ),
        "longest_gap_end_ist": (
            gap_end.astimezone(IST).isoformat()
            if gap_end else ""
        )
    }

    return summary, monthly_results, sorted(set(all_missing))


# ==================================================
# CSV EXPORT
# ==================================================

def save_csv(path, rows):

    if not rows:
        print(f"No data to save: {path}")
        return

    with open(
        path,
        "w",
        newline="",
        encoding="utf-8"
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=list(rows[0].keys())
        )

        writer.writeheader()
        writer.writerows(rows)

    print(f"Saved: {path}")


# ==================================================
# APPLICATION ENTRY POINT
# ==================================================

def main():

    if not API_KEY:
        raise RuntimeError(
            "OPENAQ_API_KEY missing. Check your .env file."
        )

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    months = generate_months()

    summaries = []
    monthly_reports = []
    missing_reports = []

    print("=" * 65)
    print("DELHI PILOT DATA QUALITY AUDIT")
    print("November 2025 - October 2026")
    print(f"Stations: {len(SENSORS)}")
    print("=" * 65)

    for sensor in SENSORS:

        summary, monthly, missing = audit_sensor(
            sensor,
            months
        )

        summaries.append(summary)
        monthly_reports.extend(monthly)

        for timestamp in missing:

            missing_reports.append({
                "station": sensor["name"],
                "sensor_id": sensor["sensor_id"],
                "missing_timestamp_ist": (
                    timestamp.astimezone(IST).isoformat()
                )
            })

    save_csv(
        OUTPUT_DIR / "pilot_station_quality.csv",
        summaries
    )

    save_csv(
        OUTPUT_DIR / "pilot_monthly_quality.csv",
        monthly_reports
    )

    save_csv(
        OUTPUT_DIR / "pilot_missing_hours.csv",
        missing_reports
    )

    print("\n" + "=" * 65)
    print("FINAL QUALITY SUMMARY")
    print("=" * 65)

    for result in summaries:

        print(
            f"{result['station']:<20} "
            f"{result['availability_percent']:>7}% | "
            f"Duplicates: {result['duplicate_records']} | "
            f"Failed months: {result['failed_months']}"
        )

    print("\nAudit completed.")


if __name__ == "__main__":
    main()
