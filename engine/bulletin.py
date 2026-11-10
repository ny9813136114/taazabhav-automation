# -*- coding: utf-8 -*-
"""Series L "किसान बुलेटिन" (9 Nov 2026, owner "haan"): one 2-3 minute
landscape (16:9) news bulletin every morning at 08:00 IST, on YouTube as a
normal video (with chapters) and as a Facebook Page video.

Everything in it comes from taazabhav.com/api/yt-feed, the same numbers the
site shows, plus the deadline items of content/yojana/queue.json. At 08:00
the newest mandi report is usually yesterday's (prices land ~11:30 IST), so
the bulletin always names the report's date.

Segments, in order (a segment without honest data today is left out):
  intro      date + what is in today's bulletin
  bhav       national typical price of the main crops, with MSP
  chaal      the week's biggest moves (site sell signal, sanity-checked)
  msp        crops whose typical price is below MSP
  mandi      big searched mandis: latest price per mandi, with its date
  kist       PM Kisan / MP / Rajasthan: last paid kist, next date only if official
  tareekh    deadlines from the yojana queue that have not passed
  sawal      viewer question of the day (comment loop)
  outro      site link

No weather: the feed has no all-India forecast, and a made-up one is worse
than none (the site's Mera Khet card gives village weather).

Never repeats: one bulletin per date (key "bulletin|<date>"), and the data is
the day's own.
"""
import json
import os
import shutil
import subprocess
from datetime import date, timedelta
from pathlib import Path

from engine import media
from engine.stories import (CROP_ORDER, HI_NAME, MAX_WEEK_MOVE, SANE_RATIO, SANE_RATIO_PERISHABLE, SEASON,
                            _reports)
from engine.text import day_hi, inr, link, pct_spoken, pct_text

SERIES = "L"
NAME = "किसान बुलेटिन"
COLOR = "#0b6e4f"
MAX_DATA_AGE = 3      # days: an older mandi report is not news any more
MANDI_AGE = 3         # days between a mandi's price and the newest report
MIN_SECONDS, MAX_SECONDS = 60, 240
BHAV_ROWS = 8
MANDI_ROWS = 6
MOVE_MIN = 3.0        # % a week; smaller moves are "steady"
STATE_SHORT = {"Madhya Pradesh": "MP", "Rajasthan": "राज.", "Maharashtra": "महा.", "Uttar Pradesh": "UP",
               "Haryana": "हरि.", "Gujarat": "गुज.", "Punjab": "पंजाब", "Karnataka": "कर्ना."}
DISCLAIMER = "यह भाव और सरकारी जानकारी है, बेचने-रखने की सलाह नहीं। बेचने से पहले अपनी मंडी का भाव मिला लें।"


def _rel(day, today):
    gap = (today - date.fromisoformat(day)).days
    return "आज" if gap == 0 else "कल" if gap == 1 else day_hi(day)


def _hi(commodity, crops):
    return (crops.get(commodity) or {}).get("nameHi") or HI_NAME.get(commodity)


# ---------------------------------------------------------------- segments
def seg_bhav(feed, today):
    """National typical price of the main crops (season crops first)."""
    rows = []
    season = SEASON.get(today.month, set())
    for r in _reports(feed, "crop"):
        d = r["data"]
        if not d.get("typical") or d.get("typical") <= 0 or (d.get("markets") or 0) < 3:
            continue
        com = d.get("commodity")
        rank = CROP_ORDER.index(com) if com in CROP_ORDER else 99
        rows.append(((0 if com in season else 1), rank, d))
    rows.sort(key=lambda x: x[:2])
    rows = [d for _, _, d in rows][:BHAV_ROWS]
    if len(rows) < 4:
        return None
    day = feed["latestDate"]
    table = []
    for d in rows:
        msp = d.get("msp")
        if msp:
            tag, tone = ("MSP से नीचे", "low") if d["typical"] < msp else ("MSP से ऊपर", "good")
        else:
            tag, tone = "MSP नहीं", "white"
        table.append({"cells": [d["nameHi"], inr(d["typical"]), inr(msp) if msp else "—", str(d["markets"]), tag], "tone": tone})
    spoken_rows = ", ".join(f"{d['nameHi']} {inr(d['typical'])}" for d in rows[:5])
    return {
        "kind": "table", "chapter": "आज के भाव", "heading": "फ़सलों का आम भाव (₹/क्विंटल)",
        "sub": f"{day_hi(day, True)} की मंडी रिपोर्ट · Agmarknet (भारत सरकार)",
        "cols": ["फ़सल", "आम भाव", "MSP", "मंडियां", ""], "rows": table,
        "say": f"सबसे पहले भाव। {_rel(day, today)}, {day_hi(day)} की मंडी रिपोर्ट में देश का आम भाव, प्रति क्विंटल: "
               f"{spoken_rows}। बाकी फ़सलें स्क्रीन पर हैं।",
        "headline": f"{rows[0]['nameHi']} {inr(rows[0]['typical'])}",
    }


