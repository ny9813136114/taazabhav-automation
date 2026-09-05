import os
import traceback
from datetime import datetime
from fetch_prices import fetch_prices
from generate_script import build_script_and_captions
from make_audio import make_audio
from make_video import make_video
from make_thumbnail import generate_thumbnail
from upload_youtube import upload_video
from price_history import load_yesterday_prices, save_today_prices

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


def _todays_format():
    day_of_year = datetime.now().timetuple().tm_yday
    return FORMAT_ROTATION[day_of_year % len(FORMAT_ROTATION)]


def run_pipeline(state, commodity, lang="hi"):
    print(f"\n=== Processing {commodity} - {state} ===")

    yesterday_prices = load_yesterday_prices(state, commodity)
    records = fetch_prices(state=state, commodity=commodity)

    if not records:
        print(f"No mandi data found for {commodity} in {state} today. Skipping.")
        return

    # build_script_and_captions() returns the exact same narration text as the
    # old build_script() did (make_audio.py doesn't change at all), PLUS the
    # individual sentences split out so they can be burned in as on-screen
    # captions -- captions always say exactly what the voice is saying.
    script, captions = build_script_and_captions(records, state, commodity, lang=lang, yesterday_prices=yesterday_prices)
    print(script)

    today_str = datetime.now().strftime("%d %b %Y")
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

    title = f"#Shorts {commodity} Bhav Today {today_str} | {state} Mandi Price Update"

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
        "APMC price", "kisan mandi rate", "TaazaBhav", "shorts"
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

    try:
        video_id = upload_video(
            video_path, title, description, tags,
            thumbnail_path=thumb_path, comment_text=comment_text,
        )
        print(f"Done! https://youtu.be/{video_id}")
        save_today_prices(state, commodity, records)
    except Exception as e:
        print(f"Upload failed for {commodity} - {state}: {e}")
        traceback.print_exc()

    for f in [audio_path, video_path, thumb_path]:
        if os.path.exists(f):
            os.remove(f)


def main():
    # GitHub Actions sets YT_STATE/YT_COMMODITY for a single scheduled run
    # (one state/commodity per cron trigger, staggered through the morning).
    # Running locally (python main.py) leaves these unset, so it falls back
    # to processing every target in TARGETS in one go -- same as before.
    single_state = os.environ.get("YT_STATE")
    single_commodity = os.environ.get("YT_COMMODITY")
    single_lang = os.environ.get("YT_LANG", "hi")

    if single_state and single_commodity:
        try:
            run_pipeline(single_state, single_commodity, single_lang)
        except Exception as e:
            print(f"Error processing {single_commodity} - {single_state}: {e}")
            traceback.print_exc()
        return

    for target in TARGETS:
        try:
            run_pipeline(target["state"], target["commodity"], target.get("lang", "hi"))
        except Exception as e:
            print(f"Error processing {target}: {e}")
            traceback.print_exc()


if __name__ == "__main__":
    main()
