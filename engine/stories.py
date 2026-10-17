# -*- coding: utf-8 -*-
"""Story pickers and scripts for the four series (execution blueprint,
17 Oct 2026, /mnt/project-files/strategy/youtube-execution-blueprint-2026-10-17.md).

Each builder turns the site feed into one Episode: a list of scenes (what
the screen shows + what the voice says), plus title, description, tags and
the comment to post. Every number comes from the feed; nothing is
estimated here. Builders return None when there is no honest story today.
"""
from datetime import date

from engine.text import day_hi, inr, link, pct_spoken, pct_text

# States most searched for mandi bhav; stories from these come first.
PRIORITY_STATES = ["Madhya Pradesh", "Rajasthan", "Maharashtra", "Uttar Pradesh", "Haryana", "Gujarat", "Punjab", "Karnataka"]

# Crop -> stock clip folder (assets/clips/<folder>).
CLIP = {
    "Onion": "onion", "Potato": "potato", "Tomato": "tomato", "Garlic": "garlic", "Soyabean": "soyabean",
    "Cotton": "cotton", "Maize": "maize", "Groundnut": "groundnut", "Wheat": "wheat", "Paddy(Common)": "paddy",
    "Mustard": "mustard", "Bajra(Pearl Millet/Cumbu)": "bajra", "Bengal Gram(Gram)(Whole)": "chana",
    "Green Gram(Moong)(Whole)": "moong", "Cummin Seed(Jeera)": "jeera",
}

# Short English names for titles ("Soybean Rate Today ...").
EN = {"Paddy(Common)": "Paddy", "Bajra(Pearl Millet/Cumbu)": "Bajra", "Bengal Gram(Gram)(Whole)": "Chana",
      "Green Gram(Moong)(Whole)": "Moong", "Cummin Seed(Jeera)": "Jeera", "Soyabean": "Soybean"}

# Month -> crops in arrival/sowing season get a bonus (Oct-Nov: kharif arrivals).
SEASON = {
    10: {"Soyabean", "Paddy(Common)", "Bajra(Pearl Millet/Cumbu)", "Maize", "Cotton", "Groundnut", "Onion", "Garlic", "Green Gram(Moong)(Whole)"},
    11: {"Soyabean", "Paddy(Common)", "Cotton", "Groundnut", "Onion", "Garlic", "Potato", "Maize"},
    12: {"Cotton", "Onion", "Potato", "Garlic", "Paddy(Common)", "Groundnut"},
    1: {"Cotton", "Onion", "Potato", "Garlic", "Tomato"},
    2: {"Mustard", "Bengal Gram(Gram)(Whole)", "Potato", "Onion", "Garlic", "Cummin Seed(Jeera)"},
    3: {"Wheat", "Mustard", "Bengal Gram(Gram)(Whole)", "Cummin Seed(Jeera)", "Garlic", "Onion"},
    4: {"Wheat", "Mustard", "Bengal Gram(Gram)(Whole)", "Onion"},
    5: {"Wheat", "Onion", "Green Gram(Moong)(Whole)"},
}

COMMENT_PROMPT = "कल किस मंडी का भाव चाहिए? कमेंट करें 👇"
DISCLAIMER = "यह भाव की जानकारी है, बेचने-रखने की सलाह नहीं। बेचने से पहले अपनी मंडी में भाव मिला लें।"


def _en(commodity):
    return EN.get(commodity, commodity)


def _reports(feed, kind, day=None):
    day = day or feed.get("latestDate")
    return [r for r in feed.get("reports", []) if r["kind"] == kind and r["date"] == day]


def _crop_report(feed, commodity):
    for r in _reports(feed, "crop"):
        if r["data"].get("commodity") == commodity:
            return r
    return None


def _signal(feed, commodity):
    for s in feed.get("signals", []):
        if s["commodity"] == commodity and s["date"] == feed.get("latestDate"):
            return s
    return None


