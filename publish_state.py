"""Minimal duplicate-upload guard for the YouTube pipeline.

Identity: a video is one (date, state, commodity) triple -- this matches
main.py's actual content architecture exactly (TARGETS is a list of
state/commodity pairs, one video is produced per target per day, aggregating
that state's top markets into a single upload). Market/mandi name is NOT
part of the identity: a single video already covers multiple markets within
one state, so it is not a separate publishing axis.

Storage: a single flat JSON file, data/published/published_log.json, in the
same style as price_history.py's data/history/*.json files (plain
json.loads/dumps, no database). Kept as its OWN file/write, deliberately
separate from price_history.py's writes: price history is recorded once a
fetch succeeds (see main.py), while this log is recorded only once a YouTube
upload actually succeeds -- merging the two would risk marking a target as
"published" on a run where the fetch worked but the upload itself failed.

Survives across GitHub Actions runs the same way data/history/ already does:
committed back to the repo by the same "Commit price history" workflow step
this repo already runs after every pipeline execution (see
.github/workflows/daily.yml).
"""
import json
from pathlib import Path

LOG_PATH = Path("data/published/published_log.json")

# How many distinct dates' entries to retain. This only needs to cover
# "was this already published very recently" (same-day retries/re-runs are
# the actual failure mode this guards against), so a modest window is
# enough; kept generous relative to price_history.py's 14-day window since
# each entry here is a few bytes.
MAX_DATES_RETAINED = 30


def _key(state, commodity):
    return f"{state.strip().lower()}|{commodity.strip().lower()}"


def _load_log():
    if not LOG_PATH.exists():
        return {}
    try:
        return json.loads(LOG_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        # A corrupted log must never crash the pipeline or silently block
        # all future uploads -- treat it as empty (nothing on record) and
        # let the next successful mark_published() call rewrite it cleanly.
        print(f"[publish_state] WARNING: {LOG_PATH} is not valid JSON; treating as empty.")
        return {}


def is_published(date_iso, state, commodity):
    """Returns True if (date_iso, state, commodity) already has a recorded
    successful upload. date_iso must be an ISO date string (YYYY-MM-DD),
    computed by the caller in the same timezone used to label the content
    (IST for this pipeline -- see main.py) so the identity matches what a
    viewer actually sees as "today" on the video."""
    log = _load_log()
    day = log.get(date_iso, {})
    return _key(state, commodity) in day


def mark_published(date_iso, state, commodity, video_id):
    """Records a successful upload. Callers MUST only call this after
    upload_youtube.upload_video() has returned a real video_id -- never
    before, and never on a path that could still raise."""
    log = _load_log()
    day = log.setdefault(date_iso, {})
    day[_key(state, commodity)] = {"video_id": video_id}

    for old_date in sorted(log.keys())[:-MAX_DATES_RETAINED]:
        del log[old_date]

    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    LOG_PATH.write_text(json.dumps(log, ensure_ascii=False, indent=2), encoding="utf-8")
