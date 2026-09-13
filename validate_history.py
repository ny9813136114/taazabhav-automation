"""Read-only validator for data/history/*.json (the YouTube pipeline's
per-state/commodity price history files -- see price_history.py).

This does NOT modify any file. It only reports what it finds. Running it is
always safe: `python validate_history.py`.

Built specifically against the actual schema found in this repo:
  { "YYYY-MM-DD": { "<market name>": <modal_price or "N/A">, ... }, ... }
one file per (state, commodity) pair, filename "<state-slug>-<commodity>.json"
(see price_history._history_file()).

What this checks, and why each check is deterministic given the real schema:

1. Invalid schema -- a date value that isn't a dict, or a market->price
   entry whose price isn't a number and isn't the literal placeholder
   "N/A" that price_history.save_today_prices() itself writes when a
   record has no modal_price. Deterministic: the schema is fully known.

2. Empty/missing market name -- a market key that is "" or whitespace-only.
   Deterministic: price_history.save_today_prices() uses r.get("market", "")
   as the dict key, so a record with no market field produces exactly this.

3. Wrong-state contamination -- a date entry where every market name in it
   carries an unambiguous OTHER-state signature term (see
   OTHER_STATE_SIGNATURES below) and the file's own expected state is not
   that state. This is the exact bug class behind the confirmed 2026-09-04
   incident in uttar-pradesh-onion.json: a pre-fix version of
   fetch_prices() fell back to returning the first N unfiltered
   (all-states) records whenever zero records matched the target state,
   so a contaminated day is *wholesale* one other state's data, not a
   handful of stray rows. Requiring 100% of that day's markets to carry
   the same other-state signature (rather than flagging on a single
   coincidental substring match) keeps this check deterministic instead
   of a fuzzy heuristic.

4. Implausible price magnitude -- a numeric price far below the file's own
   observed typical range (see PRICE_OUTLIER_RATIO). This is reported as a
   FLAG only, never auto-corrected: a genuinely low price is possible (a
   real market glut), and the pipeline has no ground truth to correct
   against. Several real examples of this were found during the Phase 0/1A
   audit (e.g. Punjab records repeatedly in the paise-per-quintal range
   across independent files) and are surfaced here for human follow-up,
   not fixed.

5. Missing dates in the trailing window -- a gap in the expected daily
   sequence over the file's own min..max date range. Informational only
   (a legitimately failed/skipped run also produces a gap; see
   docs/RELIABILITY.md's discussion of run_pipeline()'s RESULT_SKIPPED_NO_DATA).

6. Duplicate records -- structurally not possible in this schema (each
   date is a unique JSON object key, and each market name within a date is
   also a unique key), so this always reports zero; included so the report
   explicitly states that rather than silently omitting the check.

State/commodity are inferred from the filename convention already used by
price_history._history_file(): "<state-with-dashes>-<commodity>.json".
"""
import json
import re
import sys
from datetime import date, timedelta
from pathlib import Path

HISTORY_DIR = Path("data/history")

# Terms that unambiguously identify ONE specific state's market-naming
# convention and would never legitimately appear in another state's data.
# "Uzhavar Sandhai" is Tamil Nadu's state-run farmers'-market scheme name --
# this is the exact term found contaminating uttar-pradesh-onion.json's
# 2026-09-04 entry.
OTHER_STATE_SIGNATURES = {
    "Tamil Nadu": ["uzhavar sandhai"],
}

# A price is flagged as an outlier if it is less than this fraction of the
# file's own median price across all its other dates. 0.05 (5%) is
# deliberately conservative -- real price swings happen -- and is meant to
# catch orders-of-magnitude anomalies (e.g. 18 vs a typical 3000-4500),
# not ordinary day-to-day volatility.
PRICE_OUTLIER_RATIO = 0.05


def _slug_to_state(slug):
    """Reverses price_history._history_file()'s
    f"{state.lower().replace(' ', '-')}-{commodity.lower()}" convention as
    far as it can be reversed: everything except the last dash-separated
    token is the state slug (this is ambiguous in general for multi-word
    commodities, but every commodity actually used by this pipeline today
    -- Onion, Potato, Tomato -- is a single word, so it is exact in
    practice)."""
    parts = slug.split("-")
    state_slug = "-".join(parts[:-1])
    commodity = parts[-1]
    return state_slug.replace("-", " ").title(), commodity.title()


def _is_number(value):
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return True
    if isinstance(value, str):
        try:
            float(value)
            return True
        except ValueError:
            return False
    return False


def _as_number(value):
    return float(value)