def seg_chaal(feed, today):
    """The week's moves from the site's sell signal; |move| over
    MAX_WEEK_MOVE is treated as a data glitch and left out."""
    crops = {r["data"]["commodity"]: r["data"] for r in _reports(feed, "crop")}
    moves, steady = [], []
    for s in feed.get("signals") or []:
        if s.get("date") != feed.get("latestDate") or s.get("pctWeek") is None:
            continue
        name = _hi(s["commodity"], crops)
        if not name:
            continue
        p = s["pctWeek"]
        if abs(p) > MAX_WEEK_MOVE:
            continue
        (moves if abs(p) >= MOVE_MIN else steady).append((name, p))
    if not moves:
        return None
    moves.sort(key=lambda x: -abs(x[1]))
    moves = moves[:4]
    cards = [{"label": n, "big": pct_text(p), "sub": "हफ़्ते भर में", "tone": "good" if p > 0 else "low"} for n, p in moves]
    said = ", ".join(f"{n} {pct_spoken(p)} प्रतिशत {'ऊपर' if p > 0 else 'नीचे'}" for n, p in moves)
    st = "、".join(n for n, _ in steady[:4]).replace("、", ", ")
    return {
        "kind": "cards", "chapter": "हफ़्ते की चाल", "heading": "हफ़्ते भर की चाल",
        "sub": f"पिछले हफ़्ते के आम भाव से तुलना" + (f" · स्थिर: {st}" if st else ""),
        "cards": cards,
        "say": f"अब हफ़्ते भर की चाल। पिछले हफ़्ते के मुकाबले {said}।" + (f" {st} के भाव लगभग स्थिर रहे।" if st else "")
               + " सब्ज़ी जल्दी खराब होती है, इसलिए गिरते भाव में भी ज़्यादा दिन न रोकें।" * any(p < 0 for _, p in moves),
        "headline": f"{moves[0][0]} {pct_text(moves[0][1])}",
    }


def seg_msp(feed, today):
    rep = next(iter(_reports(feed, "msp")), None)
    items = [i for i in ((rep or {}).get("data") or {}).get("items", []) if i.get("msp") and i.get("typical") and (i.get("markets") or 0) >= 3]
    if not items:
        return None
    items = items[:4]
    cards = [{"label": i["nameHi"], "big": inr(i["typical"]), "sub": f"MSP {inr(i['msp'])}", "tone": "low"} for i in items]
    said = ", ".join(f"{i['nameHi']} का आम भाव {inr(i['typical'])}, जबकि एमएसपी {inr(i['msp'])}" for i in items[:3])
    return {
        "kind": "cards", "chapter": "MSP से नीचे", "heading": "MSP से नीचे बिक रही फ़सलें",
        "sub": "सरकारी खरीद केंद्र का विकल्प भी देखें · taazabhav.com/msp-vs-mandi", "cards": cards,
        "say": f"अब वो फ़सलें जिनका आम भाव एमएसपी से नीचे है। {said}। "
               "इन फ़सलों के लिए सरकारी खरीद केंद्र का विकल्प भी देखें।",
        "headline": f"{items[0]['nameHi']} MSP से नीचे",
    }


