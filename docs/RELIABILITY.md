# TaazaBhav Reliability Notes (Phase 1A)

This document covers what changed in Phase 1A ("make the existing
production pipeline reliable") and how to reason about failure behavior,
duplicate protection, and historical data validation going forward. It is
not a redesign doc -- the data pipeline, video rendering, TTS, and YouTube
upload logic are all unchanged; this only covers the reliability layer
wrapped around them.

## 1. Failure behavior

### What "success" and "failure" mean now

Before Phase 1A, `main.py` caught every exception, sent a Telegram alert,
and always exited 0 -- so GitHub Actions could show "Success" on a day when
no video was produced at all (confirmed in production: runs where
data.gov.in returned `502 Bad Gateway`).

Now:
- **`data.gov.in` fails, retries succeed** -> pipeline continues normally,
  nothing to see in the exit code.
- **`data.gov.in` fails, retries exhausted** (`fetch_prices.DataFetchError`)
  -> `run_pipeline()` returns `RESULT_FAILED`, a Telegram alert is sent
  (unchanged from before), and `main()`'s exit code becomes non-zero once
  every target has been attempted. GitHub Actions now shows **FAILURE**.
- **`data.gov.in` succeeds but returns zero records for that state/commodity
  today** -> this is a legitimate, common, non-error outcome (not every
  state reports every commodity every day). `run_pipeline()` returns
  `RESULT_SKIPPED_NO_DATA`. No alert. Does **not** contribute to a failure
  exit code.
- **Already published today** (see duplicate protection below) ->
  `RESULT_SKIPPED_ALREADY_PUBLISHED`. No alert, no failure. The fetch is
  skipped entirely (not just the upload), so a re-run costs nothing extra.
- **Video generation (audio/video/thumbnail) raises** -> propagates out of
  `run_pipeline()` exactly as before Phase 1A; `main()`'s existing
  per-target `try/except` catches it, alerts, and now also records it as a
  failure for the final exit code.
- **YouTube upload raises** -> caught inside `run_pipeline()` (unchanged
  location), alerts, returns `RESULT_FAILED`. Price history and the
  published-log are both left untouched (see below).
- **Telegram alert itself fails** -> `notify.send_telegram_alert()` is
  intentionally unchanged and still fails silently *to the pipeline*
  (it must never turn one real failure into two), but it prints a clear
  `Telegram alert failed: ...` line either way, so the failure is visible
  in the job's own logs even if the alert never reaches Telegram.

### Per-target isolation is preserved

`main.py` can run in two modes:
- **Single target** (`YT_STATE`/`YT_COMMODITY` set -- the normal scheduled
  cron path, one state/commodity per workflow run): a failure here simply
  means the one target for that run failed; the job fails.
- **Multi target** (`workflow_dispatch`, no env vars set -- processes all 5
  `TARGETS`): every target is still attempted regardless of how an earlier
  one ended. `main()` collects a result per target and only computes the
  final exit code (0 or 1) *after* the loop finishes. One target's
  permanent failure never aborts the others.

### Retry policy (`fetch_prices.py`)

- Retries only transient failures: `ConnectionError`, `Timeout`, and HTTP
  500/502/503/504. A 4xx (e.g. a bad `api-key`) fails on the first attempt
  -- retrying a request that can never succeed would just waste time.
- Bounded: `MAX_ATTEMPTS = 3` (1 initial + 2 retries), backoff delays of
  `[3, 6]` seconds between attempts, each attempt capped at the existing
  30s request timeout.
- Every retry is logged (`[fetch_prices] Attempt N/3 failed (...); retrying
  in Ns...`), and the final `DataFetchError` is chained (`raise ... from
  last_exc`) so the original error is always visible in the traceback.

**Worst-case added time** (every attempt hangs to the full 30s timeout --
the worst case, not the typical one; a fast 502 response adds only a few
seconds):
- One target: `3 * 30s + (3 + 6)s = 99s` (~1m39s), vs. ~30s before Phase 1A
  -- a net worst-case increase of about **69 seconds per failing target**.
- Five targets, all failing maximally (`workflow_dispatch`): `5 * 99s =
  495s` (~8m15s), plus the workflow's fixed ~1 minute of
  checkout/setup/dependency-install steps -> **~9-9.5 minutes worst case**,
  comfortably inside `daily.yml`'s existing 20-minute job timeout. (Note:
  this pre-existing timeout was already sized around 5 targets' worth of
  *successful* render+upload time, ~25 minutes in the worst case if every
  target succeeds and each render+upload takes ~5 minutes -- that headroom
  question is independent of Phase 1A and unaffected by it, since retries
  only add time on the *failure* path, not the success path.)

