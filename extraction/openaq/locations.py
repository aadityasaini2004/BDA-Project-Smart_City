
import os
import requests
import json

from dotenv import load_dotenv
from pathlib import Path

load_dotenv()

API_KEY = os.getenv("OPENAQ_API_KEY")

BASE_URL = "https://api.openaq.org/v3/locations"

PROJECT_ROOT = Path(__file__).resolve().parents[2]

OUTPUT_DIR = PROJECT_ROOT / "data" / "raw" / "openaq"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def get_delhi_locations():

    if not API_KEY:
        raise ValueError("OpenAQ API key not found.")

    headers = {
        "X-API-Key": API_KEY
    }

    bbox = "76.85,28.40,77.45,28.90"

    all_locations = []
    page = 1
    limit = 1000

    while True:

        params = {
            "bbox": bbox,
            "iso": "IN",
            "limit": limit,
            "page": page
        }

        response = requests.get(
            BASE_URL,
            headers=headers,
            params=params,
            timeout=30
        )

        response.raise_for_status()

        payload = response.json()

        results = payload.get("results", [])

        if not results:
            break

        all_locations.extend(results)

        print(
            f"Page {page}: "
            f"{len(results)} locations found"
        )

        if len(results) < limit:
            break

        page += 1

    return all_locations


def main():

    print("Discovering Delhi monitoring locations...")

    locations = get_delhi_locations()

    output_file = OUTPUT_DIR / "delhi_locations.json"

    with open(output_file, "w", encoding="utf-8") as file:

        json.dump(
            locations,
            file,
            indent=4,
            ensure_ascii=False
        )

    print("\nExtraction completed!")
    print("Total locations:", len(locations))
    print("Saved to:", output_file)

    for location in locations[:10]:

        print(
            location.get("id"),
            "|",
            location.get("name"),
            "|",
            location.get("locality")
        )


if __name__ == "__main__":
    main()