def _state_rank(state):
    return PRIORITY_STATES.index(state) if state in PRIORITY_STATES else None


def _fit(title, tail=" #Shorts", limit=100):
    return title[: limit - len(tail)].rstrip(" |") + tail


# ====================================================================== A
def verdict(sig, crop, perishable):
    """(pos -1..1, short screen line, voice line, tone). Plain rules on the
    site's own sell signal (lib/sell-signal.ts); a description, not advice."""
    if not sig:
        return 0.0, "भाव मिलाकर बेचें", "बेचने से पहले पास की दो-तीन मंडियों का भाव मिला लें", "steady"
    wk = sig.get("pctWeek")
    if sig.get("belowMsp") and not perishable:
        return -0.65, "सरकारी खरीद भी देखें", f"आम भाव एमएसपी से नीचे है, सरकारी खरीद केंद्र का विकल्प भी देखें", "low"
    if sig["tone"] == "good":
        return 0.65, "बेचने का अच्छा मौका", f"भाव पिछले हफ़्ते से {pct_spoken(wk or 0)} प्रतिशत ऊपर है, बेचने का अच्छा मौका", "good"
    if sig["tone"] == "low":
        if perishable:
            return -0.2, "पास की बेहतर मंडी देखें", f"{crop} जल्दी खराब होता है, ज़्यादा न रोकें, पास की बेहतर मंडी देखें", "low"
        return -0.65, "जल्दबाज़ी न करें", "भाव पिछले हफ़्ते से नीचे है, रख सकते हैं तो जल्दबाज़ी न करें", "low"
    return 0.0, "भाव स्थिर, मंडी मिलाएँ", "भाव लगभग स्थिर है, पास की दो-तीन मंडियाँ मिलाकर बेचें", "steady"


def pick_a(feed, today, recent):
    """Biggest checked mandi move in a priority state (>= 8%), else the
    highest-paying priority-state mandi of a season crop. recent = keys
    already used in the last 7 days."""
    alert = (_reports(feed, "alert") or [None])[0]
    if not alert:
        return None
    season = SEASON.get(today.month, set())
    cands = []
    for kind, items in (("jump", alert["data"].get("jumps", [])), ("fall", alert["data"].get("falls", []))):
        for m in items:
            rank = _state_rank(m["state"])
            if rank is None or abs(m["pct"]) < 8 or m["modal"] <= 0:
                continue
            score = min(abs(m["pct"]), 60) + (15 if m["commodity"] in season else 0) + (8 - rank)
            cands.append((score, kind, m))
    for m in alert["data"].get("highs", []):
        rank = _state_rank(m["state"])
        if rank is None or m["modal"] <= 0:
            continue
        cands.append(((25 if m["commodity"] in season else 5) + (8 - rank), "high", m))
    cands.sort(key=lambda c: -c[0])
    used_crops = {k.split("|")[0] for k in recent if k}
    for prefer_new in (True, False):
        for score, kind, m in cands:
            key = f"{m['commodity']}|{m['market']}"
            if key in recent:
                continue
            if prefer_new and m["commodity"] in used_crops:
                continue
            return kind, m
    return None


