import os
from datetime import datetime
from fetch_prices import fetch_prices
from generate_script import build_script
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
    {"state": "Punjab", "commodity": "Wheat", "lang": "hi"},
]


def run_pipeline(state, commodity, lang="hi"):
    print(f"\n=== Processing {commodity} - {state} ===")

    yesterday_prices = load_yesterday_prices(state, commodity)
    records = fetch_prices(state=state, commodity=commodity)

    if not records:
        print(f"No mandi data found for {commodity} in {state} today. Skipping.")
        return

    script = build_script(records, state, commodity, lang=lang, yesterday_prices=yesterday_prices)
    print(script)

    today_str = datetime.now().strftime("%d %b %Y")

    safe_name = f"{state}_{commodity}".replace(" ", "_")
    audio_path = f"output_{safe_name}.mp3"
    video_path = f"output_{safe_name}.mp4"
    thumb_path = f"thumb_{safe_name}.jpg"

    make_audio(script, out_path=audio_path, lang=lang)
    make_video(audio_path, records, state, commodity, lang, output_path=video_path, date_str=today_str)
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

    try:
        video_id = upload_video(video_path, title, description, tags, thumbnail_path=thumb_path)
        print(f"Done! https://youtu.be/{video_id}")
        save_today_prices(state, commodity, records)
    except Exception as e:
        print(f"Upload failed for {commodity} - {state}: {e}")

    for f in [audio_path, video_path, thumb_path]:
        if os.path.exists(f):
            os.remove(f)


def main():
    for target in TARGETS:
        try:
            run_pipeline(target["state"], target["commodity"], target.get("lang", "hi"))
        except Exception as e:
            print(f"Error processing {target}: {e}")


if __name__ == "__main__":
    main()