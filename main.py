import os
import re
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
from hindi_names import commodity_hi, state_hi, date_hi, page_url, inr, price_int
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


def get_canonical_run_date():
    """The ONE business date for this entire pipeline execution (Phase 1B-B).

    Called exactly once, here, at the very top of main() -- never inside
    run_pipeline() or any downstream function. Every business-date-dependent
    component (price history, spoken narration, video title/thumbnail,
    description, comment, format-of-the-day selection) receives this same
    value explicitly as a parameter instead of computing its own.

    Why this matters (confirmed, not theoretical -- see docs/RELIABILITY.md
    and the Phase 1B-A investigation report): before this, main.py, generate_
    script.py, and price_history.py each called their own date.today()/
    datetime.now(...) independently. Real production commits proved this
    let a single run's price-history entry, spoken narration date, and
    video title disagree by a full day. Computing the date once here and
    threading it down removes the possibility of that class of bug
    entirely, rather than fixing each disagreement as it's found -- and
    guarantees the date used stays stable even if a run straddles IST
    midnight (fetch_prices.py's retries alone can now take up to ~99s)."""
    return datetime.now(IST).date()


def _todays_format(run_date):
    day_of_year = run_date.timetuple().tm_yday
    return FORMAT_ROTATION[day_of_year % len(FORMAT_ROTATION)]



def build_metadata(commodity, state, records, run_date):
    """Title, description, tags and pinned-comment text (Batch 2, 26 Sep 2026).

    Before: `#Shorts Onion Bhav Today 25 Sep 2026 | Tilhar APMC Mandi, ...`
    -- English-only, and the mandi named was simply the first API row.
    Now: Hindi story + price first (what a Hindi viewer reads in the feed),
    then the English search phrase vidIQ shows real demand for ("onion rate
    today" ~5.2K/month, low competition), then state and date. The
    description and comment lead with the matching taazabhav.com page.

    records are sorted highest modal price first (fetch_prices.clean_records).
    """
    c_hi = commodity_hi(commodity)
    s_hi = state_hi(state)
    day = run_date.strftime("%d %b")
    prices = [p for p in (price_int(r.get("modal_price")) for r in records) if p is not None]
    high = max(prices) if prices else None
    low = min(prices) if prices else None
    top_market = str(records[0].get("market", "")).strip() if records else ""

    if high is not None and low is not None and low < high:
        story = f"{c_hi} का भाव ₹{inr(low)}–₹{inr(high)}"
    elif high is not None:
        story = f"{c_hi} का भाव आज ₹{inr(high)}"
    else:
        story = f"{c_hi} का भाव आज"
    title = f"{story} | {commodity} Rate Today {state} | {day} #Shorts"
    if len(title) > 100:
        title = f"{story} | {commodity} Rate Today | {day} #Shorts"
    title = title[:100]

    url = page_url(commodity, state)
    market_lines = "\n".join(
        f"- {r.get('market')}: ₹{inr(r.get('modal_price'))}/क्विंटल"
        for r in records[:8]
    )
    range_line = (
        f"{s_hi} में आज {c_hi} का भाव ₹{inr(low)} से ₹{inr(high)} प्रति क्विंटल "
        f"({len(prices)} मंडियाँ)।" if prices else f"{s_hi} में आज {c_hi} का भाव।"
    )
    description = (
        f"{range_line}\n"
        f"हर मंडी का पूरा भाव: {url}\n\n"
        f"{commodity} rate today in {state} mandis ({run_date.strftime('%d %b %Y')}):\n"
        f"{market_lines}\n\n"
        f"Source: Agmarknet / data.gov.in (Government of India). "
        f"Prices are per quintal; freight and commission are extra.\n"
        f"TaazaBhav.com — free daily mandi bhav, no subscription.\n"
        f"Telegram: https://t.me/taazabhav\n"
        f"Instagram: https://www.instagram.com/taazabhav/\n"
        f"Facebook: https://www.facebook.com/profile.php?id=61594672476852\n\n"
        f"#mandibhav #{commodity.lower().replace(' ', '')}ratetoday "
        f"#{state.lower().replace(' ', '')}mandi #shorts"
    )
    tags = [
        f"{commodity.lower()} rate today", f"{commodity.lower()} price today",
        "mandi bhav", "mandi bhav today", "aaj ka mandi bhav",
        f"{c_hi} का भाव", f"{c_hi} का भाव आज", f"{commodity.lower()} ka bhav",
        f"{state.lower()} mandi bhav", f"{state.lower()} mandi rate",
        "kisan mandi rate", "APMC price", "TaazaBhav",
    ]
    for r in records[:3]:
        m = str(r.get("market", "")).strip()
        if m:
            tags.append(f"{m.lower()} mandi bhav")
    comment_text = (
        f"आज ({date_hi(run_date)}) {s_hi} में {c_hi} का भाव — सबसे अच्छा: "
        f"{top_market} ₹{inr(high)}.\n"
        f"अपनी मंडी का भाव यहाँ देखें: {url}\n\n"
        f"आपकी मंडी में आज क्या भाव मिला? कमेंट में लिखें।"
    )
    return title, description, tags, comment_text


