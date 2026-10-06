# -*- coding: utf-8 -*-
"""Format A "भाव फ्लैश" (Batch 4, 27 Sep 2026): an 8-second loopable Short
rendered with Remotion (shorts/) over a real produce clip.

Why: vidIQ research (Jun-Sep 2026) showed daily-price Shorts that win in
India are 5-15 s, show real produce, and carry ONE emotion word + ONE per-kg
price for a named mandi. Our 60 s narrated rate lists got 2-60 views.

This module only builds the props and calls the Remotion CLI. main.py falls
back to the old Python renderer if anything here raises, so a Remotion
problem can never cost a day's upload.
"""
import json
import os
import shutil
import subprocess
from pathlib import Path

from hindi_names import commodity_hi, state_hi, date_hi, spoken_market, price_int, inr, page_url
from fetch_clips import pick_clip, credit_for

SHORTS_DIR = Path("shorts")
FONTS = ["Baloo2-Bold.ttf", "IBMPlexMono-SemiBold.ttf"]
RENDER_TIMEOUT = 600

WORD = {
    "low": "सबसे सस्ता!",
    "high": "सबसे ऊँचा भाव!",
    "up": "भाव में उछाल!",
    "down": "भाव गिरा!",
}


def _clip_folder(commodity):
    key = str(commodity).strip().lower()
    for name in ("onion", "potato", "tomato", "garlic", "soyabean", "cotton", "maize", "groundnut"):
        if name in key:
            return name
    return "generic"


def choose_tone(story, slot):
    """Spread days alternate cheapest/dearest across slots so the channel
    shows both sides; other stories lead with the best price (what a farmer
    selling today wants to know)."""
    if story == "spread":
        return "low" if int(slot) % 2 == 1 else "high"
    return "high"


def build_props(records, state, commodity, run_date, story=None, slot=1, clip_name=None, credit=None):
    """records: cleaned rows for ONE state, highest modal first (clean_records)."""
    priced = [r for r in records if price_int(r.get("modal_price")) is not None]
    if len(priced) < 2:
        raise ValueError("need at least 2 priced mandis for a flash")
    tone = choose_tone(story, slot)
    main, other = (priced[-1], priced[0]) if tone == "low" else (priced[0], priced[-1])
    main_q, other_q = price_int(main["modal_price"]), price_int(other["modal_price"])
    return {
        "clip": clip_name,
        "photo": None,
        "credit": credit,
        "tone": tone,
        "word": WORD[tone],
        "commodityHi": commodity_hi(commodity),
        "perKg": round(main_q / 100, 1),
        "perQtl": main_q,
        "mandi": spoken_market(main.get("market", "")),
        "stateHi": state_hi(state),
        "compare": {"mandi": spoken_market(other.get("market", "")), "perKg": round(other_q / 100, 1)},
        "dateHi": date_hi(run_date),
        "seconds": 8,
    }


def flash_metadata(props, commodity, state, run_date, markets_count, credit_line=None):
    kg = int(round(props["perKg"]))
    word = props["word"].rstrip("!")
    title = f"{props['commodityHi']} ₹{kg} किलो! {word} · {props['mandi']} मंडी | {commodity} Rate Today {state} #Shorts"
    if len(title) > 100:
        title = f"{props['commodityHi']} ₹{kg} किलो! {word} · {props['mandi']} | {commodity} Rate Today #Shorts"
    title = title[:100]
    url = page_url(commodity, state)
    other = props["compare"]
    description = (
        f"{date_hi(run_date)}: {props['stateHi']} में {props['commodityHi']} का थोक भाव "
        f"{props['mandi']} मंडी में ₹{inr(props['perQtl'])}/क्विंटल (₹{kg}/किलो), "
        f"वहीं {other['mandi']} में ₹{int(round(other['perKg']))}/किलो। {markets_count} मंडियों के भाव।\n"
        f"हर मंडी का पूरा भाव: {url}\n\n"
        f"Source: Agmarknet / data.gov.in (Government of India). Wholesale (thok) prices; retail prices differ.\n"
        + (f"{credit_line}\n" if credit_line else "")
        + "Telegram: https://t.me/taazabhav\n"
        f"#mandibhav #{commodity.lower().replace(' ', '')}ratetoday #{state.lower().replace(' ', '')}mandi #shorts"
    )
    return title, description


def render(props, out_path, clip_path=None):
    """Copies fonts + clip into shorts/public, writes props, runs Remotion."""
    public = SHORTS_DIR / "public"
    (public / "fonts").mkdir(parents=True, exist_ok=True)
    for f in FONTS:
        shutil.copyfile(Path("assets/fonts") / f, public / "fonts" / f)
    if clip_path:
        shutil.copyfile(clip_path, public / "clip.mp4")
        props = {**props, "clip": "clip.mp4"}
    props_file = (SHORTS_DIR / "props.json").resolve()
    props_file.write_text(json.dumps(props, ensure_ascii=False), encoding="utf-8")
    cmd = ["npx", "remotion", "render", "src/Root.tsx", "BhavFlash", str(Path(out_path).resolve()),
           f"--props={props_file}", "--log=error"]
    browser = os.environ.get("REMOTION_BROWSER_EXECUTABLE")
    if browser:
        cmd.append(f"--browser-executable={browser}")
    subprocess.run(cmd, cwd=SHORTS_DIR, check=True, timeout=RENDER_TIMEOUT)
    return out_path


def make_flash(records, state, commodity, run_date, story=None, slot=1, out_path="flash.mp4"):
    """Returns (video_path, title, description). Raises on any failure."""
    clip = pick_clip(_clip_folder(commodity), run_date, slot)
    c = credit_for(clip)
    credit = f"Video: {c['author']} / {c['source']}" if c else None
    props = build_props(records, state, commodity, run_date, story, slot, credit=credit)
    render(props, out_path, clip_path=clip)
    title, description = flash_metadata(props, commodity, state, run_date, len(records), credit_line=credit)
    return out_path, title, description