def validate_file(path):
    """Returns a dict report for one history file. Never raises on bad
    data -- a file that fails to parse at all is reported as its own
    finding rather than crashing the scan."""
    report = {
        "file": str(path),
        "state": None,
        "commodity": None,
        "dates_scanned": 0,
        "records_scanned": 0,
        "findings": [],
    }

    state_guess, commodity_guess = _slug_to_state(path.stem)
    report["state"] = state_guess
    report["commodity"] = commodity_guess

    try:
        raw = path.read_text(encoding="utf-8")
        history = json.loads(raw)
    except (OSError, json.JSONDecodeError) as e:
        report["findings"].append({"type": "unreadable_file", "detail": str(e)})
        return report

    if not isinstance(history, dict):
        report["findings"].append({"type": "invalid_schema", "detail": "top-level JSON is not an object"})
        return report

    all_prices = []
    dates_present = []

    for date_key, day_value in history.items():
        report["dates_scanned"] += 1

        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", date_key):
            report["findings"].append({"type": "invalid_date_key", "date": date_key})
            continue
        dates_present.append(date_key)

        if not isinstance(day_value, dict):
            report["findings"].append({"type": "invalid_schema", "date": date_key, "detail": "date value is not an object"})
            continue

        market_names_this_day = []
        for market_name, price in day_value.items():
            report["records_scanned"] += 1
            market_names_this_day.append(market_name)

            if not market_name or not market_name.strip():
                report["findings"].append({"type": "empty_market_name", "date": date_key})

            if price == "N/A":
                continue  # documented placeholder for "no modal_price in the source record" -- not an error

            if not _is_number(price):
                report["findings"].append({
                    "type": "invalid_price_value", "date": date_key,
                    "market": market_name, "value": price,
                })
                continue

            numeric_price = _as_number(price)
            all_prices.append(numeric_price)
            if numeric_price <= 0:
                report["findings"].append({
                    "type": "non_positive_price", "date": date_key,
                    "market": market_name, "value": numeric_price,
                })

        # --- Wrong-state contamination check (100%-of-day signal only) ---
        if market_names_this_day:
            for other_state, signatures in OTHER_STATE_SIGNATURES.items():
                if other_state.lower() == state_guess.lower():
                    continue
                lowered = [m.lower() for m in market_names_this_day]
                all_match = all(any(sig in name for sig in signatures) for name in lowered)
                if all_match:
                    report["findings"].append({
                        "type": "wrong_state_contamination",
                        "date": date_key,
                        "expected_state": state_guess,
                        "detected_state": other_state,
                        "market_count": len(market_names_this_day),
                        "sample_markets": market_names_this_day[:3],
                    })

    # --- Implausible price magnitude (relative to this file's own data) ---
    if len(all_prices) >= 5:
        sorted_prices = sorted(all_prices)
        median = sorted_prices[len(sorted_prices) // 2]
        threshold = median * PRICE_OUTLIER_RATIO
        if threshold > 0:
            for date_key, day_value in history.items():
                if not isinstance(day_value, dict):
                    continue
                for market_name, price in day_value.items():
                    if _is_number(price):
                        numeric_price = _as_number(price)
                        if 0 < numeric_price < threshold:
                            report["findings"].append({
                                "type": "implausible_price_magnitude",
                                "date": date_key,
                                "market": market_name,
                                "value": numeric_price,
                                "file_median": median,
                            })

    # --- Missing dates in the observed range (informational) ---
    if dates_present:
        parsed = sorted(date.fromisoformat(d) for d in dates_present)
        expected = parsed[0]
        missing = []
        while expected <= parsed[-1]:
            if expected not in parsed:
                missing.append(expected.isoformat())
            expected += timedelta(days=1)
        if missing:
            report["findings"].append({"type": "missing_dates_in_range", "dates": missing})

    # --- Duplicate records: structurally impossible under this schema ---
    # (JSON object keys are unique both across dates and across markets
    # within a date), included explicitly so the report states this rather
    # than silently omitting the check.
    report["duplicate_records_possible"] = False

    return report


def scan_all(history_dir=HISTORY_DIR):
    if not history_dir.exists():
        return []
    return [validate_file(p) for p in sorted(history_dir.glob("*.json"))]


def _print_report(reports):
    total_files = len(reports)
    total_dates = sum(r["dates_scanned"] for r in reports)
    total_records = sum(r["records_scanned"] for r in reports)
    total_findings = sum(len(r["findings"]) for r in reports)

    print(f"Scanned {total_files} file(s), {total_dates} date-entries, {total_records} market-records.")
    print(f"Total findings: {total_findings}\n")

    for r in reports:
        if not r["findings"]:
            continue
        print(f"--- {r['file']} (expected state: {r['state']}, commodity: {r['commodity']}) ---")
        for f in r["findings"]:
            print(f"  {f}")
        print()


if __name__ == "__main__":
    _print_report(scan_all())
