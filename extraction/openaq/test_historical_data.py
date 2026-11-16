
import os
import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("OPENAQ_API_KEY")

if not API_KEY:
    raise ValueError("OPENAQ_API_KEY not found in .env")

SENSOR_ID = 12234787

URL = f"https://api.openaq.org/v3/sensors/{SENSOR_ID}/hours"

headers = {
    "X-API-Key": API_KEY
}

params = {
    "datetime_from": "2025-10-31T18:30:00Z",
    "datetime_to": "2025-11-01T18:30:00Z",
    "limit": 1000,
    "page": 1
}

print("Testing historical PM2.5 hourly data...")
response = requests.get(
    URL,
    headers=headers,
    params=params,
    timeout=30
)

print("HTTP Status:", response.status_code)
response.raise_for_status()

data = response.json()

print("Response keys:", list(data.keys()))

results = data.get("results", [])

print("Records received:", len(results))

if results:
    print("\nFirst record:")
    print(results[0])

    print("\nLast record:")
    print(results[-1])
else:
    print("No hourly records returned for this date.")