def run_pipeline(state, commodity, run_date, lang="hi", records=None, story=None, slot=None):
    """run_date: the canonical business date for this whole pipeline
    execution (a datetime.date, IST-derived), computed once by
    get_canonical_run_date() in main() and passed down unchanged -- this
    function must never compute its own "today" for any business-date
    purpose (history key, narration, title, format-of-the-day)."""
    print(f"\n=== Processing {commodity} - {state} ===")

    today_iso = run_date.isoformat()
    if publish_state.is_published(today_iso, state, commodity):
        print(f"Already published today ({today_iso}) for {commodity} - {state}. Skipping to avoid a duplicate upload.")
        return RESULT_SKIPPED_ALREADY_PUBLISHED

    yesterday_prices = load_yesterday_prices(state, commodity)

    try:
        # Batch 3: the story engine (pick_story.py) has usually already
        # fetched and cleaned this pair's rows while scoring -- reuse them
        # instead of hitting data.gov.in a second time.
        if records is None:
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
    script, captions = build_script_and_captions(records, state, commodity, run_date, lang=lang, yesterday_prices=yesterday_prices)
    print(script)

    today_str = run_date.strftime("%d %b %Y")
    format_mode = _todays_format(run_date)
    print(f"Format today: {format_mode}")

    safe_name = f"{state}_{commodity}".replace(" ", "_")
    audio_path = f"output_{safe_name}.mp3"
    video_path = f"output_{safe_name}.mp4"
    thumb_path = f"thumb_{safe_name}.jpg"

    title, description, tags, comment_text = build_metadata(commodity, state, records, run_date)

    # Batch 4: scheduled slots publish the 8 s "भाव फ्लैश" (Remotion + stock
    # clip). Any failure falls back to the classic narrated video below.
    flash_ok = False
    if slot and os.environ.get("TB_FORMAT", "flash") == "flash":
        try:
            import flash
            video_path, title, description = flash.make_flash(
                records, state, commodity, run_date, story=story, slot=slot, out_path=video_path)
            thumb_path = None
            flash_ok = True
            print(f"Flash rendered: {title}")
        except Exception as e:
            print(f"Flash render failed, using classic video: {e}")
            traceback.print_exc()

    if not flash_ok:
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

    result = RESULT_SUCCESS
    try:
        video_id = upload_video(
            video_path, title, description, tags,
            thumbnail_path=thumb_path, comment_text=comment_text,
        )
        print(f"Done! https://youtu.be/{video_id}")
        save_today_prices(state, commodity, records, run_date)
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
        if f and os.path.exists(f):
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

    # ONE canonical business date for this entire process execution --
    # computed exactly once, here, before any target is processed, and
    # passed explicitly to every run_pipeline() call below. See
    # get_canonical_run_date()'s docstring for why: this is what makes a
    # multi-target workflow_dispatch run (which can take many minutes)
    # immune to date drift between its targets, and what makes each
    # target's own history/narration/title internally consistent.
    run_date = get_canonical_run_date()

    # GitHub Actions sets YT_STATE/YT_COMMODITY for a single scheduled run
    # (one state/commodity per cron trigger, staggered through the morning).
    # Running locally (python main.py) leaves these unset, so it falls back
    # to processing every target in TARGETS in one go -- same as before.
    single_slot = os.environ.get("YT_SLOT")
    single_state = os.environ.get("YT_STATE")
    single_commodity = os.environ.get("YT_COMMODITY")
    single_lang = os.environ.get("YT_LANG", "hi")

    if single_slot:
        # Batch 3: a scheduled slot picks the day's strongest story
        # (pick_story.py) instead of a fixed state/crop. Falls back to the
        # old fixed target for this slot if nothing can be scored.
        import pick_story
        try:
            ranked = pick_story.ranked_for_today(run_date)
            state, commodity, pre_records, reason = pick_story.choose_for_slot(
                single_slot, run_date, publish_state.is_published, ranked)
        except Exception as e:
            state, commodity = pick_story.FALLBACK_BY_SLOT.get(int(single_slot), pick_story.FALLBACK_BY_SLOT[1])
            pre_records, reason = None, f"fallback after story-engine error: {e}"
        print(f"Slot {single_slot}: {commodity} - {state} ({reason})")
        try:
            m = re.search(r"story=(\w+)", reason or "")
            results.append(run_pipeline(state, commodity, run_date, single_lang, records=pre_records,
                                        story=m.group(1) if m else None, slot=int(single_slot)))
        except Exception as e:
            print(f"Error processing {commodity} - {state}: {e}")
            traceback.print_exc()
            send_telegram_alert(f"TaazaBhav ALERT: slot {single_slot} ({commodity} - {state}) run crashed\n\n{e}")
            results.append(RESULT_FAILED)
    elif single_state and single_commodity:
        try:
            results.append(run_pipeline(single_state, single_commodity, run_date, single_lang))
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
                results.append(run_pipeline(target["state"], target["commodity"], run_date, target.get("lang", "hi")))
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