def seg_mandi(feed, today):
    """One row per searched mandi: its newest sane price within MANDI_AGE
    days of the newest report, season crops first."""
    latest = date.fromisoformat(feed["latestDate"])
    season = SEASON.get(today.month, set())
    typical = {r["data"]["commodity"]: r["data"] for r in _reports(feed, "crop")}
    rows = []
    for m in feed.get("mandis") or []:
        best = None
        for c in m.get("crops") or []:
            com = c.get("commodity")
            if com not in HI_NAME or (c.get("modal") or 0) <= 0:
                continue
            if (latest - date.fromisoformat(c["date"])).days > MANDI_AGE:
                continue
            nat = typical.get(com, {})
            lo, hi = SANE_RATIO_PERISHABLE if nat.get("perishable") else SANE_RATIO
            if nat.get("typical") and not lo <= c["modal"] / nat["typical"] <= hi:
                continue
            k = (0 if com in season else 1, -date.fromisoformat(c["date"]).toordinal(), CROP_ORDER.index(com) if com in CROP_ORDER else 99)
            if best is None or k < best[0]:
                best = (k, c)
        if best:
            c = best[1]
            rows.append({"mandi": m.get("marketHi") or m["market"], "state": STATE_SHORT.get(m.get("state"), m.get("state", "")),
                         "crop": HI_NAME[c["commodity"]], "modal": c["modal"], "date": c["date"]})
    rows = rows[:MANDI_ROWS]
    if len(rows) < 3:
        return None
    said = ", ".join(f"{r['mandi']} में {r['crop']} {inr(r['modal'])}" for r in rows[:4])
    return {
        "kind": "table", "chapter": "बड़ी मंडियां", "heading": "बड़ी मंडियों का ताज़ा भाव (₹/क्विंटल)",
        "sub": "हर मंडी की सबसे नई रिपोर्ट · तारीख साथ में",
        "cols": ["मंडी", "राज्य", "फ़सल", "भाव", "तारीख"],
        "rows": [{"cells": [r["mandi"], r["state"], r["crop"], inr(r["modal"]), day_hi(r["date"])], "tone": "white"} for r in rows],
        "say": f"अब बड़ी मंडियां, हर मंडी की सबसे नई रिपोर्ट से: {said}। तारीख स्क्रीन पर है।",
        "headline": f"{rows[0]['mandi']} {rows[0]['crop']} {inr(rows[0]['modal'])}",
    }


def seg_kist(feed, today):
    """Last paid kist (official) and, only when officially announced, the next date."""
    cards, said = [], []
    for k in feed.get("kist") or []:
        last, nxt = k.get("last") or {}, k.get("next") or {}
        if not last.get("date"):
            continue
        n = last.get("n") or last.get("label")
        name = k["nameHi"] if k["key"] == "pmkisan" else f"{k.get('stateHi', '')} {k['nameHi'].replace('मुख्यमंत्री ', 'CM ')}"
        if nxt.get("officialDate"):
            big, tone = day_hi(nxt["officialDate"]), "good"
            nxt_say = f"अगली {nxt.get('n')}वीं किस्त की सरकारी तारीख {day_hi(nxt['officialDate'], True)} है"
        else:
            big, tone = "तारीख घोषित नहीं", "gold"
            nxt_say = "अगली किस्त की सरकारी तारीख अभी घोषित नहीं हुई"
        cards.append({"label": name[:26], "big": big, "sub": f"पिछली ({n}): {day_hi(last['date'])}", "tone": tone})
        said.append(f"{name}: पिछली किस्त {day_hi(last['date'])} को आई थी, {nxt_say}")
    if not cards:
        return None
    return {
        "kind": "cards", "chapter": "किस्त अपडेट", "heading": "किस्त अपडेट",
        "sub": "सिर्फ़ सरकारी तारीख · बाकी तारीखें अफ़वाह · taazabhav.com/pm-kisan-kist", "cards": cards[:3],
        "say": "अब किस्त अपडेट। " + "। ".join(said[:3]) + "। सोशल मीडिया पर चल रही दूसरी तारीखों पर भरोसा न करें।",
        "headline": "किस्त अपडेट",
    }


