# -*- coding: utf-8 -*-
"""09:30 IST pillar post on the Facebook Page + Instagram (TaazaBhav FB/IG
Content Engine plan, sections 3-5).

The day's pillar comes from content/calendar/<YYYY-MM>.json (built from the
website's own tool code by ops/build_calendar.ts). Static days carry the
whole post; dynamic days are built here from taazabhav.com/api/yt-feed:

  P1  Aapki Mandi Report: one state's lowest-to-highest price for a crop today
  P3-hold  Kisan ka Hisaab: what holding a crop for 2 months costs, today's price
  P4  Rokun ya Bechun: each crop's 7-day price move (data, not advice)
  P7  Khet Alarm: frost risk at farm hubs in the next nights; takes the slot
      over from any pillar when it fires (site's /api/khet-weather + pala rules)

Every post passes the no-repeat ledger (posts/ledger.py). If the day's post
can't be built or is blocked, the old tool carousel posts instead.

  preview (default): the pillar post goes to the owner's Telegram only, and
  the old tool carousel runs as before (POSTS_LIVE).
  publish (repo variable PILLAR_LIVE=1): the pillar post replaces the tool
  carousel on FB + IG.

python -m posts.pillar [preview|publish|dry] [YYYY-MM-DD]"""
import json
import os
import sys
import traceback
from datetime import date, datetime, timedelta
from pathlib import Path

import requests

from posts import ledger
from posts.run import IST, alert, publish, send_preview, share_kit

CAL_DIR = Path("content/calendar")
STATE = Path("data/posts/pillar.json")
SITE = "https://taazabhav.com"
TAGS = "#किसान #kisan #taazabhav #ताज़ाभाव"
HI_MONTHS = ["जनवरी", "फ़रवरी", "मार्च", "अप्रैल", "मई", "जून", "जुलाई", "अगस्त", "सितंबर", "अक्टूबर", "नवंबर", "दिसंबर"]
STATE_HI = {"madhya-pradesh": "मध्य प्रदेश", "rajasthan": "राजस्थान", "maharashtra": "महाराष्ट्र", "uttar-pradesh": "उत्तर प्रदेश",
            "gujarat": "गुजरात", "haryana": "हरियाणा", "punjab": "पंजाब", "karnataka": "कर्नाटक"}
# Frost watch points: wheat-mustard-potato belts of the north and centre.
HUBS = [("लुधियाना", "punjab", 30.9, 75.85), ("हिसार", "haryana", 29.15, 75.72), ("श्रीगंगानगर", "rajasthan", 29.9, 73.88),
        ("जयपुर", "rajasthan", 26.9, 75.8), ("ग्वालियर", "madhya-pradesh", 26.2, 78.18), ("आगरा", "uttar-pradesh", 27.18, 78.0),
        ("बरेली", "uttar-pradesh", 28.37, 79.43), ("भोपाल", "madhya-pradesh", 23.26, 77.41)]
MIN_MARKETS = 5


def mode():
    m = (sys.argv[1] if len(sys.argv) > 1 else "").strip()
    if m:
        return m
    return "publish" if os.environ.get("PILLAR_LIVE", "").strip() == "1" else "preview"


def hi_date(d):
    d = date.fromisoformat(d) if isinstance(d, str) else d
    return f"{d.day} {HI_MONTHS[d.month - 1]}"


def rs(n):
    from posts.bhav import rs as _rs
    return _rs(n)


