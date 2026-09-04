import os
import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.environ["DATA_GOV_API_KEY"]
RESOURCE_ID = "9ef84268-d588-465a-a308-a864a43d0070"
BASE_URL = f"https://api.data.gov.in/resource/{RESOURCE_ID}"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}


def fetch_prices(state="Uttar Pradesh", commodity="Onion", limit=15):
    """Fetch today's mandi prices for a commodity, then filter by state locally
    (data.gov.in's own State filter is unreliable for this resource)."""
    params = {
        "api-key": API_KEY,
        "format": "json",
        "limit": 500,
        "filters[commodity]": commodity,
    }
    resp = requests.get(BASE_URL, params=params, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    all_records = resp.json().get("records", [])

    state_records = [
        r for r in all_records
        if r.get("state", "").strip().lower() == state.strip().lower()
    ]

  

    return state_records[:limit]


if __name__ == "__main__":
    rows = fetch_prices()
    print(f"Fetched {len(rows)} records")
    for r in rows[:3]:
        print(r)