
import os
import requests

from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("OPENAQ_API_KEY")

BASE_URL = "https://api.openaq.org/v3/locations"

def test_connection():

    if not API_KEY:
        print("ERROR: OpenAQ API key not found.")
        return

    headers = {
        "X-API-Key": API_KEY
    }

    params = {
        "limit": 1
    }

    try:
        response = requests.get(
            BASE_URL,
            headers=headers,
            params=params,
            timeout=30
        )

        print("HTTP Status:", response.status_code)

        response.raise_for_status()

        data = response.json()

        print("API Connection Successful!")
        print("Response keys:", list(data.keys()))

        results = data.get("results", [])

        if results:
            print("Sample location:", results[0].get("name"))
        else:
            print("API responded, but no location was returned.")

    except requests.exceptions.HTTPError as error:
        print("HTTP Error:", error)
        print("Response:", response.text[:500])

    except requests.exceptions.RequestException as error:
        print("Connection Error:", error)


if __name__ == "__main__":
    test_connection()
