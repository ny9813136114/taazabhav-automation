import os
import sys
import traceback
from datetime import datetime, timezone, timedelta
from fetch_prices import fetch_prices, DataFetchError

# GitHub Actions runners' clock (and Python's datetime.now()) is UTC, but
# every cron time in daily.yml was picked to land at a specific IST wall-clock
# time (e.g. "30 23 * * *" = 23:30 UTC = 05:00 IST). IST is UTC+5:30, so on
# any run between 18:30 UTC and 23:59 UTC the UTC calendar date is still
# YESTERDAY relative to India even though it's already tomorrow morning in
# IST -- three of the five daily runs (23:30/23:40/23:50 UTC) land in that
# window, which is why their video titles/thumbnails were showing the wrong
# (previous) date. Every date shown to viewers must be computed from IST,
# not from the server's own UTC clock.
IST = timezone(timedelta(hours=5, minutes=30))
from generate_script import build_script_and_captions
from make_audio import make_audio
from make_video import make_video
from make_thumbnail import generate_thumbnail
from upload_youtube import upload_video
from price_history import load_yesterday_prices, save_today_prices
from notify import send_telegram_alert
import publish_state
# ---- States/commodities to cover in each daily run (items with real daily demand) ----
TARGETS = [
    {"state": "Uttar Pradesh", "commodity": "Onion", "lang": "hi"},
    {"state": "Maharashtra", "commodity": "Onion", "lang": "hi"},
    {"state": "West Bengal", "commodity": "Potato", "lang": "hi"},
    {"state": "Karnataka", "commodity": "Tomato", "lang": "hi"},
    {"state": "Punjab", "commodity": "Potato", "lang": "hi"},
]
# ---- Content-format variety: rotates day to day so the channel doesn't look
# like the same templated video every single day (also helps with YouTube's
# repetitive/inauthentic-content policy risk on a fully-automated channel).
# Four formats, all built on the exact same narration/captions/timing --
# only the visuals differ, so this stays 100% automated with no extra
# manual work per format:
#   ticker     -- original data-table price card + "other mandis" list
#   trend      -- adds one Bull vs Bear day-over-day segment at the end
#                 (falls back to ticker automatically if no price history
#                 is available yet for that target)
#   countdown  -- same 3 narrated markets shown as a #1/#2/#3 rank reveal
#   spotlight  -- same 3 narrated markets shown as a min/max/modal range gauge
# Every day of the year lands on the same format across all 5 videos, picked
# deterministically so every scheduled run that day (each is a separate
# GitHub Actions job) agrees on which format to use without needing to
# share state between them.
FORMAT_ROTATION = ["ticker", "trend", "countdown", "spotlight"]

# ---------------------------------------------------------------------------
# Per-target outcome. Callers of run_pipeline() (main(), and tests) branch on
# these instead of relying on exceptions alone, so that:
#   - a legitimate "no data today" skip is never treated as a failure, and
#   - a real failure (fetch, render, or upload) is never treated as success,
# while every target is still attempted regardless of how a prior one ended
# (see main() below).
# ---------------------------------------------------------------------------
RESULT_SUCCESS = "success"
RESULT_SKIPPED_NO_DATA = "skipped_no_data"
RESULT_SKIPPED_ALREADY_PUBLISHED = "skipped_already_published"
RESULT_FAILED = "failed"


def _todays_format():
    day_of_year = datetime.now(IST).timetuple().tm_yday
    return FORMAT_ROTATION[day_of_year % len(FORMAT_ROTATION)]


