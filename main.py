import os
from fetch_prices import fetch_prices
from generate_script import build_script
from make_audio import make_audio
from make_video import make_video
from upload_youtube import upload_video
from price_history import load_yesterday_prices, save_today_prices

STATE = os.environ.get("YT_STATE", "Uttar Pradesh")
COMMODITY = os.environ.get("YT_COMMODITY", "Onion")
LANG = os.environ.get("YT_LANG", "hi")


def main():
    yesterday_prices = load_yesterday_prices(STATE, COMMODITY)
    records = fetch_prices(state=STATE, commodity=COMMODITY)
    script = build_script(records, STATE, COMMODITY, lang=LANG, yesterday_prices=yesterday_prices)
    print(script)

    make_audio(script, out_path="output.mp3", lang=LANG)
    make_video("output.mp3", records, STATE, COMMODITY, LANG, output_path="output.mp4")

    title = f"{COMMODITY} Bhav Today - {STATE} Mandi Price Update"
    description = (
        "Daily mandi (agricultural market) price update, auto-generated from "
        "data.gov.in official data.\n\nSubscribe for daily updates from mandis across India."
    )
    tags = ["mandi bhav", f"{COMMODITY.lower()} price", f"{STATE.lower()} mandi", "agriculture", "TaazaBhav"]

    video_id = upload_video("output.mp4", title, description, tags)
    print(f"Done! https://youtu.be/{video_id}")

    save_today_prices(STATE, COMMODITY, records)


if __name__ == "__main__":
    main()