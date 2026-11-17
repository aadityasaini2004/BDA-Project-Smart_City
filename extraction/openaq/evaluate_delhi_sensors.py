
import os
import csv
import time
import math
import requests

from pathlib import Path
from datetime import datetime, timezone, timedelta
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

START_DATE = datetime(2025, 11, 1, tzinfo=IST)
END_DATE = datetime(2026, 11, 1, tzinfo=IST)

LIMIT = 1000
MAX_RETRIES = 4
MIN_AVAILABILITY = 80.0

INPUT_FILE = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "openaq"
    / "delhi_pm25_shortlist_with_coordinates.csv"
)

OUTPUT_DIR = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "openaq"
    / "evaluation"
)

SUMMARY_FILE = OUTPUT_DIR / "delhi_sensor_evaluation.csv"
MONTHLY_FILE = OUTPUT_DIR / "delhi_sensor_monthly_evaluation.csv"

# Five stations already evaluated in the pilot.
PILOT_SENSOR_IDS = {
    12234787,  # R K Puram
    12235610,  # Anand Vihar
    12234796,  # Punjabi Bagh
    12234753,  # ITO
    12235020,  # Dwarka Sector 8
}


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
# LOAD SENSOR SHORTLIST
# ==================================================

def load_sensors():

    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            f"Shortlist not found: {INPUT_FILE}"
        )

    sensors = []

    with open(
        INPUT_FILE,
        "r",
        encoding="utf-8-sig",
        newline=""
    ) as file:

        reader = csv.DictReader(file)

        if not reader.fieldnames:
            raise ValueError("Shortlist CSV has no headers.")

        for row in reader:

            sensor_id = (
                row.get("sensor_id")
                or row.get("sensorId")
            )

            if not sensor_id:
                continue

            try:
                sensor_id = int(sensor_id)
            except (ValueError, TypeError):
                continue

            if sensor_id in PILOT_SENSOR_IDS:
                continue

            sensors.append({
                "station": (
                    row.get("location_name")
                    or row.get("station")
                    or row.get("name")
                    or "Unknown"
                ),
                "sensor_id": sensor_id,
                "parameter": (
                    row.get("parameter_name")
                    or "pm25"
                ),
                "latitude": row.get("latitude", ""),
                "longitude": row.get("longitude", "")
            })

    # Prevent duplicate sensor IDs in the input CSV.
    unique_sensors = {}
    for sensor in sensors:
        unique_sensors[sensor["sensor_id"]] = sensor

    return list(unique_sensors.values())


# ==================================================
# OPENAQ API REQUEST
# ==================================================

def fetch_month(sensor_id, start, end, session):

    url = f"{BASE_URL}/sensors/{sensor_id}/hours"

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
                response = session.get(
                    url,
                    params=params,
                    timeout=60
                )

                # Retry rate limits and temporary server errors.
                if response.status_code == 429 or response.status_code >= 500:
                    if attempt == MAX_RETRIES - 1:
                        response.raise_for_status()

                    retry_after = response.headers.get("Retry-After")

                    try:
                        wait = float(retry_after)
                    except (ValueError, TypeError):
                        wait = 2 ** attempt

                    time.sleep(min(wait, 60))
                    continue

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
# SENSOR EVALUATION
# ==================================================

