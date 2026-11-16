
import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]

LOCATION_FILE = ROOT / "data/raw/openaq/delhi_locations.json"
SHORTLIST_FILE = ROOT / "data/processed/openaq/delhi_pm25_shortlist.csv"

OUTPUT_FILE = (
    ROOT / "data/processed/openaq/delhi_pm25_shortlist_with_coordinates.csv"
)


def load_records(path):
    with open(path, "r", encoding="utf-8") as file:
        data = json.load(file)

    if isinstance(data, list):
        return data

    if isinstance(data, dict):
        if isinstance(data.get("results"), list):
            return data["results"]

        if isinstance(data.get("locations"), list):
            return data["locations"]

    raise ValueError(f"Unexpected JSON structure in {path}")


def main():

    locations = load_records(LOCATION_FILE)

    location_map = {
        item.get("id"): item
        for item in locations
        if item.get("id") is not None
    }

    enriched = []

    with open(SHORTLIST_FILE, "r", encoding="utf-8") as file:
        sensors = list(csv.DictReader(file))

    for sensor in sensors:

        location_id = int(sensor["location_id"])
        location = location_map.get(location_id, {})

        coordinates = location.get("coordinates") or {}

        latitude = coordinates.get("latitude")
        longitude = coordinates.get("longitude")

        enriched.append({
            **sensor,
            "latitude": latitude,
            "longitude": longitude,
            "locality": location.get("locality"),
            "city": location.get("city"),
            "country": (
                location.get("country", {}).get("name")
                if isinstance(location.get("country"), dict)
                else location.get("country")
            ),
            "coordinates_available": (
                latitude is not None and longitude is not None
            )
        })

    fields = list(enriched[0].keys()) if enriched else []

    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        writer.writerows(enriched)

    print("\n========== LOCATION VERIFICATION ==========")
    print("Shortlisted sensors:", len(enriched))

    missing = 0

    for item in enriched:

        if not item["coordinates_available"]:
            missing += 1

        print(
            f"{item['location_name']} | "
            f"ID: {item['location_id']} | "
            f"Lat: {item['latitude']} | "
            f"Lon: {item['longitude']} | "
            f"Locality: {item['locality']}"
        )

    print("\nLocations without coordinates:", missing)
    print("Saved:", OUTPUT_FILE)
    print("===========================================")


if __name__ == "__main__":
    main()
