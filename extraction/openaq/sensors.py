
import os
import json
import time
import requests

from dotenv import load_dotenv
from pathlib import Path

load_dotenv()

API_KEY = os.getenv("OPENAQ_API_KEY")

BASE_URL = "https://api.openaq.org/v3/locations"

PROJECT_ROOT = Path(__file__).resolve().parents[2]

INPUT_FILE = (
    PROJECT_ROOT / "data" / "raw" /
    "openaq" / "delhi_locations.json"
)

OUTPUT_DIR = PROJECT_ROOT / "data" / "raw" / "openaq"

SENSOR_FILE = OUTPUT_DIR / "delhi_sensors.json"
SUMMARY_FILE = OUTPUT_DIR / "delhi_sensor_summary.csv"


def fetch_sensors(location_id):

    url = f"{BASE_URL}/{location_id}/sensors"

    headers = {
        "X-API-Key": API_KEY
    }

    all_sensors = []
    page = 1
    limit = 1000

    while True:

        params = {
            "limit": limit,
            "page": page
        }

        response = requests.get(
            url,
            headers=headers,
            params=params,
            timeout=30
        )

        response.raise_for_status()

        payload = response.json()
        results = payload.get("results", [])

        if not results:
            break

        all_sensors.extend(results)

        if len(results) < limit:
            break

        page += 1

    return all_sensors


def main():

    if not API_KEY:
        raise ValueError("OpenAQ API key not found.")

    with open(INPUT_FILE, "r", encoding="utf-8") as file:
        locations = json.load(file)

    all_sensor_records = []
    summary_records = []

    print(f"Starting sensor discovery for {len(locations)} locations...\n")

    for index, location in enumerate(locations, start=1):

        location_id = location.get("id")
        location_name = location.get("name")

        print(
            f"[{index}/{len(locations)}] "
            f"Checking: {location_name} ({location_id})"
        )

        try:

            sensors = fetch_sensors(location_id)

            print(f"    Sensors found: {len(sensors)}")

            for sensor in sensors:

                parameter = sensor.get("parameter") or {}

                record = {
                    "location_id": location_id,
                    "location_name": location_name,
                    "sensor_id": sensor.get("id"),
                    "parameter_name": parameter.get("name"),
                    "parameter_display_name": parameter.get("displayName"),
                    "parameter_units": parameter.get("units"),
                    "sensor_name": sensor.get("name"),
                    "sensor_datetime_first": sensor.get("datetimeFirst"),
                    "sensor_datetime_last": sensor.get("datetimeLast"),
                    "sensor": sensor
                }

                all_sensor_records.append(record)

                summary_records.append({
                    key: value
                    for key, value in record.items()
                    if key != "sensor"
                })

            time.sleep(0.2)

        except requests.exceptions.HTTPError as error:

            status = error.response.status_code

            print(f"    HTTP Error: {status}")

            if status == 429:
                print("    Rate limit reached. Stopping safely.")
                break

        except requests.exceptions.RequestException as error:

            print(f"    Request failed: {error}")

    with open(SENSOR_FILE, "w", encoding="utf-8") as file:

        json.dump(
            all_sensor_records,
            file,
            indent=4,
            ensure_ascii=False
        )

    import csv

    if summary_records:

        with open(
            SUMMARY_FILE,
            "w",
            newline="",
            encoding="utf-8"
        ) as file:

            writer = csv.DictWriter(
                file,
                fieldnames=summary_records[0].keys()
            )

            writer.writeheader()
            writer.writerows(summary_records)

    print("\n========== SENSOR DISCOVERY SUMMARY ==========")
    print("Locations processed:", len(locations))
    print("Total sensors discovered:", len(all_sensor_records))
    print("JSON saved:", SENSOR_FILE)
    print("CSV saved:", SUMMARY_FILE)


if __name__ == "__main__":
    main()
