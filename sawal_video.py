# -*- coding: utf-8 -*-
"""Batch 8 (6 Oct 2026): "सवाल-जवाब" explainer Shorts, one a day at 12:30 IST.

Each video answers ONE farmer question (PM Kisan, khad rate, mandi parchi,
crop-loss claim, MSP, rabi farming, fraud alerts) in ~20-30 s with a free AI
Hindi voice (edge-tts), then sends the viewer to the matching taazabhav.com
tool page. Does NOT need price data, so the channels keep posting while the
price feed is down.

Content comes from content/queue.json (written by Claude in batches of ~30).
Every number in it was copied from the website's own lib files on the date
in `checked_on`, so the site and the videos say the same thing. Items with
`valid_to` stop by themselves after that date (season-bound reminders).

Safety: a scheduled run only publishes when the repo variable SAWAL_LIVE is
"1". Until then it renders the video and sends it to the owner's Telegram
chat as a preview, so the first videos can be checked before anything goes
public. A manual run with mode=publish publishes once.
"""
import asyncio
import json
import os
import re
import subprocess
import sys
import traceback
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import requests

from hindi_names import date_hi

IST = timezone(timedelta(hours=5, minutes=30))
QUEUE = Path("content/queue.json")
PUBLISHED = Path("data/published_sawal.json")
REPEAT_AFTER_DAYS = 60
VOICE = os.environ.get("SAWAL_VOICE", "hi-IN-SwaraNeural")
CHANNEL = "@taazabhav"
TAIL_SECONDS = 1.2  # silence after the last line so the loop doesn't cut the CTA

PILLAR = {
    "sarkari": ("सरकारी पैसा", "gold"),
    "khad": ("खाद का सही रेट", "gold"),
    "hisab": ("मंडी पर्ची चेक", "gold"),
    "nuksan": ("फसल नुकसान", "red"),
    "msp": ("MSP या मंडी?", "gold"),
    "kheti": ("खेती का काम", "green"),
    "dhokha": ("धोखा अलर्ट", "red"),
}


# ---------------------------------------------------------------- queue
def load_queue(path=QUEUE):
    return json.loads(Path(path).read_text(encoding="utf-8"))["items"]