def evaluate_sensor(sensor, months, session):

    station = sensor["station"]
    sensor_id = sensor["sensor_id"]

    print("\n" + "=" * 60)
    print(f"Evaluating: {station} | Sensor ID: {sensor_id}")
    print("=" * 60)

    all_timestamps = set()

    total_records = 0
    duplicate_records = 0
    invalid_timestamps = 0
    valid_values = 0
    invalid_values = 0

    coverage_values = []

    successful_months = 0
    failed_months = 0

    monthly_results = []

    for month_start, month_end in months:

        month_name = month_start.strftime("%Y-%m")

        print(f"  {month_name}: ", end="", flush=True)

        expected = expected_timestamps(
            month_start,
            month_end
        )

        try:

            records = fetch_month(
                sensor_id,
                month_start,
                month_end,
                session
            )

            month_timestamps = []
            month_numeric_values = 0
            month_invalid_values = 0
            month_coverage = []

            for record in records:

                timestamp = parse_timestamp(record)

                if timestamp is None:
                    invalid_timestamps += 1
                else:
                    month_timestamps.append(timestamp)

                value = record.get("value")

                if (
                    isinstance(value, (int, float))
                    and not isinstance(value, bool)
                    and math.isfinite(value)
                ):
                    valid_values += 1
                    month_numeric_values += 1
                else:
                    invalid_values += 1
                    month_invalid_values += 1

                coverage = record.get("coverage") or {}
                percent = coverage.get("percentCoverage")

                if (
                    isinstance(percent, (int, float))
                    and not isinstance(percent, bool)
                    and math.isfinite(percent)
                ):
                    coverage_values.append(percent)
                    month_coverage.append(percent)

            # Count duplicates using all returned timestamps.
            unique_month_timestamps = set(month_timestamps)

            duplicate_records += (
                len(month_timestamps)
                - len(unique_month_timestamps)
            )

            # Keep only timestamps expected within this month.
            available = unique_month_timestamps.intersection(
                expected
            )

            missing = expected - available

            all_timestamps.update(available)

            expected_count = len(expected)
            available_count = len(available)

            availability = (
                available_count / expected_count * 100
                if expected_count else 0
            )

            avg_coverage = (
                sum(month_coverage) / len(month_coverage)
                if month_coverage else None
            )

            successful_months += 1

            monthly_results.append({
                "station": station,
                "sensor_id": sensor_id,
                "month": month_name,
                "status": "SUCCESS",
                "records_received": len(records),
                "unique_timestamps": len(unique_month_timestamps),
                "available_hours": available_count,
                "expected_hours": expected_count,
                "missing_hours": len(missing),
                "availability_percent": round(availability, 2),
                "valid_numeric_values": month_numeric_values,
                "invalid_numeric_values": month_invalid_values,
                "avg_api_coverage_percent": (
                    round(avg_coverage, 2)
                    if avg_coverage is not None else ""
                )
            })

            print(
                f"{available_count}/{expected_count} hours "
                f"({availability:.2f}%)"
            )

        except requests.RequestException as error:

            failed_months += 1

            monthly_results.append({
                "station": station,
                "sensor_id": sensor_id,
                "month": month_name,
                "status": "FAILED",
                "records_received": "",
                "unique_timestamps": "",
                "available_hours": "",
                "expected_hours": len(expected),
                "missing_hours": "",
                "availability_percent": "",
                "valid_numeric_values": "",
                "invalid_numeric_values": "",
                "avg_api_coverage_percent": ""
            })

            print(f"FAILED: {error}")

    expected_total = sum(
        len(expected_timestamps(start, end))
        for start, end in months
        if any(
            row["month"] == start.strftime("%Y-%m")
            and row["status"] == "SUCCESS"
            for row in monthly_results
        )
    )

    available_total = len(all_timestamps)

    availability = (
        available_total / expected_total * 100
        if expected_total else 0
    )

    avg_coverage = (
        sum(coverage_values) / len(coverage_values)
        if coverage_values else None
    )

    if failed_months:
        status = "INCOMPLETE"
    elif availability >= MIN_AVAILABILITY:
        status = "PASS"
    elif availability >= 60:
        status = "REVIEW"
    else:
        status = "REJECT"

    summary = {
        "station": station,
        "sensor_id": sensor_id,
        "parameter": sensor["parameter"],
        "latitude": sensor["latitude"],
        "longitude": sensor["longitude"],
        "total_records": total_records + sum(
            int(row["records_received"])
            for row in monthly_results
            if row["status"] == "SUCCESS"
        ),
        "available_hours": available_total,
        "expected_hours": expected_total,
        "missing_hours": max(
            0, expected_total - available_total
        ),
        "availability_percent": round(availability, 2),
        "duplicate_records": duplicate_records,
        "invalid_timestamps": invalid_timestamps,
        "valid_numeric_values": valid_values,
        "invalid_numeric_values": invalid_values,
        "avg_api_coverage_percent": (
            round(avg_coverage, 2)
            if avg_coverage is not None else ""
        ),
        "successful_months": successful_months,
        "failed_months": failed_months,
        "status": status
    }

    return summary, monthly_results


# ==================================================
# CSV EXPORT
# ==================================================

def save_csv(path, rows):

    if not rows:
        print(f"No rows to save: {path}")
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
# MAIN
# ==================================================

def main():

    if not API_KEY:
        raise RuntimeError(
            "OPENAQ_API_KEY missing. Check your .env file."
        )

    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            f"Input shortlist not found: {INPUT_FILE}"
        )

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    sensors = load_sensors()
    months = generate_months()

    if not sensors:
        raise RuntimeError(
            "No eligible sensors found. Check the shortlist CSV "
            "and its sensor_id column."
        )

    print("=" * 65)
    print("DELHI PM2.5 SENSOR BATCH EVALUATION")
    print("=" * 65)
    print(f"Shortlisted sensors: 42")
    print(f"Pilot sensors skipped: {len(PILOT_SENSOR_IDS)}")
    print(f"Sensors to evaluate: {len(sensors)}")
    print("Period: November 2025 - October 2026")
    print("=" * 65)

    session = requests.Session()
    session.headers.update({
        "X-API-Key": API_KEY,
        "Accept": "application/json"
    })

    summaries = []
    monthly_reports = []

    try:
        for index, sensor in enumerate(sensors, start=1):

            print(
                f"\nSENSOR {index}/{len(sensors)}"
            )

            summary, monthly = evaluate_sensor(
                sensor,
                months,
                session
            )

            summaries.append(summary)
            monthly_reports.extend(monthly)

            print(
                f"RESULT: {summary['station']} | "
                f"{summary['availability_percent']}% | "
                f"{summary['status']}"
            )

    finally:
        session.close()

    save_csv(SUMMARY_FILE, summaries)
    save_csv(MONTHLY_FILE, monthly_reports)

    print("\n" + "=" * 65)
    print("FINAL EVALUATION SUMMARY")
    print("=" * 65)

    for result in summaries:
        print(
            f"{result['station']:<35} "
            f"{result['availability_percent']:>7}% "
            f"{result['status']}"
        )

    print("\nStatus counts:")

    for status in ["PASS", "REVIEW", "REJECT", "INCOMPLETE"]:
        count = sum(
            row["status"] == status
            for row in summaries
        )
        print(f"{status}: {count}")

    print("\nEvaluation completed.")


if __name__ == "__main__":
    main()
