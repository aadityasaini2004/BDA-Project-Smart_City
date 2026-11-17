
"""
Delhi PM2.5 Historical Data Extraction
Period: November 2025 - October 2026
Source: OpenAQ API v3

Features:
- Reads approved sensors from the sensor registry.
- Extracts hourly data month by month.
- Saves original API JSON responses.
- Retries temporary API failures.
- Resumes completed months.
- Preserves the existing R K Puram extraction.
"""

import os
import json
import time
import calendar
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo

import pandas as pd
import requests
from dotenv import load_dotenv


# --------------------------------------------------
# CONFIGURATION
# --------------------------------------------------

ROOT = Path(__file__).resolve().parents[2]

REGISTRY_FILE = (
    ROOT / "data/processed/openaq/delhi_sensor_registry.csv"
)

OUTPUT_DIR = ROOT / "data/raw/openaq/historical"

SUMMARY_DIR = ROOT / "data/processed/openaq/extraction"

BASE_URL = "https://api.openaq.org/v3"

START_YEAR = 2025
START_MONTH = 11

END_YEAR = 2026
END_MONTH = 10

TIMEZONE = ZoneInfo("Asia/Kolkata")

PAGE_LIMIT = 1000
MAX_RETRIES = 5
REQUEST_DELAY = 0.25

# This sensor already has all 12 months extracted.
EXISTING_COMPLETED_SENSORS = {"12234787"}


# --------------------------------------------------
# INITIALIZATION
# --------------------------------------------------

load_dotenv(ROOT / ".env")

API_KEY = os.getenv("OPENAQ_API_KEY")

if not API_KEY:
    raise RuntimeError(
        "OPENAQ_API_KEY not found. Check your .env file."
    )

HEADERS = {
    "X-API-Key": API_KEY,
    "Accept": "application/json"
}

SESSION = requests.Session()
SESSION.headers.update(HEADERS)


# --------------------------------------------------
# DATE UTILITIES
# --------------------------------------------------

def get_months():
    months = []

    year = START_YEAR
    month = START_MONTH

    while (year, month) <= (END_YEAR, END_MONTH):
        months.append((year, month))

        if month == 12:
            year += 1
            month = 1
        else:
            month += 1

    return months


def get_utc_boundaries(year, month):
    """
    Convert Indian local month boundaries to UTC.

    Example:
    2025-11-01 00:00 IST
    becomes
    2025-10-31 18:30 UTC
    """

    local_start = datetime(
        year, month, 1, 0, 0, 0, tzinfo=TIMEZONE
    )

    if month == 12:
        local_end = datetime(
            year + 1, 1, 1, 0, 0, 0, tzinfo=TIMEZONE
        )
    else:
        local_end = datetime(
            year, month + 1, 1, 0, 0, 0, tzinfo=TIMEZONE
        )

    utc_start = local_start.astimezone(
        ZoneInfo("UTC")
    )

    utc_end = local_end.astimezone(
        ZoneInfo("UTC")
    )

    return (
        utc_start.isoformat().replace("+00:00", "Z"),
        utc_end.isoformat().replace("+00:00", "Z")
    )


# --------------------------------------------------
# API REQUEST
# --------------------------------------------------

def fetch_page(sensor_id, year, month, page):

    datetime_from, datetime_to = get_utc_boundaries(
        year, month
    )

    url = f"{BASE_URL}/sensors/{sensor_id}/hours"

    params = {
        "datetime_from": datetime_from,
        "datetime_to": datetime_to,
        "limit": PAGE_LIMIT,
        "page": page
    }

    for attempt in range(1, MAX_RETRIES + 1):

        try:
            response = SESSION.get(
                url,
                params=params,
                timeout=60
            )

            if response.status_code == 429:
                wait = min(2 ** attempt, 60)
                print(f"Rate limited. Waiting {wait}s...")
                time.sleep(wait)
                continue

            response.raise_for_status()

            data = response.json()

            if "results" not in data:
                raise ValueError(
                    "API response does not contain results."
                )

            return data

        except (
            requests.RequestException,
            ValueError
        ) as error:

            print(
                f"Request failed: sensor={sensor_id}, "
                f"month={year}-{month:02d}, "
                f"page={page}, attempt={attempt}: {error}"
            )

            if attempt == MAX_RETRIES:
                raise

            time.sleep(min(2 ** attempt, 30))

    raise RuntimeError("Maximum retries exceeded.")


# --------------------------------------------------
# MONTH EXTRACTION
# --------------------------------------------------

