import os
import time
import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.environ["DATA_GOV_API_KEY"]
RESOURCE_ID = "9ef84268-d588-465a-a308-a864a43d0070"
BASE_URL = f"https://api.data.gov.in/resource/{RESOURCE_ID}"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

# ---------------------------------------------------------------------------
# Retry policy for data.gov.in, which has confirmed intermittent 5xx errors
# in production (502 Bad Gateway observed on real scheduled runs). Only
# transient failures are retried -- a bad api-key or a malformed request
# (4xx, not in RETRYABLE_STATUS_CODES) fails immediately, since retrying
# those can never succeed and would just waste the workflow's time budget.
#
# Budget: MAX_ATTEMPTS=3 total tries, with REQUEST_TIMEOUT=30s per try and
# BACKOFF_SECONDS between tries. Worst case per call (every attempt hangs to
# the full timeout): 3*30 + sum(BACKOFF_SECONDS) = 90 + 9 = 99s. Typical case
# (a fast 502 response, not a hang): a few seconds per attempt + 9s backoff.
# See docs/RELIABILITY.md for the full worst-case analysis across a
# multi-target run.
# ---------------------------------------------------------------------------
MAX_ATTEMPTS = 3
BACKOFF_SECONDS = [3, 6]  # delay before attempt 2, delay before attempt 3
REQUEST_TIMEOUT = 30
RETRYABLE_STATUS_CODES = {500, 502, 503, 504}


class DataFetchError(Exception):
    """Raised when data.gov.in cannot be reached after exhausting retries.
    This is a genuine upstream failure (as opposed to a legitimate empty
    result set) and callers must treat it as a pipeline failure, not a
    quiet skip."""


def _get_with_retry(params):
    """GETs BASE_URL with `params`, retrying transient failures up to
    MAX_ATTEMPTS times with backoff. Returns the successful Response.
    Raises DataFetchError (chained to the last real exception) once all
    attempts are exhausted or a non-retryable error is hit."""
    last_exc = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            resp = requests.get(BASE_URL, params=params, headers=HEADERS, timeout=REQUEST_TIMEOUT)
            if resp.status_code in RETRYABLE_STATUS_CODES:
                raise requests.exceptions.HTTPError(
                    f"{resp.status_code} Server Error (retryable) for url: {resp.url}",
                    response=resp,
                )
            resp.raise_for_status()  # non-retryable 4xx/5xx (e.g. bad api-key) raises straight through
            return resp
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
            last_exc = e
            is_retryable = True
        except requests.exceptions.HTTPError as e:
            last_exc = e
            status = e.response.status_code if e.response is not None else None
            is_retryable = status in RETRYABLE_STATUS_CODES

        if not is_retryable or attempt == MAX_ATTEMPTS:
            break
        delay = BACKOFF_SECONDS[attempt - 1]
        print(f"[fetch_prices] Attempt {attempt}/{MAX_ATTEMPTS} failed ({last_exc}); retrying in {delay}s...")
        time.sleep(delay)

    raise DataFetchError(
        f"data.gov.in request failed after {MAX_ATTEMPTS} attempt(s): {last_exc}"
    ) from last_exc


def fetch_all_states(commodity, limit=500):
    """Fetches up to `limit` records for `commodity` across ALL states in one
    API call (data.gov.in has no reliable server-side state filter for this
    resource, so state filtering always happens locally -- see
    filter_by_state()). Exposed separately from fetch_prices() so callers
    that need the same commodity's data for multiple states (e.g.
    telegram_broadcast.py, which previously called fetch_prices() once per
    state per commodity) can fetch it ONCE and filter locally, instead of
    making one redundant upstream call per state.
    Raises DataFetchError if the request fails after retries."""
    params = {
        "api-key": API_KEY,
        "format": "json",
        "limit": limit,
        "filters[commodity]": commodity,
    }
    resp = _get_with_retry(params)
    return resp.json().get("records", [])


def filter_by_state(records, state):
    """Pure local filter: narrows an already-fetched all-states record list
    down to one state. Does not call the network. Split out from
    fetch_prices() so callers can reuse one fetch_all_states() result across
    several states without re-fetching."""
    return [
        r for r in records
        if r.get("state", "").strip().lower() == state.strip().lower()
    ]


def fetch_prices(state="Uttar Pradesh", commodity="Onion", limit=15):
    """Fetch today's mandi prices for a commodity in one state. Internally:
    fetch_all_states() (one retried API call) + filter_by_state() (local).

    NOTE: a state with zero matching records for this commodity today is a
    legitimate, common outcome (not every state reports every commodity
    every day) and returns an empty list here -- this is intentionally
    different from a DataFetchError, which means the request itself could
    not be completed. Callers must keep treating an empty list as "nothing
    to publish today" and a DataFetchError as a real failure; conflating the
    two was the root cause of a historical data-integrity incident (see
    docs/RELIABILITY.md and data/history/uttar-pradesh-onion.json's fixed
    2026-09-04 entry) where an earlier version of this function silently
    fell back to unfiltered, wrong-state data instead of returning an empty
    list.
    """
    all_records = fetch_all_states(commodity)
    state_records = filter_by_state(all_records, state)
    return state_records[:limit]


if __name__ == "__main__":
    rows = fetch_prices()
    print(f"Fetched {len(rows)} records")
    for r in rows[:3]:
        print(r)