def calendar(day):
    try:
        cal = json.loads((CAL_DIR / f"{day:%Y-%m}.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None, None
    plan = next((d for d in cal["days"] if d["date"] == day.isoformat()), None)
    return cal, plan


def make_post(pid, path, slides, lines, ask, group, trust, meta):
    link = f"taazabhav.com{path}"
    slides = slides + [{"kind": "cta", "big": "मुफ़्त टूल, हिंदी में", "url": link}]
    caption = "\n".join(lines + ["", ask, "", f"पूरा हिसाब: {link} (लिंक बायो में)", "", TAGS])[:2200]
    return {"id": pid, "path": path, "slides": slides, "caption": caption, "group": f"{group}\nhttps://{link}",
            "trust": trust, "link": f"https://{link}", "ask": ask, "meta": meta}


def feed_trust(day):
    return f"स्रोत: मंडी भाव, Agmarknet / data.gov.in · जाँच: {hi_date(day)} {day.year}"


# ---------------------------------------------------------------- P1
def state_report(feed, state, day):
    return next((r["data"] for r in feed.get("reports", []) if r.get("kind") == "state" and r.get("date") == day.isoformat()
                 and r["data"].get("stateSlug") == state), None)


def build_p1(feed, day, args, led):
    """Lowest-to-highest price today for the state's main crop (the bhav
    post's crop order), skipping crops the ledger has used lately."""
    from posts.bhav import PRIORITY
    order = [args.get("state")] + [s for s in ledger.STATES if s != args.get("state")]
    for st in order:
        rep = state_report(feed, st, day)
        if not rep:
            continue
        crops = [c for c in rep.get("crops", []) if c.get("markets", 0) >= MIN_MARKETS and c.get("hi") and c.get("lo")]
        rank = {k: i for i, k in enumerate(PRIORITY)}
        crops.sort(key=lambda c: (rank.get(c["slug"], len(rank)), -c["markets"]))
        for c in crops:
            meta = {"crop": c["slug"], "state": st, "angle": f"spread-{day.isoformat()}"}
            e = entry_for(day, "P1", f"p1-{st}-{c['slug']}-{day.isoformat()}", meta, "")
            if not ledger.problems(e, led, day, ("hook",)):
                return p1_post(rep, c, st, day, feed)
    return None


def p1_post(rep, c, st, day, feed):
    gap = c["hi"] - c["lo"]
    crop_rep = next((r["data"] for r in feed.get("reports", []) if r.get("kind") == "crop" and r.get("date") == day.isoformat()
                     and r["data"].get("slug") == c["slug"]), {})
    top = [t for t in crop_rep.get("top", []) if t.get("state") == rep["state"]][:3]
    rows = [["सबसे ऊंचा भाव", rs(c["hi"])], ["आम भाव", rs(c["typical"])], ["सबसे कम भाव", rs(c["lo"])]]
    rows += [[f"{t['marketHi']} मंडी", rs(t["modal"])] for t in top]
    msp = c.get("msp")
    slides = [
        {"kind": "hook", "label": f"आपकी मंडी रिपोर्ट · {rep['stateHi']} · {hi_date(day)}",
         "big": f"{c['nameHi']}: {rs(c['lo'])} से {rs(c['hi'])}", "sub": f"एक ही दिन, {c['markets']} मंडियां, {rs(gap)} का फ़र्क"},
        {"kind": "table", "title": f"{rep['stateHi']} में आज {c['nameHi']} (₹/क्विंटल)", "rows": rows,
         **({"total": ["MSP", rs(msp)]} if msp else {}), "note": "मॉडल भाव, मंडी रिपोर्ट से"},
        {"kind": "list", "title": "बेचने से पहले", "items": ["पास की 2-3 मंडी का भाव मिलाएं", "भाड़ा जोड़कर देखें, दूर की मंडी हमेशा फ़ायदे की नहीं",
                                                               "आपकी मंडी का भाव कमेंट करें, अगले शनिवार की रिपोर्ट में आएगा"]},
    ]
    lines = [f"{rep['stateHi']} में आज ({hi_date(day)}) {c['nameHi']} का भाव {rs(c['lo'])} से {rs(c['hi'])} प्रति क्विंटल रहा।",
             f"{c['markets']} मंडियों में आम भाव {rs(c['typical'])}; सबसे ऊंचे और सबसे कम भाव में {rs(gap)} का फ़र्क।"]
    lines += [f"• {t['marketHi']}: {rs(t['modal'])}" for t in top]
    path = f"/mandi-bhav/{c['slug']}/{st}"
    return make_post(f"p1-{st}-{c['slug']}-{day.isoformat()}", path, slides, lines,
                     f"आपकी मंडी में आज {c['nameHi']} कितने में बिका? मंडी का नाम और भाव कमेंट करें।",
                     f"{rep['stateHi']} में आज {c['nameHi']} {rs(c['lo'])} से {rs(c['hi'])}। अपनी मंडी का भाव देखें 👇",
                     feed_trust(day), {"crop": c["slug"], "state": st, "angle": f"spread-{day.isoformat()}"})


# ---------------------------------------------------------------- P3 hold
def hold_or_sell(qtl, price_now, months, storage, interest, loss_pct):
    """Same maths as the site's lib/hold-or-sell.ts (no bonus, no later price)."""
    loss = min(max(loss_pct, 0), 50) / 100
    sell_now = qtl * price_now
    storage_cost = qtl * storage * months
    interest_cost = sell_now * interest * months / 1200
    qtl_later = qtl * (1 - loss)
    break_even = (sell_now + storage_cost + interest_cost) / qtl_later
    net_flat = qtl_later * price_now - storage_cost - interest_cost
    return {"sellNow": round(sell_now), "storageCost": round(storage_cost), "interestCost": round(interest_cost),
            "qtlLater": round(qtl_later * 100) / 100, "breakEven": round(break_even),
            "risePerMonth": round((break_even - price_now) / months), "costIfFlat": round(sell_now - net_flat)}


def build_p3_hold(feed, day, args, cal):
    st, crop, qtl = args["state"], args["crop"], args["qtl"]
    rep = state_report(feed, st, day)
    c = next((x for x in (rep or {}).get("crops", []) if x["slug"] == crop and x.get("markets", 0) >= 3), None)
    if not c:
        return None
    h = cal["site"]["hold"]
    r = hold_or_sell(qtl, c["typical"], h["months"], h["storagePerQtlMonth"], h["interestPctYear"], h["lossPct"])
    m = h["months"]
    slides = [
        {"kind": "hook", "label": f"किसान का हिसाब · {rep['stateHi']}", "big": f"{qtl} क्विंटल {c['nameHi']} {m} महीने रोकी: {rs(r['costIfFlat'])} ख़र्च",
         "sub": f"भाव {rs(r['breakEven'])} से ऊपर गया, तभी फ़ायदा"},
        {"kind": "table", "title": f"आज का आम भाव {rs(c['typical'])} ({c['markets']} मंडी)", "rows": [
            ["आज बेचें तो", rs(r["sellNow"])], [f"गोदाम किराया ({rs(h['storagePerQtlMonth'])}/क्विंटल/महीना)", rs(r["storageCost"])],
            [f"ब्याज ({h['interestPctYear']}% सालाना)", rs(r["interestCost"])], [f"सूखत/नुकसान ({h['lossPct']}%)", f"{r['qtlLater']} क्विंटल बचे"]],
         "total": ["बराबरी का भाव", rs(r["breakEven"])]},
        {"kind": "answer", "label": "हर महीने भाव कितना बढ़े", "big": f"+{rs(r['risePerMonth'])}", "sub": "तब जाकर रोकना बराबर पड़ेगा"},
    ]
    lines = [f"{rep['stateHi']} का उदाहरण: {qtl} क्विंटल {c['nameHi']}, आज का आम भाव {rs(c['typical'])} ({hi_date(day)})।",
             f"{m} महीने रोकने का ख़र्च (भाव न बढ़े तो): {rs(r['costIfFlat'])}।",
             f"फ़ायदा तभी जब भाव {rs(r['breakEven'])} से ऊपर जाए, यानी हर महीने करीब {rs(r['risePerMonth'])} की बढ़त।",
             f"(गोदाम {rs(h['storagePerQtlMonth'])}/क्विंटल/महीना, ब्याज {h['interestPctYear']}%, सूखत {h['lossPct']}%; अपने आंकड़े टूल में डालें।)"]
    bh = cal["site"].get("bhavantar") or {}
    if crop == "soybean" and st == "madhya-pradesh" and bh and bh["saleStart"] <= day.isoformat() <= bh["saleEnd"]:
        lines.append(f"मप्र में भावांतर की बिक्री {hi_date(bh['saleEnd'])} {bh['saleEnd'][:4]} तक; उसके बाद बेचने पर भावांतर नहीं।")
    return make_post(f"p3-hold-{crop}-{st}-{day.isoformat()}", "/rokun-ya-bechun", slides, lines,
                     f"आप {c['nameHi']} रोक रहे हैं या बेच दी? कितने भाव का इंतज़ार है? कमेंट में लिखें।",
                     f"{qtl} क्विंटल {c['nameHi']} {m} महीने रोकने का ख़र्च {rs(r['costIfFlat'])}। अपना हिसाब 👇",
                     f"स्रोत: आज का मंडी भाव + रोकूं या बेचूं टूल का हिसाब · जाँच: {hi_date(day)} {day.year}",
                     {"tool": "rokun", "crop": crop, "state": st, "angle": f"hold-{day:%Y-%m}"})


# ---------------------------------------------------------------- P4
def crop_names(feed):
    names = {}
    for r in feed.get("reports", []):
        d = r.get("data", {})
        if r.get("kind") == "crop" and d.get("slug"):
            names[d["slug"]] = d.get("nameHi")
        for c in d.get("crops", []) + d.get("items", []):
            if c.get("slug") and c.get("nameHi"):
                names.setdefault(c["slug"], c["nameHi"])
    return names


def build_p4(feed, day):
    names = crop_names(feed)
    sig = [s for s in feed.get("signals", []) if s.get("date") == day.isoformat() and names.get(s["slug"]) and s.get("pctWeek") is not None]
    if len(sig) < 4:
        return None
    sig.sort(key=lambda s: -abs(s["pctWeek"]))
    # Lead with a crop farmers store (a vegetable swing says little about
    # holding), unless every stored crop is flat.
    stored = [s for s in sig if not s.get("perishable")]
    lead = stored[0] if stored and abs(stored[0]["pctWeek"]) >= 2 else sig[0]
    arrow = lambda p: f"{'▲' if p > 0 else '▼' if p < 0 else '='} {abs(p):.0f}%"
    rows = [[names[s["slug"]] + (" (MSP से नीचे)" if s.get("belowMsp") else ""), arrow(s["pctWeek"])] for s in sig[:6]]
    up = [names[s["slug"]] for s in sig if s["pctWeek"] >= 3]
    down = [names[s["slug"]] for s in sig if s["pctWeek"] <= -3]
    slides = [
        {"kind": "hook", "label": f"रोकूं या बेचूं · {hi_date(day)}", "big": f"{names[lead['slug']]} 7 दिन में {arrow(lead['pctWeek'])}",
         "sub": "हर फसल का हफ़्ते भर का रुख़ →"},
        {"kind": "table", "title": "7 दिन में आम भाव", "rows": rows, "note": "देश भर का आम भाव, पिछले हफ़्ते से तुलना"},
        {"kind": "list", "title": "फ़ैसला आपका, पर ये देखें", "items": [
            "रोकने का ख़र्च: गोदाम, ब्याज और सूखत जोड़ें", "प्याज़, आलू, टमाटर जैसी फसल ज़्यादा दिन नहीं रुकती",
            "MSP से नीचे भाव हो तो सरकारी ख़रीद/भावांतर देखें"]},
    ]
    lines = [f"रोकूं या बेचूं, {hi_date(day)}: 7 दिन में भाव का रुख़ (देश भर का आम भाव)।"]
    if up:
        lines.append("ऊपर: " + ", ".join(up[:5]))
    if down:
        lines.append("नीचे: " + ", ".join(down[:5]))
    lines += [f"• {r[0]}: {r[1]}" for r in rows]
    lines.append("यह सलाह नहीं, भाव का रुख़ है। अपनी मंडी और ख़र्च देखकर फ़ैसला करें।")
    return make_post(f"p4-{day.isoformat()}", "/rokun-ya-bechun", slides, lines,
                     "आप इस हफ़्ते रुकेंगे या बेचेंगे? फसल का नाम लिखकर बताएं।",
                     f"{names[lead['slug']]} 7 दिन में {arrow(lead['pctWeek'])}। बाकी फसलों का रुख़ 👇", feed_trust(day),
                     {"angle": f"week-{day.isocalendar()[1]}-{day.year}"})


# ---------------------------------------------------------------- P7
def night_risk(n, watch_c, high_c, calm_gust=10):
    """Same rule as the site's lib/pala.ts nightRisk."""
    calm = (n.get("code", 9) if n.get("code") is not None else 9) <= 1 and (n.get("gust") if n.get("gust") is not None else 99) < calm_gust
    t = n["tmin"]
    if t <= 0:
        return "frost"
    if t <= high_c or (t <= watch_c and calm):
        return "high"
    if t <= watch_c or (t <= 6 and calm):
        return "watch"
    return "none"


def frost_hits(day, cal, s=requests):
    p = cal["site"]["pala"]
    hits = []
    for name, st, lat, lon in HUBS:
        try:
            r = s.get(f"{SITE}/api/khet-weather", params={"lat": lat, "lon": lon}, timeout=40,
                      headers={"User-Agent": "TaazaBhav-posts/1.0"})
            fc = r.json().get("forecast", []) if r.status_code == 200 else []
        except Exception:
            continue
        for n in fc:
            if day.isoformat() <= n["date"] <= (day + timedelta(days=2)).isoformat() and n.get("tmin") is not None:
                risk = night_risk(n, p["watchC"], p["highC"])
                if risk in ("frost", "high"):
                    hits.append({"place": name, "state": st, "date": n["date"], "tmin": n["tmin"], "risk": risk})
                    break
    return hits


def build_p7(hits, day, cal):
    p = cal["site"]["pala"]
    hits = sorted(hits, key=lambda h: h["tmin"])
    lead = hits[0]
    word = {"frost": "पाला पड़ेगा", "high": "पाले का ज़्यादा ख़तरा"}
    rows = [[f"{h['place']} ({hi_date(h['date'])} की रात)", f"{h['tmin']:g}°C · {word[h['risk']]}"] for h in hits[:6]]
    short = [x.split("।")[0] for x in p["prevent"]]
    slides = [
        {"kind": "hook", "label": f"खेत अलार्म · {hi_date(day)}", "big": f"{lead['place']}: रात {lead['tmin']:g}°C",
         "sub": f"{word[lead['risk']]}, अगले 2 दिन"},
        {"kind": "table", "title": "कहाँ ख़तरा (न्यूनतम तापमान)", "rows": rows, "note": "MET Norway अनुमान, ताज़ा भाव के पाला अलर्ट से"},
        {"kind": "list", "title": "आज शाम ये करें", "items": short},
        {"kind": "list", "title": "किस फसल को ज़्यादा ख़तरा", "items": p["crops"][:3]},
    ]
    lines = [f"खेत अलार्म, {hi_date(day)}: अगली रातों में पाले का ख़तरा।"] + [f"• {r[0]}: {r[1]}" for r in rows]
    lines += ["", "बचाव:"] + [f"• {x}" for x in p["prevent"]] + ["", p["sdrf"] + "।"]
    states = sorted({h["state"] for h in hits})
    return make_post(f"p7-pala-{day.isoformat()}", "/pala-alert", slides, lines,
                     "आपके इलाके में आज रात कितनी ठंड है? ज़िला और तापमान कमेंट करें।",
                     f"{lead['place']} में रात {lead['tmin']:g}°C, पाले का ख़तरा। अपने खेत का अनुमान देखें 👇",
                     f"स्रोत: MET Norway (CC BY 4.0), IMD शीतलहर मानक, कृषि विभाग सलाह · जाँच: {hi_date(day)} {day.year}",
                     {"tool": "pala", "state": "+".join(states), "angle": f"pala-{day.isoformat()}"})


# ---------------------------------------------------------------- run
def entry_for(day, pillar, pid, meta, caption, res=None):
    res = res or {}
    return ledger.entry(day=day, slot="09:30", fmt="photo", pillar=pillar, post_id=pid, caption=caption,
                        crop=meta.get("crop"), state=meta.get("state"), tool=meta.get("tool"), angle=meta.get("angle"),
                        claim=meta.get("claim"), facebook=res.get("facebook"), instagram=res.get("instagram"))


def build(day, cal, plan, feed_loader, weather=frost_hits):
    """-> (pillar, post) for the day, or (pillar, None) when it can't be built."""
    led = ledger.load()
    try:
        hits = weather(day, cal) if cal.get("site", {}).get("pala") else []
    except Exception as e:
        print(f"[pillar] weather check failed: {e}")
        hits = []
    if hits:
        return "P7", build_p7(hits, day, cal)
    pillar = plan["pillar"]
    if plan.get("post"):
        return pillar, plan["post"]
    feed = feed_loader()
    if plan.get("dynamic") == "P1":
        return pillar, build_p1(feed, day, plan.get("args") or {}, led)
    if plan.get("dynamic") == "P3-hold":
        return pillar, build_p3_hold(feed, day, plan["args"], cal)
    if plan.get("dynamic") == "P4":
        return pillar, build_p4(feed, day)
    return pillar, None


def load_state():
    try:
        return json.loads(STATE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"history": [], "preview": []}


def save_state(state):
    STATE.parent.mkdir(parents=True, exist_ok=True)
    for k in ("history", "preview"):
        state[k] = state.get(k, [])[-90:]
    STATE.write_text(json.dumps(state, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


def legacy(reason, run_mode):
    """The old tool carousel posts instead, so the 09:30 slot is never empty.
    On a scheduled run (no mode given) it follows POSTS_LIVE, as before; a
    manual preview run only previews it."""
    print(f"[pillar] {reason}; tool carousel instead")
    from posts import run
    explicit = len(sys.argv) > 1 and sys.argv[1].strip()
    sys.argv = [sys.argv[0]] + (["publish"] if run_mode == "publish" else ["preview"] if explicit else [])
    return run.main()


def main():
    run_mode = mode()
    day = date.fromisoformat(sys.argv[2]) if len(sys.argv) > 2 else datetime.now(IST).date()
    state = load_state()
    key = "history" if run_mode == "publish" else "preview"
    if run_mode != "dry" and any(h["date"] == day.isoformat() for h in state.get(key, [])):
        print(f"[pillar] {run_mode}: already done today")
        return 0
    cal, plan = calendar(day)
    if not plan:
        alert(f"TaazaBhav pillar post: no calendar for {day:%Y-%m} (content/calendar). Tool carousel posted instead.")
        return legacy("no calendar day", run_mode) if run_mode != "dry" else 1
    if cal.get("previewOnly") and run_mode == "publish":
        # A part month (built with a start date) is for watching the format only.
        run_mode, key = "preview", "preview"
        if any(h["date"] == day.isoformat() for h in state.get(key, [])):
            print("[pillar] preview: already done today")
            return 0

    def feed_loader():
        from engine.feed import load_feed
        return load_feed(today=day, want_today=True)

    try:
        pillar, post = build(day, cal, plan, feed_loader)
    except Exception as e:
        traceback.print_exc()
        pillar, post = plan["pillar"], None
        alert(f"TaazaBhav pillar post ({plan['pillar']}, {day}): build failed: {e}")
    bad = []
    if post:
        bad = ledger.problems(entry_for(day, pillar, post["id"], post["meta"], post["caption"]), ledger.load(), day)
    if not post or bad:
        why = "; ".join(bad) if bad else "no data to build it today"
        if run_mode != "dry":
            alert(f"TaazaBhav pillar post ({pillar}, {day}): {why}. Tool carousel instead.")
        return legacy(why, run_mode) if run_mode != "dry" else 1
    print(f"[pillar] {run_mode}: {pillar} {post['id']}")
    try:
        from posts.render import render
        slides = render(post, Path("posts-out"))
        if run_mode == "dry":
            print("\n".join(map(str, slides)))
            return 0
        if run_mode == "preview":
            send_preview(post, slides)
            state.setdefault("preview", []).append({"date": day.isoformat(), "id": post["id"], "pillar": pillar})
            save_state(state)
            # Until PILLAR_LIVE=1 the old carousel keeps the slot (it follows POSTS_LIVE).
            return legacy("preview mode", "preview")
        res = publish(post, slides)
        state.setdefault("history", []).append({"date": day.isoformat(), "id": post["id"], "pillar": pillar,
                                                "facebook": res["facebook"], "instagram": res["instagram"]})
        save_state(state)
        ledger.safe_record(entry_for(day, pillar, post["id"], post["meta"], post["caption"], res))
        if res["errors"]:
            alert(f"TaazaBhav pillar post ({post['id']}): " + "\n".join(res["errors"])[:500])
        try:
            share_kit(post, res["facebook"])
        except Exception as e:
            alert(f"TaazaBhav pillar post: share kit failed: {e}")
        print(f"[pillar] published FB {res['facebook']} IG {res['instagram']}")
        return 0
    except Exception as e:
        traceback.print_exc()
        alert(f"TaazaBhav pillar post: {post['id']} failed, nothing posted.\n\n{e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