def build_a(feed, today, recent):
    picked = pick_a(feed, today, recent)
    if not picked:
        return None
    kind, m = picked
    crop = m["nameHi"]
    rep = _crop_report(feed, m["commodity"])
    data = rep["data"] if rep else {}
    sig = _signal(feed, m["commodity"])
    perishable = bool(data.get("perishable"))
    mandi = m["marketHi"]
    up = kind == "jump" or (kind == "high")
    tone = "up" if up else "down"
    scenes = [
        {"kind": "number", "label": crop, "big": inr(m["modal"]), "count": m["modal"], "sub": f"{mandi} मंडी", "tone": tone,
         "say": f"{crop}, {m['modal']} रुपये क्विंटल!"},
    ]
    if kind in ("jump", "fall"):
        word = "ऊपर" if m["pct"] > 0 else "नीचे"
        scenes.append({"kind": "move", "big": pct_text(m["pct"]), "label": f"{mandi} मंडी", "sub": m["stateHi"], "tone": tone,
                       "say": f"{m['stateHi']} की {mandi} मंडी में, {day_hi(m['prevDate'])} से {pct_spoken(m['pct'])} प्रतिशत {word}"})
    else:
        scenes.append({"kind": "move", "big": "सबसे ऊँचा भाव", "label": f"{mandi} मंडी", "sub": m["stateHi"], "tone": "up",
                       "say": f"{m['stateHi']} की {mandi} मंडी में, आज {crop} का सबसे ऊँचा भाव"})
    if data.get("typical"):
        bars = [{"label": "देश का आम भाव", "value": data["typical"], "text": inr(data["typical"]), "tone": "steady"}]
        say = f"पर देश की मंडियों का आम भाव {data['typical']} रुपये"
        if data.get("msp"):
            below = data["typical"] < data["msp"]
            bars[0]["tone"] = "low" if below else "good"
            bars.append({"label": "MSP", "value": data["msp"], "text": inr(data["msp"]), "tone": "white"})
            say += f", एमएसपी {data['msp']} से {'नीचे' if below else 'ऊपर'}"
        scenes.append({"kind": "compare", "label": f"{crop}: देश भर में", "bars": bars, "say": say})
    pos, line, vsay, vtone = verdict(sig, crop, perishable)
    scenes.append({"kind": "meter", "label": "फ़ैसला", "pos": pos, "sub": line, "tone": vtone, "left": "रुकें", "right": "बेचें", "say": vsay})
    scenes.append({"kind": "cta", "label": "आपकी मंडी का भाव?", "big": "कमेंट करें 👇", "sub": "taazabhav.com", "say": "कल किस मंडी का भाव चाहिए? कमेंट में लिखें"})

    en = _en(m["commodity"])
    change = f" {pct_text(m['pct'])}" if kind != "high" else " सबसे ऊँचा"
    title = _fit(f"{inr(m['modal'])} {crop}! {mandi} मंडी{change} | {en} Rate Today {m['market']}")
    page = f"/mandi-bhav/{data.get('slug') or m['slug']}"
    desc = "\n".join([
        f"{day_hi(feed['latestDate'], True)}: {m['stateHi']} की {mandi} मंडी में {crop} {inr(m['modal'])} प्रति क्विंटल"
        + (f" ({pct_text(m['pct'], arrow=False)} {'ऊपर' if m['pct'] > 0 else 'नीचे'})" if kind != "high" else " (आज का सबसे ऊँचा भाव)") + "।",
        f"{crop} का आज का भाव, 900+ मंडियाँ: {link(page)}",
        f"{mandi} मंडी के सभी भाव: {link(m['path'])}",
        "",
        "स्रोत: Agmarknet / data.gov.in (सरकारी मंडी आँकड़े), ताज़ा भाव मंडी समाचार।",
        DISCLAIMER,
        "",
        "रोज़ सुबह 7:30 बजे भाव धमाका · Telegram: https://t.me/taazabhav",
        f"#मंडीभाव #{en.replace(' ', '')}Rate #{m['market'].replace(' ', '')}Mandi #kisan #taazabhav",
    ])
    return {
        "series": "A", "key": f"{m['commodity']}|{m['market']}", "clip": CLIP.get(m["commodity"], "generic"),
        "stamp": day_hi(feed["latestDate"]), "scenes": scenes, "title": title, "description": desc,
        "tags": [crop, f"{en} rate today", f"{m['market']} mandi bhav", "mandi bhav", "aaj ka mandi bhav", "taazabhav"],
        "comment": f"📍 {crop} का भाव, 900+ मंडियाँ: {link(page)}\n{COMMENT_PROMPT}",
        "playlist": "A", "link": link(page),
    }