def load_published(path=PUBLISHED):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def mark_published(item_id, day, path=PUBLISHED):
    p = load_published(path)
    p[item_id] = day.isoformat()
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(p, ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8")


def _in_window(item, today):
    start = date.fromisoformat(item["valid_from"]) if item.get("valid_from") else date.min
    end = date.fromisoformat(item["valid_to"]) if item.get("valid_to") else date.max
    return start <= today <= end


def pick(items, published, today):
    """Next item for today: first in queue order that is in its date window and
    never posted; if every valid item was posted, the one posted longest ago,
    but only after REPEAT_AFTER_DAYS. None when nothing is due."""
    valid = [i for i in items if _in_window(i, today)]
    fresh = [i for i in valid if i["id"] not in published]
    if fresh:
        return fresh[0]
    old = [i for i in valid if (today - date.fromisoformat(published[i["id"]])).days >= REPEAT_AFTER_DAYS]
    return min(old, key=lambda i: published[i["id"]]) if old else None


# ---------------------------------------------------------------- text
def spoken(text):
    """Screen text -> what the voice should say. Rupee amounts, percent,
    links and helpline numbers are rewritten so the Hindi voice reads them
    the way a farmer would say them."""
    t = re.sub(r"taazabhav\.com[^\s,।]*", "ताज़ा भाव डॉट कॉम", text)
    t = re.sub(r"pmkisan\.gov\.in", "पीएम किसान डॉट जीओवी डॉट इन", t)
    t = re.sub(r"pmfby\.gov\.in", "पीएमएफबीवाई डॉट जीओवी डॉट इन", t)
    t = re.sub(r"(\d+)\s*:\s*(\d+)\s*:\s*(\d+)", r"\1, \2, \3", t)

    def phone(m):  # helplines read digit by digit
        return " ".join(re.sub(r"\D", "", m.group(0)))
    t = re.sub(r"\b1800-\d{3}-\d{4}\b|\b\d{5,6}\b(?![,\d])", phone, t)
    t = re.sub(r"₹\s*([\d,]+(?:\.\d+)?)", r"\1 रुपये", t)
    t = re.sub(r"(\d+(?:\.\d+)?)\s*%", r"\1 प्रतिशत", t)
    t = t.replace("/क्विंटल", " प्रति क्विंटल").replace("/किलो", " प्रति किलो")
    return re.sub(r"\s+", " ", t).strip()


def segments(item):
    return [item["hook_hi"], *item["points_hi"], item["cta_hi"]]


def short_link(item):
    return item["page"].replace("https://", "")


def link_for(item, src):
    # Owner, 19 Oct 2026: no UTM tags on links.
    return item["page"]


def metadata(item, today):
    title = item["title"][:100]
    asof = f"{date_hi(date.fromisoformat(item['checked_on']))} {item['checked_on'][:4]}"
    lines = [item["hook_hi"], ""] + [f"✅ {p}" for p in item["points_hi"]] + [
        "",
        f"पूरी जानकारी और हिसाब: {link_for(item, 'youtube')}",
        "",
        f"जानकारी {asof} तक की। योजनाओं की तारीखें और रेट बदल सकते हैं, आधिकारिक साइट या कृषि कार्यालय से पुष्टि करें।",
        "",
        "रोज़ का मंडी भाव और किसान अलर्ट: https://t.me/taazabhav",
        "#kisan #farmer #taazabhav #shorts",
    ]
    desc = "\n".join(lines)
    tags = ["kisan", "farmer", "taazabhav", "ताज़ा भाव", PILLAR.get(item["pillar"], ("", ""))[0]]
    eng = title.split("|")[-1].replace("#Shorts", "").strip()
    if eng:
        tags.append(eng)
    comment = f"{item['hook_hi']} पूरा हिसाब यहाँ: {link_for(item, 'youtube')}"
    return title, desc, [t for t in tags if t], comment


def meta_caption(item):
    pts = "\n".join(f"✅ {p}" for p in item["points_hi"])
    return (f"{item['hook_hi']}\n\n{pts}\n\n🌐 {short_link(item)} (लिंक बायो में)\n\n"
            "#kisan #farmer #kheti #taazabhav")


def telegram_text(item):
    pts = "\n".join(f"✅ {p}" for p in item["points_hi"])
    return f"❓ {item['hook_hi']}\n\n{pts}\n\n👉 {link_for(item, 'telegram')}"


# ---------------------------------------------------------------- media
def _duration(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                          "-of", "default=nw=1:nk=1", str(path)], capture_output=True, text=True, check=True)
    return float(out.stdout.strip())


def make_voice(texts, out_dir):
    """One mp3 per line (edge-tts), so each line appears on screen exactly
    when it is spoken. Returns [(file name, seconds)]."""
    import edge_tts
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    async def _go():
        for i, t in enumerate(texts):
            await edge_tts.Communicate(spoken(t), VOICE, rate="+5%").save(str(out_dir / f"line{i}.mp3"))
    asyncio.run(_go())
    return [(f"voice/line{i}.mp3", _duration(out_dir / f"line{i}.mp3")) for i in range(len(texts))]


def build_props(item, voice, today, clip=None, credit=None, fps=30):
    label, tone = PILLAR.get(item["pillar"], ("किसान सवाल", "gold"))
    lines, frame = [], 0
    for (text, (audio, secs)) in zip(segments(item), voice):
        n = max(1, round(secs * fps))
        lines.append({"text": text, "audio": audio, "from": frame, "frames": n})
        frame += n + round(0.15 * fps)  # small breath between lines
    asof = f"{date_hi(date.fromisoformat(item['checked_on']))} {item['checked_on'][:4]}"
    return {
        "clip": clip, "credit": credit, "label": label, "tone": tone,
        "lines": lines, "link": short_link(item),
        "asof": f"जानकारी {asof} तक की",
        "frames": frame + round(TAIL_SECONDS * fps),
    }


