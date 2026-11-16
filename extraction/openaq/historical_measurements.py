
import calendar
import json
import os
import time

from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import requests
from dotenv import load_dotenv


# --------------------------------------------------
# CONFIGURATION
# --------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[2]

load_dotenv(PROJECT_ROOT / ".env")

API_KEY = os.getenv("OPENAQ_API_KEY")

if not API_KEY:
    raise ValueError("OPENAQ_API_KEY not found in project .env file.")

SENSOR_ID = 12234787
LOCATION_NAME = "R K Puram, Delhi - DPCC"
PARAMETER = "pm25"

START_YEAR = 2025
START_MONTH = 11

END_YEAR = 2026
END_MONTH = 10

TIMEZONE = ZoneInfo("Asia/Kolkata")

LIMIT = 1000
MAX_RETRIES = 5

BASE_URL = f"https://api.openaq.org/v3/sensors/{SENSOR_ID}/hours"

OUTPUT_DIR = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "openaq"
    / "historical"
    / f"sensor_{SENSOR_ID}"
)

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# --------------------------------------------------
# HTTP SESSION
# --------------------------------------------------

session = requests.Session()

session.headers.update({
    "X-API-Key": API_KEY,
    "Accept": "application/json"
})


# --------------------------------------------------
# DATE UTILITIES
# --------------------------------------------------

def get_month_range(year, month):
    """Return month boundaries converted from IST to UTC."""

    start_local = datetime(
        year, month, 1, 0, 0, 0,
        tzinfo=TIMEZONE
    )

    if month == 12:
        next_month = datetime(
            year + 1, 1, 1, 0, 0, 0,
            tzinfo=TIMEZONE
        )
    else:
        next_month = datetime(
            year, month + 1, 1, 0, 0, 0,
            tzinfo=TIMEZONE
        )

    start_utc = start_local.astimezone(timezone.utc)
    end_utc = next_month.astimezone(timezone.utc)

    return (
        start_utc.isoformat().replace("+00:00", "Z"),
        end_utc.isoformat().replace("+00:00", "Z")
    )


def get_months():
    """Generate all requested months, inclusive."""

    year = START_YEAR
    month = START_MONTH

    while (year, month) <= (END_YEAR, END_MONTH):
        yield year, month

        if month == 12:
            year += 1
            month = 1
        else:
            month += 1


# --------------------------------------------------
# API REQUEST WITH RETRIES
# --------------------------------------------------

def fetch_page(params):
    for attempt in range(1, MAX_RETRIES + 1):

        try:
            response = session.get(
                BASE_URL,
                params=params,
                timeout=60
            )

            if response.status_code == 429:
                retry_after = response.headers.get("Retry-After")

                try:
                    wait_time = int(retry_after)
                except (TypeError, ValueError):
                    wait_time = min(2 ** attempt, 60)

                print(f"Rate limited. Waiting {wait_time}s...")
                time.sleep(wait_time)
                continue

            if response.status_code >= 500:
                raise requests.HTTPError(
                    f"Server error: {response.status_code}"
                )

            response.raise_for_status()

            return response.json()

        except (requests.RequestException, ValueError) as error:

            print(
                f"Request attempt {attempt}/{MAX_RETRIES} failed: "
                f"{error}"
            )

            if attempt == MAX_RETRIES:
                raise

            time.sleep(min(2 ** attempt, 30))

    raise RuntimeError("Maximum retries exceeded.")


# --------------------------------------------------
# MONTH EXTRACTION
# --------------------------------------------------

def extract_month(year, month):

    month_name = f"{year}-{month:02d}"

    month_dir = OUTPUT_DIR / month_name
    month_dir.mkdir(parents=True, exist_ok=True)

    manifest_path = month_dir / "manifest.json"

    # Resume completed months
    if manifest_path.exists():

        with open(manifest_path, "r", encoding="utf-8") as file:
            manifest = json.load(file)

        if manifest.get("status") == "completed":
            print(f"[SKIP] {month_name} already completed.")
            return manifest.get("total_records", 0)

    datetime_from, datetime_to = get_month_range(year, month)

    print(f"\nExtracting {month_name}")
    print(f"UTC range: {datetime_from} -> {datetime_to}")

    page = 1
    total_records = 0
    total_pages = 0

    while True:

        params = {
            "datetime_from": datetime_from,
            "datetime_to": datetime_to,
            "limit": LIMIT,
            "page": page
        }

        data = fetch_page(params)

        results = data.get("results", [])

        page_path = month_dir / f"page_{page}.json"
        temp_path = month_dir / f"page_{page}.tmp"

        # Preserve the original API response for this page
        with open(temp_path, "w", encoding="utf-8") as file:
            json.dump(data, file, ensure_ascii=False, indent=2)

        temp_path.replace(page_path)

        record_count = len(results)

        total_records += record_count
        total_pages += 1

        print(
            f"  Page {page}: {record_count} records "
            f"(total: {total_records})"
        )

        if record_count < LIMIT:
            break

        page += 1
        time.sleep(0.25)

    manifest = {
        "status": "completed",
        "sensor_id": SENSOR_ID,
        "location_name": LOCATION_NAME,
        "parameter": PARAMETER,
        "year": year,
        "month": month,
        "timezone": "Asia/Kolkata",
        "datetime_from_utc": datetime_from,
        "datetime_to_utc": datetime_to,
        "total_records": total_records,
        "total_pages": total_pages,
        "extracted_at_utc": datetime.now(
            timezone.utc
        ).isoformat()
    }

    temp_manifest = month_dir / "manifest.tmp"

    with open(temp_manifest, "w", encoding="utf-8") as file:
        json.dump(manifest, file, ensure_ascii=False, indent=2)

    temp_manifest.replace(manifest_path)

    print(f"[SUCCESS] {month_name}: {total_records} records")

    return total_records


# --------------------------------------------------
# MAIN
# --------------------------------------------------

def main():

    print("=" * 60)
    print("OPENAQ HISTORICAL DATA EXTRACTION")
    print("=" * 60)

    print(f"Sensor ID: {SENSOR_ID}")
    print(f"Location: {LOCATION_NAME}")
    print(f"Parameter: {PARAMETER}")
    print("Period: November 2025 - October 2026")
    print(f"Output: {OUTPUT_DIR}")

    successful_months = 0
    failed_months = []
    grand_total = 0

    months = list(get_months())

    for index, (year, month) in enumerate(months, start=1):

        print(f"\nMONTH {index}/{len(months)}")

        try:
            count = extract_month(year, month)

            grand_total += count
            successful_months += 1

        except Exception as error:

            month_name = f"{year}-{month:02d}"

            print(f"[FAILED] {month_name}: {error}")

            failed_months.append(month_name)

    print("\n" + "=" * 60)
    print("EXTRACTION SUMMARY")
    print("=" * 60)

    print(f"Months processed: {successful_months}/{len(months)}")
    print(f"Records this run: {grand_total}")
    print(f"Failed months: {failed_months}")

    print(f"\nOutput directory: {OUTPUT_DIR}")

    if failed_months:
        print("\nRerun this script after checking the failed months.")
    else:
        print("\nAll requested months completed!")


if __name__ == "__main__":
    main()