def extract_month(sensor_id, station, year, month):

    month_name = f"{year}-{month:02d}"

    month_dir = (
        OUTPUT_DIR
        / f"sensor_{sensor_id}"
        / month_name
    )

    month_dir.mkdir(parents=True, exist_ok=True)

    manifest_path = month_dir / "month_manifest.json"

    # Resume only if the month has a completed manifest.
    if manifest_path.exists():

        try:
            previous = json.loads(
                manifest_path.read_text(encoding="utf-8")
            )

            if previous.get("status") == "completed":
                print(
                    f"SKIPPING {station} | {month_name} "
                    "(already completed)"
                )

                return {
                    "sensor_id": sensor_id,
                    "station": station,
                    "month": month_name,
                    "status": "SKIPPED",
                    "records": previous.get("total_records", 0),
                    "pages": previous.get("total_pages", 0)
                }

        except (json.JSONDecodeError, OSError):
            print("Invalid old manifest. Re-extracting month.")

    print(f"\nExtracting {station} | {month_name}")

    page = 1
    total_records = 0
    total_pages = 0

    try:

        while True:

            data = fetch_page(
                sensor_id,
                year,
                month,
                page
            )

            results = data["results"]

            # Save the complete original API response.
            page_file = month_dir / f"page_{page}.json"
            temp_file = month_dir / f"page_{page}.tmp"

            temp_file.write_text(
                json.dumps(data, ensure_ascii=False, indent=2),
                encoding="utf-8"
            )

            temp_file.replace(page_file)

            count = len(results)

            total_records += count
            total_pages += 1

            print(
                f"  Page {page}: {count} records "
                f"| Total: {total_records}"
            )

            if count < PAGE_LIMIT:
                break

            page += 1
            time.sleep(REQUEST_DELAY)

        manifest = {
            "sensor_id": sensor_id,
            "station": station,
            "month": month_name,
            "status": "completed",
            "total_records": total_records,
            "total_pages": total_pages,
            "extracted_at_utc": datetime.now(
                ZoneInfo("UTC")
            ).isoformat()
        }

        manifest_path.write_text(
            json.dumps(manifest, indent=2),
            encoding="utf-8"
        )

        print(
            f"COMPLETED {station} | {month_name} "
            f"| {total_records} records"
        )

        return {
            "sensor_id": sensor_id,
            "station": station,
            "month": month_name,
            "status": "COMPLETED",
            "records": total_records,
            "pages": total_pages
        }

    except Exception as error:

        failure_manifest = {
            "sensor_id": sensor_id,
            "station": station,
            "month": month_name,
            "status": "failed",
            "error": str(error),
            "records_downloaded": total_records,
            "pages_downloaded": total_pages
        }

        manifest_path.write_text(
            json.dumps(failure_manifest, indent=2),
            encoding="utf-8"
        )

        print(
            f"FAILED {station} | {month_name}: {error}"
        )

        return {
            "sensor_id": sensor_id,
            "station": station,
            "month": month_name,
            "status": "FAILED",
            "records": total_records,
            "pages": total_pages
        }


# --------------------------------------------------
# MAIN
# --------------------------------------------------

def main():

    if not REGISTRY_FILE.exists():
        raise FileNotFoundError(REGISTRY_FILE)

    registry = pd.read_csv(REGISTRY_FILE)

    required = {
        "sensor_id",
        "eligible_for_extraction"
    }

    missing = required - set(registry.columns)

    if missing:
        raise ValueError(
            f"Registry missing columns: {sorted(missing)}"
        )

    eligible = registry[
        registry["eligible_for_extraction"]
        .astype(str)
        .str.lower()
        .isin(["true", "1", "yes"])
    ].copy()

    eligible["sensor_id"] = (
        eligible["sensor_id"]
        .astype(str)
        .str.replace(r"\.0$", "", regex=True)
        .str.strip()
    )

    if eligible["sensor_id"].duplicated().any():
        raise ValueError("Duplicate sensor IDs in registry.")

    print("\n========== DELHI EXTRACTION ==========")
    print(f"Eligible sensors: {len(eligible)}")
    print(f"Months per sensor: {len(get_months())}")
    print(
        f"Existing completed sensors: "
        f"{len(EXISTING_COMPLETED_SENSORS)}"
    )

    print(
        f"Planned sensor-months: "
        f"{len(eligible) * len(get_months())}"
    )

    SUMMARY_DIR.mkdir(parents=True, exist_ok=True)

    results = []

    for index, row in enumerate(
        eligible.to_dict("records"), start=1
    ):

        sensor_id = row["sensor_id"]

        station = str(
            row.get("station", row.get("location_name", sensor_id))
        )

        print("\n" + "=" * 65)
        print(
            f"SENSOR {index}/{len(eligible)}: "
            f"{station} ({sensor_id})"
        )
        print("=" * 65)

        # R K Puram was previously extracted completely.
        if sensor_id in EXISTING_COMPLETED_SENSORS:

            print(
                "Preserving existing R K Puram extraction. "
                "Not downloading it again."
            )

            continue

        for year, month in get_months():

            result = extract_month(
                sensor_id,
                station,
                year,
                month
            )

            results.append(result)

            # Save progress after every month.
            pd.DataFrame(results).to_csv(
                SUMMARY_DIR / "delhi_extraction_progress.csv",
                index=False
            )

    # Final report.
    if results:

        report = pd.DataFrame(results)

        report.to_csv(
            SUMMARY_DIR / "delhi_extraction_summary.csv",
            index=False
        )

        print("\n========== FINAL EXTRACTION REPORT ==========")

        print(
            report["status"].value_counts().to_string()
        )

        print(
            f"\nRecords downloaded: "
            f"{report['records'].sum():,}"
        )

        print(
            f"Total completed months: "
            f"{(report['status'] == 'COMPLETED').sum()}"
        )

        print(
            f"Failed months: "
            f"{(report['status'] == 'FAILED').sum()}"
        )

        print(
            "\nSummary saved:",
            SUMMARY_DIR / "delhi_extraction_summary.csv"
        )

    else:
        print("No new extraction tasks were required.")


if __name__ == "__main__":
    main()