### Why the "Commit price history" step now has `if: always()`

`save_today_prices()` and `publish_state.mark_published()` are written to
local files as each target completes inside the same job -- they are not
committed to git until the "Commit price history" step runs afterward. With
`main.py` now able to exit non-zero, GitHub Actions' default `if:
success()` step behavior would **skip that commit step entirely** whenever
any target failed -- discarding the real, valid history/published-state
files written by any *other* target that succeeded in the same
`workflow_dispatch` run. `if: always()` was added to both `daily.yml`'s and
`telegram_daily.yml`'s commit steps specifically to prevent this; it does
not change whether the job is reported as failed (the earlier "Run
pipeline" step's exit code still does that).

## 2. Duplicate protection (`publish_state.py`)

- **Identity**: `(date, state, commodity)`, matching the actual content
  architecture exactly -- `main.py`'s `TARGETS` are state/commodity pairs,
  and one video is produced per target per day (aggregating that state's
  top markets into a single upload). Market/mandi name is *not* part of
  the identity, since a single video already covers several markets within
  one state.
- **Date source**: the IST calendar date (`datetime.now(IST).date().isoformat()`
  in `main.py`), matching the date already shown to viewers in the video
  title/thumbnail -- not the server's UTC date, and not `price_history.py`'s
  own `date.today()` (see "Known limitation" below).
- **Where it's stored**: `data/published/published_log.json`, one flat JSON
  file, same style as `data/history/*.json` -- no database. Committed back
  to the repo by the same "Commit price history" workflow step that already
  commits `data/history/`, so it survives across GitHub Actions runs the
  same way price history already does.
- **When it's written**: `publish_state.mark_published(...)` is called in
  `main.py` **only** immediately after `upload_youtube.upload_video()` has
  already returned a real `video_id` -- never before, and never on a path
  that could still raise. This is a **separate function call, writing a
  separate file**, from `price_history.save_today_prices()` (which itself
  is also gated on upload success, per the pre-existing code -- but the two
  are independent writes, so neither can be silently inferred from the
  other).
- **How retries work**: if `upload_video()` raises, `mark_published()` is
  never reached, so the target is never recorded as published and remains
  eligible to be retried (a manual `workflow_dispatch` re-run, or the next
  day's cron for that target). If a target IS already marked published for
  today, `run_pipeline()` checks this **before even calling
  `fetch_prices()`**, so a redundant re-run costs nothing beyond reading one
  small JSON file.
- **Capacity**: the log retains the most recent 30 distinct dates; older
  entries are pruned on each write (mirroring `price_history.py`'s own
  14-day rolling window, just with a larger margin since each entry here is
  a few bytes).

## 3. Historical validation (`validate_history.py`)

Read-only. Run it any time with `python validate_history.py`; it never
modifies a file.

### What is validated (all deterministic given the actual schema)
- **Invalid schema**: a date value that isn't an object, or a price that is
  neither numeric nor the literal `"N/A"` placeholder that
  `price_history.save_today_prices()` itself writes for a missing
  `modal_price`.
- **Empty market names**: a market key that is empty/whitespace-only.
- **Wrong-state contamination**: a date entry where *100% of that day's
  market names* carry an unambiguous other-state signature (currently:
  Tamil Nadu's "Uzhavar Sandhai" farmers'-market naming). Requiring the
  *entire* day to match (not a single stray record) keeps this
  deterministic rather than a fuzzy guess, and matches exactly how the
  confirmed 2026-09-04 incident actually looked (all 15 records that day
  were Tamil Nadu markets, zero were Uttar Pradesh).
- **Implausible price magnitude**: a numeric price under 5% of that file's
  own median price. Flagged only, never auto-corrected -- there is no
  ground truth to correct against, and a real, if unusual, low price is
  possible.
- **Missing dates**: a gap in the day-by-day sequence between a file's
  earliest and latest recorded date. Informational -- a legitimate
  `RESULT_SKIPPED_NO_DATA` day also produces a gap.
- **Duplicate records**: structurally impossible under this schema (JSON
  object keys are unique both across dates and across markets within a
  date) -- the report states this explicitly rather than silently omitting
  the check.

### What cannot be validated
- **Commodity mismatch**: the schema does not store a commodity field per
  record (it's implied entirely by the filename), so there is nothing to
  cross-check a record's commodity against.
- **Whether a flagged low price is actually wrong**: the validator has no
  authoritative source to compare against; it can only say "this is far
  outside this file's own typical range," not "this is incorrect."
- **Live API-side issues**: this only looks at what's already committed to
  `data/history/`; it says nothing about the current state of the
  data.gov.in feed itself.

### How the confirmed incident was handled

`data/history/uttar-pradesh-onion.json`'s `2026-09-04` entry contained 15
records, all Tamil Nadu "Uzhavar Sandhai" markets, zero Uttar Pradesh
markets. This is now understood precisely: the pre-fix version of
`fetch_prices()` (commit `8daf93e`) contained

```python
if not state_records:
    return all_records[:limit]
return state_records[:limit]
```

i.e. whenever the state filter matched **zero** records, it silently fell
back to the first `limit` records of the entire *unfiltered, all-states*
response. On 2026-09-04, Uttar Pradesh apparently had zero Onion records
that day, so the fallback fired and returned whatever the API's first 15
records happened to be that day (Tamil Nadu). The very next commit on the
same day (`41d9eee`, "Fix fetch_prices.py: stop silently falling back to
wrong-state data when no records match") removed exactly this fallback --
consistent, verified, and matching the commit message exactly. The current
`fetch_prices.py` (Phase 1A version) preserves that fix and additionally
makes the "zero records" case a documented, intentional, non-error return
value (see `fetch_prices.fetch_prices()`'s docstring).

The one contaminated date entry was removed from
`data/history/uttar-pradesh-onion.json`, leaving an honest gap for that
date (the file already has one such gap, `2026-09-03: {}`, for a day with
a legitimate empty result) rather than fabricated or guessed data. No other
file in `data/history/` or `data/telegram_history/` showed this same
100%-of-day contamination pattern in the Phase 1A scan (see the
implementation report for exact scan counts).

### A related, separate, and NOT-yet-fixed finding

The Phase 1A scan also found a **price-scale anomaly specific to Punjab
records** (e.g. `Rs. 0.08` where every other state shows `Rs. 500-1500`
for the same commodity), reproduced independently across both
`data/history/punjab-potato.json` and the separately-maintained
`data/telegram_history/Punjab.json`. This is a different bug class from
the wrong-state contamination above -- the state/market attribution here
looks correct, only the price magnitude is implausible -- and it was only
flagged, not corrected, since there is no deterministic way to know the
intended value. This is recommended as Phase 1B (Data Trust) work, not
addressed in Phase 1A.

## Known limitation carried forward (not fixed in Phase 1A)

`price_history.py`'s `save_today_prices()`/`load_yesterday_prices()` use
`date.today()` (the server's local/UTC date), while `main.py` computes the
IST date explicitly for everything shown to viewers (title, thumbnail, and
now `publish_state`'s identity key). This pre-existing inconsistency was
deliberately left alone in Phase 1A -- fixing it touches
`price_history.py`'s date handling more broadly than the reliability issues
in scope here, and `publish_state.py` was written to source its date from
the caller (`main.py`'s already-correct IST date) specifically so it
doesn't inherit this problem. Recommended as Phase 1B follow-up.
