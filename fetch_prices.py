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
# Budget: MAX_ATTEMPTS=3 total tries, with REQUEST_TIMEOUT (see below) per try and
# BACKOFF_SECONDS between tries. Worst case per call (every attempt hangs to
# the full timeout): 3*60 + sum(BACKOFF_SECONDS) = 180 + 9 = 189s. Typical case
# (a fast 502 response, not a hang): a few seconds per attempt + 9s backoff.
# See docs/RELIABILITY.md for the full worst-case analysis across a
# multi-target run.
# ---------------------------------------------------------------------------
MAX_ATTEMPTS = 3
BACKOFF_SECONDS = [3, 6]  # delay before attempt 2, delay before attempt 3
# 60s (was 30s): matches the website's own fetch-daily timeout. On 26-27 Sep
# 2026 data.gov.in answered light requests instantly but took >40s on real
# commodity queries, so every 30s attempt timed out. Worst case per page is
# now 3*60 + 9 = 189s; the workflow timeout (35 min) still covers paging.
REQUEST_TIMEOUT = 60
# 429 included: a public, rate-limited government API polled up to ~30
# times a day in a concentrated morning window (5 YouTube targets + 25
# Telegram commodities, some run concurrently) is at least as likely to
# rate-limit as to 5xx -- both are worth a backoff-and-retry.
RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}


class DataFetchError(Exception):
    """Raised when data.gov.in cannot be reached after exhausting retries.
    This is a genuine upstream failure (as opposed to a legitimate empty
    result set) and callers must treat it as a pipeline failure, not a
    quiet skip."""


def _get_with_retry(params):
    """GETs BASE_URL with `params`, retrying transient failures up to
    MAX_ATTEMPTS times with backoff. Returns the parsed JSON body of the
    successful response. Raises DataFetchError (chained to the last real
    exception) once all attempts are exhausted or a non-retryable error is
    hit.

    JSON parsing happens INSIDE this retry loop, not after it returns: a
    response that passes raise_for_status() (HTTP 200) but has a malformed
    or non-JSON body -- a real failure mode for this API, e.g. an HTML
    maintenance page served with a 200 -- must go through the same
    retry/classification path as a 5xx, not bypass it entirely."""
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
            return resp.json()
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
            last_exc = e
            is_retryable = True
        except requests.exceptions.HTTPError as e:
            last_exc = e
            status = e.response.status_code if e.response is not None else None
            is_retryable = status in RETRYABLE_STATUS_CODES
        except ValueError as e:
            # resp.json() failed to parse (e.g. requests.exceptions.
            # JSONDecodeError, a ValueError subclass) -- a malformed body
            # on an otherwise-200 response. At least as likely to be a
            # transient upstream glitch as a 5xx, so retry it the same way.
            last_exc = e
            is_retryable = True
        except requests.exceptions.RequestException as e:
            # Catch-all for other transient network conditions not already
            # covered above (e.g. ChunkedEncodingError) -- retry with the
            # same bounded budget rather than letting an unclassified
            # exception bypass this function's retry/error-classification
            # boundary entirely.
            last_exc = e
            is_retryable = True

        if not is_retryable or attempt == MAX_ATTEMPTS:
            break
        delay = BACKOFF_SECONDS[attempt - 1]
        print(f"[fetch_prices] Attempt {attempt}/{MAX_ATTEMPTS} failed ({last_exc}); retrying in {delay}s...")
        time.sleep(delay)

    raise DataFetchError(
        f"data.gov.in request failed after {MAX_ATTEMPTS} attempt(s): {last_exc}"
    ) from last_exc


PAGE_SIZE = 500
MAX_PAGES = 12  # hard stop: 6,000 rows, far above any single commodity's daily count


def fetch_all_states(commodity, limit=PAGE_SIZE):
    """Fetches ALL records for `commodity` across ALL states, paging through
    the API with `offset` (data.gov.in has no reliable server-side state
    filter for this resource, so state filtering always happens locally --
    see filter_by_state()).

    Why paging (Batch 1, 26 Sep 2026): this used to be ONE call with
    limit=500. Onion/potato/tomato each report from far more than 500
    markets on a busy day, so whichever states the API happened to list
    after row 500 were silently cut off -- a state could look like "no data
    today" when it actually had dozens of markets reporting (likely why
    Karnataka tomato and Punjab potato skipped most days).

    Paging stops when a page comes back short (fewer than `limit` rows),
    empty, or once the API's own `total` is reached. Each page goes through
    the same retry policy as before; a page that still fails after retries
    raises DataFetchError for the whole call (a partial all-India list would
    silently drop states again, which is exactly the bug being fixed).

    Exposed separately from fetch_prices() so callers that need the same
    commodity's data for multiple states (e.g. telegram_broadcast.py) can
    fetch it ONCE and filter locally.
    Raises DataFetchError if a request fails after retries."""
    all_records = []
    offset = 0
    for _ in range(MAX_PAGES):
        params = {
            "api-key": API_KEY,
            "format": "json",
            "limit": limit,
            "offset": offset,
            "filters[commodity]": commodity,
        }
        data = _get_with_retry(params)
        page = data.get("records", []) or []
        all_records.extend(page)
        total = _to_int(data.get("total"))
        offset += len(page)
        if len(page) < limit or not page:
            break
        if total is not None and offset >= total:
            break
    return all_records


def _to_int(v):
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


def _price(v):
    """Parses an API price field ("2311.09", "3000", 3000) to a whole-rupee
    int, or None if it is missing/unparseable/non-positive."""
    try:
        f = float(str(v).replace(",", "").strip())
    except (TypeError, ValueError):
        return None
    if f != f or f <= 0:  # NaN or non-positive
        return None
    return int(f + 0.5)  # half-up, not Python's banker's rounding


def clean_records(records):
    """Makes one state's rows safe and meaningful to show on screen
    (Batch 1, 26 Sep 2026 -- fixes real on-screen errors seen live):

    1. Prices become whole rupees (the 25 Sep card showed "Rs.2311.09").
       Rows with a missing or non-positive modal price are dropped.
    2. ONE row per mandi. The API returns one row per variety/grade, so the
       same mandi could appear twice with very different prices (25 Sep UP
       onion: Tilhar APMC at 5,983 AND 3,000). For a mandi with several
       rows we keep its median-priced row -- a real reported row, not an
       invented average.
    3. Sorted by modal price, highest first. Before this, records came in
       raw API order, so "the" mandi named in the title, hero price label
       and narration was simply whichever row the API listed first. Now
       records[0] is always the best-paying mandi and records[-1] the
       lowest, so every downstream "top" label is true by construction.
    """
    by_market = {}
    for r in records:
        modal = _price(r.get("modal_price"))
        if modal is None:
            continue
        row = dict(r)
        row["modal_price"] = modal
        lo = _price(r.get("min_price"))
        hi = _price(r.get("max_price"))
        row["min_price"] = lo if lo is not None else modal
        row["max_price"] = hi if hi is not None else modal
        key = str(r.get("market", "")).strip().lower()
        by_market.setdefault(key, []).append(row)

    cleaned = []
    for rows in by_market.values():
        rows.sort(key=lambda x: x["modal_price"])
        cleaned.append(rows[(len(rows) - 1) // 2])
    cleaned.sort(key=lambda x: x["modal_price"], reverse=True)
    return cleaned


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
    state_records = clean_records(filter_by_state(all_records, state))
    return state_records[:limit]


if __name__ == "__main__":
    rows = fetch_prices()
    print(f"Fetched {len(rows)} records")
    for r in rows[:3]:
        print(r)