def run_pipeline(state, commodity, lang="hi"):
    print(f"\n=== Processing {commodity} - {state} ===")

    # Captured once and reused for both today_iso (publish_state's identity
    # key) and today_str (the date shown to viewers) below -- fetch_prices()
    # can now take up to ~99s under the Phase 1A retry policy, and computing
    # these from two separate datetime.now(IST) calls straddling that delay
    # could let them disagree across an IST midnight (a review finding on
    # this branch: the guard's key and the displayed date drifting apart).
    now_ist = datetime.now(IST)
    today_iso = now_ist.date().isoformat()
    if publish_state.is_published(today_iso, state, commodity):
        print(f"Already published today ({today_iso}) for {commodity} - {state}. Skipping to avoid a duplicate upload.")
        return RESULT_SKIPPED_ALREADY_PUBLISHED

    yesterday_prices = load_yesterday_prices(state, commodity)

    try:
        records = fetch_prices(state=state, commodity=commodity)
    except DataFetchError as e:
        # A genuine upstream failure (data.gov.in unreachable/erroring even
        # after retries) -- this is NOT the same as a legitimate empty
        # result and must be surfaced as a pipeline failure, not silently
        # swallowed. See fetch_prices.py's retry policy and docs/RELIABILITY.md.
        print(f"Data fetch permanently failed for {commodity} - {state}: {e}")
        traceback.print_exc()
        send_telegram_alert(f"TaazaBhav ALERT: data fetch failed for {commodity} - {state}\n\n{e}")
        return RESULT_FAILED

    if not records:
        print(f"No mandi data found for {commodity} in {state} today. Skipping.")
        return RESULT_SKIPPED_NO_DATA

    # build_script_and_captions() returns the exact same narration text as the
    # old build_script() did (make_audio.py doesn't change at all), PLUS the
    # individual sentences split out so they can be burned in as on-screen
    # captions -- captions always say exactly what the voice is saying.
    script, captions = build_script_and_captions(records, state, commodity, lang=lang, yesterday_prices=yesterday_prices)
    print(script)

    today_str = now_ist.strftime("%d %b %Y")
    format_mode = _todays_format()
    print(f"Format today: {format_mode}")

    safe_name = f"{state}_{commodity}".replace(" ", "_")
    audio_path = f"output_{safe_name}.mp3"
    video_path = f"output_{safe_name}.mp4"
    thumb_path = f"thumb_{safe_name}.jpg"

    make_audio(script, out_path=audio_path, lang=lang)
    make_video(
        audio_path, records, state, commodity, lang,
        output_path=video_path, date_str=today_str,
        intro_caption=captions["intro"],
        market_captions=captions["markets"],
        format_mode=format_mode,
        trend_data=captions["trend_data"],
        trend_caption=captions["trend"],
    )
    generate_thumbnail(commodity, state, records, today_str, out_path=thumb_path)

    # Specific mandi/APMC name (e.g. "Sealdah", "Azadpur") straight from
    # today's data.gov.in record, not just the broad state name. Real
    # competitor channels in this niche (checked via vidIQ) name their
    # specific mandi and rank far better on it than on the state name --
    # e.g. "mandsaur mandi bhav" scores much less competitive (33/100)
    # than generic "mandi bhav" (48/100) in vidIQ's own keyword data.
    # Falls back to the state name on the rare day a record has no market
    # field, so this never breaks the pipeline.
    mandi_name = str(records[0].get("market", "")).strip() if records else ""
    location_label = mandi_name if mandi_name else state

    title = f"#Shorts {commodity} Bhav Today {today_str} | {location_label} Mandi, {state}"

    top_markets = records[:5]
    market_lines = "\n".join(
        f"- {r.get('market')}: Rs.{r.get('modal_price')}/quintal"
        for r in top_markets
    )
    description = (
        f"{commodity} Mandi Bhav Today ({today_str}) - {state}\n\n"
        f"Aaj {state} ke mandiyon mein {commodity} ka taaza bhav:\n\n"
        f"{market_lines}\n\n"
        f"Ye video roz automatically {state} ke APMC mandis ke official data.gov.in data se banti hai. "
        f"Kisan aur vyapari roz ka sahi bhav yahan dekh sakte hain.\n\n"
        f"Subscribe karo TaazaBhav ko roz ka mandi bhav paane ke liye!\n\n"
        f"#mandibhav #{commodity.lower()}price #{state.lower().replace(' ', '')}mandi #shorts"
    )
    tags = [
        "mandi bhav", "mandi bhav today", f"{commodity.lower()} price today",
        f"{commodity.lower()} ka bhav", f"{state.lower()} mandi rate",
        f"{state.lower()} mandi bhav", "aaj ka mandi bhav", "agriculture price india",
        "APMC price", "kisan mandi rate", "TaazaBhav", "shorts",
        f"{location_label.lower()} mandi bhav",
    ]

    # Auto-posted immediately after upload for engagement/SEO. NOTE: the
    # YouTube Data API has no "pin comment" endpoint at all (only
    # list/insert/update/delete/setModerationStatus exist on Comments), so
    # this can't be auto-pinned -- it just posts the comment. Pin it
    # manually in YouTube Studio if you want it pinned (one tap per video).
    comment_text = (
        f"Aaj ({today_str}) {state} ke mandiyon mein {commodity} ka poora bhav:\n\n"
        f"{market_lines}\n\n"
        f"Ye update roz subah 6 baje se pehle milega. Channel subscribe karein "
        f"taaki koi din miss na ho."
    )

    result = RESULT_SUCCESS
    try:
        video_id = upload_video(
            video_path, title, description, tags,
            thumbnail_path=thumb_path, comment_text=comment_text,
        )
        print(f"Done! https://youtu.be/{video_id}")
        save_today_prices(state, commodity, records)
        # Deliberately a separate write from save_today_prices() above, and
        # deliberately placed only after upload_video() has already returned
        # a real video_id -- if upload_video() raised, we never reach this
        # line, so a failed upload can never be mistaken for a published one
        # on a subsequent retry. See publish_state.py.
        publish_state.mark_published(today_iso, state, commodity, video_id)
    except Exception as e:
        print(f"Upload failed for {commodity} - {state}: {e}")
        traceback.print_exc()
        send_telegram_alert(f"TaazaBhav ALERT: upload failed for {commodity} - {state}\n\n{e}")
        result = RESULT_FAILED
    for f in [audio_path, video_path, thumb_path]:
        if os.path.exists(f):
            os.remove(f)
    return result


