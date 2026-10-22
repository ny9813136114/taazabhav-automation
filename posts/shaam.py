# -*- coding: utf-8 -*-
"""Shaam ka sawal: at 19:00 IST the Page asks one real question in its own
comment under the day's post, on Facebook and Instagram (TaazaBhav FB/IG
Content Engine plan, section 4). The answers (farmers' own mandi prices,
parchi deductions) feed Aapki Mandi Report (P1) and Parchi Doctor (P2).

Which post: the 14:30 bhav carousel when there is one (the question is about
today's prices); Wednesday's question is about the morning's Hisaab
Challenge and Sunday has no bhav post, so those two go under the 09:30 post.

Asli sawal only, never "comment YES" style bait (Meta cuts the reach of
engagement bait).

  preview (default): the question and the post it would go under go to the
  owner's Telegram only.
  publish (repo variable COMMENTS_LIVE=1): the Page comments on FB + IG.

python -m posts.shaam [preview|publish|dry] [YYYY-MM-DD]"""
import json
import os
import sys
from datetime import date, datetime
from pathlib import Path

from posts import ledger
from posts.run import IST, _owner, _tg, alert

STATE = Path("data/posts/shaam.json")
BHAV_STATE = Path("data/posts/bhav.json")
PILLAR_STATE = Path("data/posts/pillar.json")
DEFAULT_CROP = "सोयाबीन"


def mode():
    m = (sys.argv[1] if len(sys.argv) > 1 else "").strip()
    if m:
        return m
    return "publish" if os.environ.get("COMMENTS_LIVE", "").strip() == "1" else "preview"


def _read(path):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def lead_crop(day, bhav_state):
    """Hindi name of the first crop in today's bhav post (published or
    previewed), else soybean, the season's main sale."""
    for k in ("history", "preview"):
        for h in reversed(bhav_state.get(k, [])):
            if h.get("date") == day.isoformat() and h.get("lead"):
                return h["lead"]
    return DEFAULT_CROP


def challenge_today(day, led, pillar_state):
    d = day.isoformat()
    if any(x.get("date") == d and x.get("pillar") == "P6" for x in led):
        return True
    return any(h.get("date") == d and h.get("pillar") == "P6"
               for k in ("history", "preview") for h in pillar_state.get(k, []))


def question(day, crop, challenge):
    """The day's question (Mon=0 ... Sun=6)."""
    wd = day.weekday()
    if wd == 2 and challenge:
        return "आज सुबह के हिसाब चैलेंज का आपका जवाब क्या है? हिसाब भी लिखिए। सही जवाब कल सुबह की पोस्ट में।"
    return {
        0: "इस हफ्ते मंडी में कौन सी फसल बेचने ले जाएंगे, और किस भाव की उम्मीद है? फसल, मंडी और भाव लिखिए।",
        1: f"आज आपकी मंडी में {crop} किस भाव बिका? मंडी का नाम और भाव लिखिए, दूसरे किसान भाइयों के काम आएगा।",
        2: f"आज {crop} की बोली आपकी मंडी में कहाँ से कहाँ तक गई? मंडी का नाम और सबसे ऊंचा भाव लिखिए।",
        3: f"आज {crop} की बोली आपकी मंडी में कहाँ से कहाँ तक गई? मंडी का नाम और सबसे ऊंचा भाव लिखिए।",
        4: f"{crop} अभी रोकेंगे या बेचेंगे? अपनी वजह भी लिखिए: भाव, पैसे की ज़रूरत या रखने की जगह।",
        5: "पिछली बार मंडी की पर्ची में आढ़त, तुलाई और मंडी शुल्क मिलाकर कितना कटा? फसल, मंडी और कटौती लिखिए।",
        6: "अगले हफ्ते किस फसल के भाव या किस सरकारी योजना की जानकारी चाहिए? कमेंट में लिखिए।",
    }[wd]


def target(day, led):
    """Today's post the question goes under: (ledger entry, why) or (None, why)."""
    d = day.isoformat()
    today = [x for x in led if x.get("date") == d and x.get("format") == "photo" and (x.get("facebook") or x.get("instagram"))]
    by_slot = {x.get("slot"): x for x in today}
    order = ["09:30", "14:30"] if day.weekday() in (2, 6) else ["14:30", "09:30"]
    for slot in order:
        if slot in by_slot:
            return by_slot[slot], slot
    return None, "no photo post on the Page today"


def load_state():
    return _read(STATE) or {"history": [], "preview": []}


def save_state(state):
    STATE.parent.mkdir(parents=True, exist_ok=True)
    for k in ("history", "preview"):
        state[k] = state.get(k, [])[-60:]
    STATE.write_text(json.dumps(state, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


def main():
    run_mode = mode()
    day = date.fromisoformat(sys.argv[2]) if len(sys.argv) > 2 else datetime.now(IST).date()
    state = load_state()
    key = "history" if run_mode == "publish" else "preview"
    if run_mode != "dry" and any(h["date"] == day.isoformat() for h in state.get(key, [])):
        print(f"[shaam] {run_mode}: already done today")
        return 0
    led = ledger.load()
    q = question(day, lead_crop(day, _read(BHAV_STATE)), challenge_today(day, led, _read(PILLAR_STATE)))
    post, slot = target(day, led)
    print(f"[shaam] {run_mode}: {q}\n[shaam] under: {post.get('id') if post else slot}")
    if run_mode == "dry":
        return 0
    if run_mode == "preview":
        where = f"{slot} post ({post['id']}): https://www.facebook.com/{post['facebook']}" if post and post.get("facebook") else slot
        _tg("sendMessage", {"chat_id": _owner(), "disable_web_page_preview": "true",
                            "text": f"PREVIEW, shaam ka sawal (abhi post nahi hua)\n\nIs post ke neeche: {where}\n\nPage ka comment:\n{q}"})
        state.setdefault("preview", []).append({"date": day.isoformat(), "post": post.get("id") if post else None, "q": q})
        save_state(state)
        return 0
    if not post:
        alert(f"TaazaBhav shaam ka sawal ({day}): {slot}, no comment posted.")
        return 1
    import meta_publish as mp
    token, _ = mp.page_credentials()
    res, errors = {"date": day.isoformat(), "post": post["id"], "q": q}, []
    for net in ("facebook", "instagram"):
        if not post.get(net):
            continue
        try:
            res[net] = mp.post_comment(post[net], q, token)
        except Exception as e:
            errors.append(f"{net}: {e}")
    if res.get("facebook") or res.get("instagram"):
        state.setdefault("history", []).append(res)
        save_state(state)
    if errors:
        alert(f"TaazaBhav shaam ka sawal ({post['id']}):\n" + "\n".join(errors)[:500])
    print(f"[shaam] FB {res.get('facebook')} IG {res.get('instagram')}")
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
