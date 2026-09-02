from fetch_prices import fetch_prices
from generate_script import build_script
from make_audio import make_audio
from make_video import make_video
from upload_youtube import upload_video

state = "Uttar Pradesh"
commodity = "Onion"

records = fetch_prices(state=state, commodity=commodity)
script = build_script(records, state=state, commodity=commodity, lang="hi")
print(script)

make_audio(script, out_path="test_audio.mp3", lang="hi")
print("Audio saved")

make_video("test_audio.mp3", records, state, commodity, "hi", output_path="test_video.mp4")
print("Video saved")

title = f"{commodity} Bhav Today - {state} Mandi Price Update"
description = "Daily mandi (agricultural market) price update, auto-generated from data.gov.in official data.\n\nSubscribe for daily updates from mandis across India."
tags = ["mandi bhav", "onion price", "uttar pradesh mandi", "agriculture", "TaazaBhav"]

video_id = upload_video("test_video.mp4", title, description, tags)
print(f"Done! https://youtu.be/{video_id}")