# ====================================================================== B
SCHEME_DAY = {1: "mpkalyan", 4: "rajsamman"}  # Tue = MP, Fri = Rajasthan, other days PM Kisan


def _kist_label(k):
    last = k["last"]
    return str(last.get("n") or last.get("label"))


def build_b(feed, today, recent, claim=None):
    """claim: optional {'date': '2026-10-20', 'count': 5} from engine.claims
    (dates other YouTube videos are announcing for PM Kisan)."""
    kist = {k["key"]: k for k in feed.get("kist", [])}
    if not kist:
        return None
    # An official date not yet covered goes first, whatever the day.
    chosen, announced = None, False
    for k in kist.values():
        od = k["next"].get("officialDate")
        if od and f"{k['key']}|announced|{od}" not in recent and od >= today.isoformat():
            chosen, announced = k, True
            break
    if not chosen:
        chosen = kist.get(SCHEME_DAY.get(today.weekday(), "pmkisan")) or kist.get("pmkisan")
    k = chosen
    n = k["next"]["n"]
    name = k["nameHi"]
    last = k["last"]
    last_label = _kist_label(k)
    today_hi = day_hi(today)
    scenes = [{"kind": "headline", "label": name, "big": f"{n}वीं किस्त कब?", "sub": inr(k["amount"]),
               "tone": "white", "say": f"{name} की {n}वीं किस्त कब आएगी? सच सुनिए"}]
    if announced:
        od = k["next"]["officialDate"]
        scenes.append({"kind": "stamp", "label": "सरकारी घोषणा", "big": f"पक्का: {day_hi(od)}", "sub": f"{n}वीं किस्त, {inr(k['amount'])}", "tone": "good",
                       "say": f"सरकार ने घोषणा कर दी है, {n}वीं किस्त {day_hi(od)} को आएगी"})
        scenes.append({"kind": "timeline", "label": "पैसा न आए तो", "items": [
            {"label": "1", "value": "eKYC पूरा करें", "tone": "good"},
            {"label": "2", "value": "बैंक-आधार लिंक देखें", "tone": "good"},
            {"label": "3", "value": "स्टेटस चेक करें", "tone": "good"}],
            "say": "पैसा न आए तो ई-केवाईसी, बैंक से आधार लिंक और स्टेटस ज़रूर देखें"})
        key = f"{k['key']}|announced|{od}"
    else:
        if claim and k["key"] == "pmkisan":
            scenes.append({"kind": "claim", "label": "यूट्यूब पर चल रहा है", "big": f"{day_hi(claim['date'])}?", "sub": f"{claim['count']} वीडियो में यही तारीख",
                           "say": f"यूट्यूब पर {day_hi(claim['date'])} की तारीख चल रही है"})
        scenes.append({"kind": "stamp", "label": "सरकारी घोषणा", "big": "अभी नहीं ❌", "sub": f"{today_hi} तक कोई तारीख घोषित नहीं", "tone": "low",
                       "say": f"ताज़ा भाव के किस्त ट्रैकर के मुताबिक, {today_hi} तक सरकार ने कोई तारीख घोषित नहीं की"})
        window = k["next"].get("windowHi")
        items = [{"label": f"{last_label}वीं किस्त आई", "value": day_hi(last["date"], True), "tone": "good"},
                 {"label": f"{n}वीं किस्त", "value": f"{window} (संभावित)" if window else "तारीख घोषित नहीं", "tone": "steady"}]
        say = f"पिछली किस्त {day_hi(last['date'])} को आई थी" + (f", अगली {window} में संभावित" if window else "")
        scenes.append({"kind": "timeline", "label": "अब तक का हाल", "items": items, "say": say})
        key = f"{k['key']}|status|{today.isoformat()}"
    scenes.append({"kind": "cta", "label": "तारीख आते ही 🔔", "big": "किस्त घंटी लगाएँ", "sub": f"taazabhav.com{k['path']}",
                   "say": "तारीख घोषित होते ही ताज़ा भाव की किस्त घंटी आपको फ़ोन पर बताएगी, लिंक कमेंट में"})

    en_name = {"pmkisan": "PM Kisan", "mpkalyan": "MP Kisan Kalyan", "rajsamman": "Rajasthan Kisan Samman Nidhi"}[k["key"]]
    if announced:
        title = _fit(f"पक्का! {name} {n}वीं किस्त {day_hi(k['next']['officialDate'])} को | {en_name} {n}th Installment Date")
    elif claim and k["key"] == "pmkisan":
        title = _fit(f"{n}वीं किस्त {day_hi(claim['date'])} को? सच – {today_hi} | {en_name} {n}th Installment Date")
    else:
        title = _fit(f"{name} {n}वीं किस्त कब आएगी? सच – {today_hi} | {en_name} {n}th Installment Date")
    status = (f"सरकारी घोषणा: {n}वीं किस्त {day_hi(k['next']['officialDate'], True)} को।" if announced
              else f"{day_hi(today, True)} तक {n}वीं किस्त की कोई सरकारी तारीख घोषित नहीं हुई।")
    desc = "\n".join([
        status,
        f"पिछली ({last_label}वीं) किस्त: {day_hi(last['date'], True)}।",
        f"पूरी जानकारी, स्टेटस और पैसा न आए तो क्या करें: {link(k['path'])}",
        f"आधिकारिक साइट: {k['statusUrl']}",
        "",
        "हम सिर्फ़ सरकारी घोषणा बताते हैं, अंदाज़े वाली तारीख नहीं। तारीख घोषित होते ही किस्त घंटी फ़ोन पर बताएगी।",
        "Telegram: https://t.me/taazabhav",
        "#pmkisan #kist #किसान #taazabhav",
    ])
    return {
        "series": "B", "key": key, "clip": "generic", "stamp": today_hi, "stampTop": "किस्त ट्रैकर",
        "scenes": scenes, "title": title, "description": desc,
        "tags": [f"{en_name} {n}th installment", f"{en_name} installment date", "pm kisan", "kist kab aayegi", name, "taazabhav"],
        "comment": f"🔔 तारीख घोषित होते ही अलर्ट: {link(k['path'])}\nआपकी पिछली किस्त आई थी? कमेंट करें 👇",
        "playlist": "B", "link": link(k["path"]),
    }


