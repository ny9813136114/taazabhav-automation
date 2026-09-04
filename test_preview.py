from datetime import datetime
from fetch_prices import fetch_prices
from generate_script import build_script
from make_audio import make_audio
from make_video import make_video
from make_thumbnail import generate_thumbnail
from price_history import load_yesterday_prices

STATE = "Uttar Pradesh"
COMMODITY = "Onion"
LANG = "hi"

yesterday_prices = load_yesterday_prices(STATE, COMMODITY)
records = fetch_prices(state=STATE, commodity=COMMODITY)

script = build_script(records, STATE, COMMODITY, lang=LANG, yesterday_prices=yesterday_prices)
print(script)

today_str = datetime.now().strftime("%d %b %Y")

make_audio(script, out_path="preview.mp3", lang=LANG)
make_video("preview.mp3", records, STATE, COMMODITY, LANG, output_path="preview.mp4", date_str=today_str)
generate_thumbnail(COMMODITY, STATE, records, today_str, out_path="preview_thumb.jpg")

print("Preview ready: preview.mp4 and preview_thumb.jpg")