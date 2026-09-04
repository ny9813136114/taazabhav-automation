import os
from datetime import datetime
from fetch_prices import fetch_prices
from generate_script import build_script
from make_audio import make_audio
from make_video import make_video
from make_thumbnail import generate_thumbnail
from upload_youtube import upload_video
from price_history import load_yesterday_prices, save_today_prices

STATE = os.environ.get("YT_STATE", "Uttar Pradesh")
COMMODITY = os.environ.get("YT_COMMODITY", "Onion")
LANG = os.environ.get("YT_LANG", "hi")


def main():
    yesterday_prices = load_yesterday_prices(STATE, COMMODITY)
    records = fetch_prices(state=STATE, commodity=COMMODITY)

    if not records:
        print("No mandi data found today (mandi holiday?). Skipping.")
        return

    script = build_script(records, STATE, COMMODITY, lang=LANG, yesterday_prices=yesterday_prices)
    print(script)

    today_str = datetime.now().strftime("%d %b %Y")

    make_audio(script, out_path="output.mp3", lang=LANG)
    make_video("output.mp3", records, STATE, COMMODITY, LANG, output_path="output.mp4", date_str=today_str)
    generate_thumbnail(COMMODITY, STATE, records, today_str, out_path="thumb.jpg")

    # ---- SEO-optimized title ----
    title = f"#Shorts {COMMODITY} Bhav Today {today_str} | {STATE} Mandi Price Update"

    # ---- SEO-optimized description ----
    top_markets = records[:5] if records else []
    market_lines = "\n".join(
        f"- {r.get('market')}: Rs.{r.get('modal_price')}/quintal"
        for r in top_markets
    )

    description = (
        f"{COMMODITY} Mandi Bhav Today ({today_str}) - {STATE}\n\n"
        f"Aaj {STATE} ke mandiyon mein {COMMODITY} ka taaza bhav:\n\n"
        f"{market_lines}\n\n"
        f"Ye video roz automatically {STATE} ke APMC mandis ke official data.gov.in data se banti hai. "
        f"Kisan aur vyapari roz ka sahi bhav yahan dekh sakte hain.\n\n"
        f"Subscribe karo TaazaBhav ko roz ka mandi bhav paane ke liye!\n\n"
        f"#mandibhav #{COMMODITY.lower()}price #{STATE.lower().replace(' ', '')}mandi #shorts"
    )

    # ---- SEO tags ----
    tags = [
        "mandi bhav", "mandi bhav today", f"{COMMODITY.lower()} price today",
        f"{COMMODITY.lower()} ka bhav", f"{STATE.lower()} mandi rate",
        f"{STATE.lower()} mandi bhav", "aaj ka mandi bhav", "agriculture price india",
        "APMC price", "kisan mandi rate", "TaazaBhav", "shorts"
    ]

    video_id = upload_video("output.mp4", title, description, tags, thumbnail_path="thumb.jpg")
    print(f"Done! https://youtu.be/{video_id}")

    save_today_prices(STATE, COMMODITY, records)


if __name__ == "__main__":
    main()