# ====================================================================== C
def build_c(feed, today, recent):
    day = feed.get("latestDate")
    if not day:
        return None
    news = []
    teji = (_reports(feed, "teji-mandi") or [None])[0]
    if teji:
        d = teji["data"]
        movers = sorted(d.get("up", [])[:1] + d.get("down", [])[:1], key=lambda x: -abs(x["pct"]))
        if movers:
            m = movers[0]
            word = "चढ़ा" if m["pct"] > 0 else "गिरा"
            news.append({"label": m["nameHi"], "big": pct_text(m["pct"]), "tone": "up" if m["pct"] > 0 else "down",
                         "sub": f"आम भाव {inr(m['today'])}/क्विंटल",
                         "say": f"{m['nameHi']} का भाव {pct_spoken(m['pct'])} प्रतिशत {word}, आम भाव {m['today']} रुपये क्विंटल",
                         "path": teji["path"], "clip": CLIP.get(m["commodity"], "generic")})
    msp = (_reports(feed, "msp") or [None])[0]
    if msp:
        under = [i for i in msp["data"].get("items", []) if i["typical"] < i["msp"]]
        if under:
            names = ", ".join(i["nameHi"] for i in under[:3])
            news.append({"label": "MSP से नीचे", "big": f"{len(under)} फ़सलें", "count": None, "tone": "down", "sub": names,
                         "say": f"{names} का आम मंडी भाव एमएसपी से नीचे", "path": msp["path"]})
    kist = {k["key"]: k for k in feed.get("kist", [])}.get("pmkisan")
    if kist:
        n = kist["next"]["n"]
        od = kist["next"].get("officialDate")
        news.append({"label": f"पीएम किसान {n}वीं किस्त", "big": day_hi(od) if od else "तारीख नहीं", "tone": "good" if od else "steady",
                     "sub": "सरकारी घोषणा" if od else f"{day_hi(today)} तक घोषणा नहीं",
                     "say": f"पीएम किसान की {n}वीं किस्त {day_hi(od)} को आएगी" if od else f"पीएम किसान की {n}वीं किस्त की तारीख {day_hi(today)} तक घोषित नहीं",
                     "path": kist["path"]})
    if len(news) < 3:
        alert = (_reports(feed, "alert") or [None])[0]
        for h in (alert or {"data": {}})["data"].get("highs", []):
            if _state_rank(h["state"]) is not None:
                news.append({"label": f"{h['nameHi']}: सबसे ऊँचा", "big": inr(h["modal"]), "count": h["modal"], "tone": "up",
                             "sub": f"{h['marketHi']}, {h['stateHi']}",
                             "say": f"{h['nameHi']} का सबसे ऊँचा भाव {h['marketHi']} मंडी में, {h['modal']} रुपये", "path": h["path"]})
                break
    news = news[:3]
    if len(news) < 2:
        return None
    key = f"news|{day}"
    if key in recent:
        return None
    ord_ = ["पहली", "दूसरी", "तीसरी"]
    scenes = [{"kind": "headline", "label": f"किसान खबर · {day_hi(day)}", "big": f"आज की {len(news)} खबर", "tone": "white",
               "sub": "40 सेकंड में", "say": f"आज की {len(news)} बड़ी खबर, चालीस सेकंड में"}]
    for i, n in enumerate(news):
        scenes.append({"kind": "news", "n": i + 1, "of": len(news), "label": n["label"], "big": n["big"], "count": n.get("count"),
                       "sub": n["sub"], "tone": n["tone"], "say": f"{ord_[i]}: {n['say']}"})
    scenes.append({"kind": "cta", "label": "एक काम", "big": "2-3 मंडी मिलाएँ", "sub": "कल सुबह 7:30: भाव धमाका",
                   "say": "एक काम, बेचने से पहले पास की दो-तीन मंडियों का भाव मिलाएँ। कल सुबह साढ़े सात बजे, भाव धमाका"})
    heads = ", ".join(f"{n['label']} {n['big']}" for n in news[:2])
    title = _fit(f"किसान खबर {day_hi(day)}: {heads} | Kisan News Today")
    desc = "\n".join(
        [f"{day_hi(day, True)} की {len(news)} खबर:"]
        + [f"{i + 1}. {n['say']}। पूरी रिपोर्ट: {link(n['path'])}" for i, n in enumerate(news)]
        + ["", "स्रोत: Agmarknet / data.gov.in और ताज़ा भाव मंडी समाचार।", DISCLAIMER, "",
           "रोज़ शाम 6:30 बजे किसान खबर · Telegram: https://t.me/taazabhav", "#kisannews #mandibhav #किसान #taazabhav"])
    return {
        "series": "C", "key": key, "clip": news[0].get("clip", "generic"), "stamp": day_hi(day), "scenes": scenes,
        "title": title, "description": desc,
        "tags": ["kisan news", "kisan samachar", "mandi bhav today", "aaj ka mandi bhav", "pm kisan", "taazabhav"],
        "comment": f"📰 आज की पूरी मंडी समाचार: {link('/samachar')}\nआपके इलाके की कौन सी खबर चाहिए? कमेंट करें 👇",
        "playlist": "C", "link": link("/samachar"),
    }