def main():
    """Returns a process exit code: 0 if every attempted target either
    succeeded or was legitimately skipped (no data / already published),
    non-zero if at least one target had a real failure (fetch, render, or
    upload). Every target is always attempted regardless of how earlier
    ones ended -- a failure is recorded and processing continues, exactly
    like the pre-existing per-target try/except behavior; only the final
    exit code is new."""
    results = []

    # GitHub Actions sets YT_STATE/YT_COMMODITY for a single scheduled run
    # (one state/commodity per cron trigger, staggered through the morning).
    # Running locally (python main.py) leaves these unset, so it falls back
    # to processing every target in TARGETS in one go -- same as before.
    single_state = os.environ.get("YT_STATE")
    single_commodity = os.environ.get("YT_COMMODITY")
    single_lang = os.environ.get("YT_LANG", "hi")

    if single_state and single_commodity:
        try:
            results.append(run_pipeline(single_state, single_commodity, single_lang))
        except Exception as e:
            print(f"Error processing {single_commodity} - {single_state}: {e}")
            traceback.print_exc()
            send_telegram_alert(
                f"TaazaBhav ALERT: {single_commodity} - {single_state} run crashed\n\n{e}"
            )
            results.append(RESULT_FAILED)
    else:
        for target in TARGETS:
            try:
                results.append(run_pipeline(target["state"], target["commodity"], target.get("lang", "hi")))
            except Exception as e:
                print(f"Error processing {target}: {e}")
                traceback.print_exc()
                send_telegram_alert(
                    f"TaazaBhav ALERT: {target['commodity']} - {target['state']} run crashed\n\n{e}"
                )
                results.append(RESULT_FAILED)

    any_failed = any(r == RESULT_FAILED for r in results)
    if any_failed:
        print(f"\nPipeline finished with at least one failure: {results}")
        return 1
    print(f"\nPipeline finished: {results}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