def seg_tareekh(today, items):
    rows = []
    for it in items:
        d = it.get("deadline")
        if not d or d < today.isoformat() or (it.get("validFrom") or "0000") > today.isoformat():
            continue
        days = (date.fromisoformat(d) - today).days
        rows.append((d, it["hook"]["label"], days, it.get("source", "")))
    rows.sort()
    rows = rows[:3]
    if not rows:
        return None
    cards = [{"label": lab, "big": day_hi(d), "sub": f"{days} दिन बाकी", "tone": "low" if days <= 7 else "gold"} for d, lab, days, _ in rows]
    said = ", ".join(f"{lab}: {day_hi(d)}, यानी {days} दिन बाकी" for d, lab, days, _ in rows)
    return {
        "kind": "cards", "chapter": "ज़रूरी तारीखें", "heading": "ज़रूरी तारीखें",
        "sub": "स्रोत: " + ", ".join(sorted({s for *_, s in rows if s})), "cards": cards,
        "say": f"अब ज़रूरी तारीखें। {said}।",
        "headline": f"{rows[0][1]} {day_hi(rows[0][0])}",
    }


def question_crop(bhav, today):
    """The day's question crop rotates over the crops in today's table."""
    names = [r["cells"][0] for r in (bhav or {}).get("rows", [])][:5] or ["धान"]
    return names[today.toordinal() % len(names)]


def seg_sawal(crop):
    return {
        "kind": "question", "chapter": "आज का सवाल", "heading": "आज का सवाल",
        "big": f"आपकी मंडी में {crop} का भाव?", "options": ["मंडी का नाम + भाव लिखें", "बेचेंगे = 1", "रोकेंगे = 2"],
        "say": f"अब आज का सवाल। आपकी मंडी में {crop} का भाव क्या रहा? कमेंट में अपनी मंडी का नाम और भाव लिखिए। "
               "और बताइए, आप अभी बेचेंगे तो एक लिखिए, रोकेंगे तो दो। आपके जवाब कल के बुलेटिन में।",
    }


def seg_intro(today, segs):
    agenda = [s["chapter"] for s in segs]
    return {
        "kind": "intro", "chapter": "शुरुआत", "heading": NAME, "big": day_hi(today, True),
        "items": agenda,
        "say": f"राम राम किसान भाइयो, ताज़ा भाव के किसान बुलेटिन में आपका स्वागत है। आज {day_hi(today)} है। "
               f"आज के बुलेटिन में: {', '.join(agenda)}।",
    }


def seg_outro():
    return {
        "kind": "outro", "chapter": "पूरी जानकारी", "heading": "हर मंडी का पूरा भाव", "big": "taazabhav.com",
        "items": ["3,000+ मंडियों के भाव", "किस्त ट्रैकर", "MSP बनाम मंडी", "मुफ़्त किसान टूल"],
        "say": "हर मंडी का पूरा भाव, किस्त ट्रैकर और मुफ़्त किसान टूल taazabhav.com पर। "
               "बुलेटिन काम का लगा तो चैनल सब्सक्राइब करें। कल सुबह आठ बजे फिर मिलेंगे। राम राम।",
    }


# ---------------------------------------------------------------- episode
def build_l(feed, today, recent, items=()):
    key = f"bulletin|{today.isoformat()}"
    if key in recent or not feed.get("latestDate"):
        return None
    if (today - date.fromisoformat(feed["latestDate"])).days > MAX_DATA_AGE:
        return None  # no fresh mandi report: a bulletin of old prices is not news
    bhav = seg_bhav(feed, today)
    if not bhav:
        return None
    body = [s for s in (bhav, seg_chaal(feed, today), seg_msp(feed, today), seg_mandi(feed, today),
                        seg_kist(feed, today), seg_tareekh(today, items)) if s]
    segs = [seg_intro(today, body)] + body + [seg_sawal(question_crop(bhav, today)), seg_outro()]
    heads = [s["headline"] for s in body if s.get("headline")]
    title = f"किसान बुलेटिन {day_hi(today, True)}: " + ", ".join(heads[:2])
    title = (title[:76].rstrip(" ,") if len(title) > 76 else title) + " | Mandi Bhav News"
    crop = segs[-2]["big"]
    return {
        "series": SERIES, "key": key, "segments": segs, "title": title, "link": link("/"),
        "tags": ["kisan bulletin", "mandi bhav", "mandi bhav today", "aaj ka mandi bhav", "kisan news", "pm kisan",
                 "msp", "किसान बुलेटिन", "मंडी भाव", "taazabhav"],
        "comment": f"{crop} कमेंट में अपनी मंडी का नाम और भाव लिखें 👇 बेचेंगे = 1, रोकेंगे = 2",
        "dataDate": feed["latestDate"],
    }