def render(props, out_path):
    shorts = Path("shorts")
    pub = shorts / "public"
    (pub / "fonts").mkdir(parents=True, exist_ok=True)
    for f in ("Baloo2-Bold.ttf", "IBMPlexMono-SemiBold.ttf"):
        (pub / "fonts" / f).write_bytes((Path("assets/fonts") / f).read_bytes())
    if props.get("clip"):
        (pub / "clip.mp4").write_bytes(Path(props["clip"]).read_bytes())
        props = {**props, "clip": "clip.mp4"}
    pf = (shorts / "props.json").resolve()
    pf.write_text(json.dumps(props, ensure_ascii=False), encoding="utf-8")
    cmd = ["npx", "remotion", "render", "src/Root.tsx", "SawalJawab", str(Path(out_path).resolve()),
           f"--props={pf}", "--log=error"]
    if os.environ.get("REMOTION_BROWSER_EXECUTABLE"):
        cmd.append(f"--browser-executable={os.environ['REMOTION_BROWSER_EXECUTABLE']}")
    subprocess.run(cmd, cwd=shorts, check=True, timeout=900)
    return out_path


# ---------------------------------------------------------------- telegram
def _tg(method, data, files=None):
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN not set")
    r = requests.post(f"https://api.telegram.org/bot{token}/{method}", data=data, files=files, timeout=120)
    if r.status_code != 200:
        raise RuntimeError(f"Telegram {method} HTTP {r.status_code}: {r.text[:300]}")


def send_preview(path, item, title):
    chat = os.environ.get("TELEGRAM_CHAT_ID")
    if not chat:
        raise RuntimeError("TELEGRAM_CHAT_ID not set")
    with open(path, "rb") as f:
        _tg("sendVideo", {"chat_id": chat, "caption": f"PREVIEW (not posted): {title}\nid: {item['id']}"[:1000]},
            files={"video": f})


def mode():
    """'publish' or 'preview'. Manual runs pass SAWAL_MODE; scheduled runs
    publish only once the owner sets the repo variable SAWAL_LIVE=1."""
    m = (os.environ.get("SAWAL_MODE") or "").strip().lower()
    if m in ("publish", "preview"):
        return m
    return "publish" if os.environ.get("SAWAL_LIVE", "").strip() == "1" else "preview"


# ---------------------------------------------------------------- run
def main():
    from notify import send_telegram_alert
    today = datetime.now(IST).date()
    item = pick(load_queue(), load_published(), today)
    if not item:
        send_telegram_alert("TaazaBhav: explainer queue is empty for today. Ask Claude for the next 30 scripts.")
        return 0
    run_mode = mode()
    print(f"[sawal] {today} {run_mode}: {item['id']}")
    out = "sawal.mp4"
    try:
        from fetch_clips import pick_clip, credit_for
        clip = pick_clip("generic", today, 20)
        c = credit_for(clip)
        credit = f"Video: {c['author']} / {c['source']}" if c else None
        voice = make_voice(segments(item), Path("shorts/public/voice"))
        render(build_props(item, voice, today, str(clip) if clip else None, credit), out)
        title, desc, tags, comment = metadata(item, today)
        if credit:
            desc = desc.replace("\n\nरोज़ का", f"\n{credit}\n\nरोज़ का", 1)
        if run_mode == "preview":
            send_preview(out, item, title)
            print("[sawal] preview sent to owner")
            return 0
        from upload_youtube import upload_video
        vid = upload_video(out, title, desc, tags, thumbnail_path=None, comment_text=comment)
        mark_published(item["id"], today)
        print(f"[sawal] uploaded https://youtu.be/{vid}")
        try:
            import meta_publish
            if meta_publish.enabled():
                res = meta_publish.publish_all(out, meta_caption(item))
                if res["errors"]:
                    send_telegram_alert("TaazaBhav ALERT: explainer Reel issue\n\n" + "\n".join(res["errors"]))
        except Exception as e:
            send_telegram_alert(f"TaazaBhav ALERT: explainer Reel failed\n\n{e}")
        try:
            _tg("sendMessage", {"chat_id": CHANNEL, "text": telegram_text(item), "disable_web_page_preview": "true"})
        except Exception as e:
            send_telegram_alert(f"TaazaBhav ALERT: explainer Telegram post failed\n\n{e}")
        return 0
    except Exception as e:
        traceback.print_exc()
        send_telegram_alert(f"TaazaBhav ALERT: explainer video failed ({item['id']})\n\n{e}")
        return 1
    finally:
        if os.path.exists(out):
            os.remove(out)


if __name__ == "__main__":
    sys.exit(main())