def chapters(props):
    out = []
    for s in props["segments"]:
        t = int(s["from"] / media.FPS)
        out.append(f"{t // 60}:{t % 60:02d} {s['chapter']}")
    return out


def description(ep, props):
    lines = [
        f"किसान बुलेटिन, {day_hi(date.fromisoformat(ep['key'].split('|')[1]), True)}: आज के मंडी भाव, हफ़्ते की चाल, "
        "MSP से नीचे की फ़सलें, किस्त अपडेट और ज़रूरी तारीखें। हर सुबह 8 बजे।",
        "",
        "अध्याय:", *chapters(props), "",
        f"हर मंडी का भाव: {link('/mandi-bhav')}",
        f"MSP बनाम मंडी: {link('/msp-vs-mandi')}",
        f"PM Kisan किस्त ट्रैकर: {link('/pm-kisan-kist')}",
        f"सरकारी पैसा कैलेंडर: {link('/sarkari-paisa')}",
        "",
        f"स्रोत: Agmarknet (भारत सरकार) की {day_hi(ep['dataDate'], True)} की मंडी रिपोर्ट, PIB, सरकारी पोर्टल।",
        DISCLAIMER, "",
        "#किसानबुलेटिन #मंडीभाव #mandibhav #kisannews #taazabhav",
    ]
    return "\n".join(lines)[:4900]


def build_props(ep, voice):
    segs, frame = [], 0
    for s, v in zip(ep["segments"], voice):
        n = round((v["secs"] + 0.7) * media.FPS)
        sc = {k: val for k, val in s.items() if k != "say"}
        sc.update({"from": frame, "frames": n, "audio": v["audio"],
                   "words": [{"w": w["w"], "from": frame + round(w["t"] * media.FPS)} for w in v["words"]]})
        segs.append(sc)
        frame += n
    return {"name": NAME, "color": COLOR, "dateHi": day_hi(date.fromisoformat(ep["key"].split("|")[1]), True),
            "segments": segs, "frames": frame}


def thumb_props(ep):
    body = [s for s in ep["segments"] if s.get("headline")]
    return {"name": NAME, "color": COLOR, "dateHi": day_hi(date.fromisoformat(ep["key"].split("|")[1]), True),
            "lines": [s["headline"] for s in body[:3]]}


def _remotion(args, props):
    for f in ("Baloo2-Bold.ttf", "IBMPlexMono-SemiBold.ttf"):
        (media.PUBLIC / "fonts").mkdir(parents=True, exist_ok=True)
        shutil.copyfile(Path("assets/fonts") / f, media.PUBLIC / "fonts" / f)
    pf = (media.SHORTS / "props.json").resolve()
    pf.write_text(json.dumps(props, ensure_ascii=False), encoding="utf-8")
    cmd = ["npx", "remotion", *args, f"--props={pf}", "--log=error"]
    if os.environ.get("REMOTION_BROWSER_EXECUTABLE"):
        cmd.append(f"--browser-executable={os.environ['REMOTION_BROWSER_EXECUTABLE']}")
    subprocess.run(cmd, cwd=media.SHORTS, check=True, timeout=2400)


def render(props, out_path):
    _remotion(["render", "src/Root.tsx", "Bulletin", str(Path(out_path).resolve()), "--crf=26"], props)
    return out_path


def render_thumb(ep, out_path):
    _remotion(["still", "src/Root.tsx", "BulletinThumb", str(Path(out_path).resolve()), "--image-format=jpeg"], thumb_props(ep))
    return out_path


def preview_copy(path, limit_mb=48):
    """Telegram bots may send at most 50 MB; a bigger render is shrunk for the preview only."""
    p = Path(path)
    if p.stat().st_size < limit_mb * 1024 * 1024:
        return p
    small = p.with_name(p.stem + "-preview.mp4")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(p), "-vf", "scale=1280:-2", "-c:v", "libx264", "-crf", "32",
                    "-preset", "veryfast", "-c:a", "aac", "-b:a", "64k", str(small)], check=True)
    return small
