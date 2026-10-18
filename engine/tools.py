# -*- coding: utf-8 -*-
"""Series D "टूल से हल": a real phone-size screen recording of a
taazabhav.com tool solving one problem, with voice on top.

Playwright opens the live page at 390x844 (a normal Android screen),
switches it to Hindi, scrolls and types like a person would, and records
the screen. Each tool has a few example cases so the same video repeats
only after weeks. Selectors were read from the live pages on 17 Oct 2026;
if a selector stops matching, the recording step fails and the run skips
the slot (it never posts a broken video)."""
import os
import subprocess
import time
from pathlib import Path

from engine.text import link

# Fixed government prices shown on /khad-calculator (lib/khad.ts, checked 5 Oct 2026).
DAP_RS, UREA_RS = 1350, 266.5

TOOLS = [
    {
        "id": "khad", "path": "/khad-calculator", "clip": "generic",
        "cases": [{"crop": "wheat", "cropHi": "गेहूं", "acres": "2"}, {"crop": "mustard", "cropHi": "सरसों", "acres": "3"},
                  {"crop": "chana", "cropHi": "चना", "acres": "2"}, {"crop": "potato", "cropHi": "आलू", "acres": "1"}],
        "hook": lambda c: {"label": "DAP की बोरी", "big": "₹1,350", "sub": "इससे ज़्यादा लिया? गलत है", "tone": "low",
                           "say": "डीएपी की बोरी का सरकारी रेट तेरह सौ पचास रुपये है, इससे ज़्यादा लेना गलत है"},
        "steps_say": lambda c: f"अब देखिए {c['acres']} एकड़ {c['cropHi']} में कितनी बोरी लगेगी, ताज़ा भाव के खाद कैलकुलेटर में फ़सल चुनें, एकड़ डालें, और पूरा हिसाब सामने",
        "result": lambda c: {"label": "हर बोरी का सही रेट", "big": "बोरी + खर्च", "sub": "सेकंडों में", "say": "कितनी बोरी, कितना पैसा, सब सेकंडों में, बिल्कुल मुफ़्त"},
        "title": lambda c: f"DAP बोरी ₹1,350 से ज़्यादा? {c['acres']} एकड़ {c['cropHi']} का खाद हिसाब | DAP Price 2026 Khad Calculator",
        "steps": lambda c: [("hindi",), ("wait", 1200), ("scroll_to", "#khad-crop"), ("wait", 900), ("select", "#khad-crop", c["crop"]),
                            ("wait", 900), ("type", "#khad-acres", c["acres"]), ("wait", 1200), ("scroll_by", 380), ("wait", 2000),
                            ("scroll_text", "कुल खर्च"), ("wait", 3500)],
    },
    {
        "id": "msp", "path": "/msp-vs-mandi", "clip": "paddy",
        "cases": [{"crop": "paddy", "cropHi": "धान", "qtl": "40", "rate": "2200"}, {"crop": "soybean", "cropHi": "सोयाबीन", "qtl": "20", "rate": "4600"},
                  {"crop": "bajra", "cropHi": "बाजरा", "qtl": "25", "rate": "2300"}, {"crop": "maize", "cropHi": "मक्का", "qtl": "30", "rate": "1900"}],
        "hook": lambda c: {"label": c["cropHi"], "big": "MSP या मंडी?", "sub": "किसमें ज़्यादा पैसा बचेगा", "tone": "white",
                           "say": f"{c['cropHi']} एमएसपी पर बेचें या मंडी में? भाड़ा और इंतज़ार जोड़कर देखिए"},
        "steps_say": lambda c: f"फ़सल चुनें, {c['qtl']} क्विंटल डालें, मंडी का भाव {c['rate']} रुपये डालें, और दोनों तरफ़ हाथ में आने वाला पैसा सामने",
        "result": lambda c: {"label": "हाथ में कितना आएगा", "big": "MSP बनाम मंडी", "sub": "भाड़ा + इंतज़ार जोड़कर", "say": "भाड़ा, खर्च और इंतज़ार सब जोड़कर असली फ़र्क"},
        "title": lambda c: f"{c['cropHi']} MSP पर बेचें या मंडी में? 30 सेकंड में हिसाब | MSP vs Mandi Calculator",
        "steps": lambda c: [("hindi",), ("wait", 1200), ("scroll_to", "#mvm-crop"), ("wait", 900), ("select", "#mvm-crop", c["crop"]),
                            ("wait", 700), ("type", "#mvm-qtl", c["qtl"]), ("wait", 500), ("type", "#mvm-mandiRate", c["rate"]),
                            ("wait", 1200), ("scroll_by", 520), ("wait", 2500), ("scroll_by", 520), ("wait", 3000)],
    },
    {
        "id": "hisab", "path": "/mandi-hisab", "clip": "generic",
        "cases": [{"qtl": "20", "rate": "4500", "comm": "1800", "fee": "900"}, {"qtl": "15", "rate": "2400", "comm": "720", "fee": "360"},
                  {"qtl": "30", "rate": "6500", "comm": "3900", "fee": "1950"}],
        "hook": lambda c: {"label": "मंडी की पर्ची", "big": "कटौती सही?", "sub": "आढ़त, मंडी शुल्क, तौल", "tone": "low",
                           "say": "मंडी की पर्ची में आढ़ती ने कितना काटा, सही या ज़्यादा? तीस सेकंड में चेक करें"},
        "steps_say": lambda c: f"पर्ची से वज़न {c['qtl']} क्विंटल, भाव {c['rate']} रुपये, और आढ़त की रकम डालें, हिसाब चेकर तुरंत बताएगा कौन सी कटौती नियम से ज़्यादा है",
        "result": lambda c: {"label": "हर कटौती की जाँच", "big": "सही या गलत", "sub": "नियम के हिसाब से", "say": "हर कटौती नियम के हिसाब से, सही या गलत, साफ़"},
        "title": lambda c: "मंडी पर्ची में ज़्यादा कटौती? 30 सेकंड में चेक करो | Mandi Hisab Checker",
        "steps": lambda c: [("hindi",), ("wait", 1200), ("scroll_to", "#hisab-slipWeightQtl"), ("wait", 900),
                            ("type", "#hisab-slipWeightQtl", c["qtl"]), ("wait", 500), ("type", "#hisab-rate", c["rate"]), ("wait", 500),
                            ("type", "#hisab-commissionRs", c["comm"]), ("wait", 500), ("type", "#hisab-marketFeeRs", c["fee"]),
                            ("wait", 1200), ("scroll_by", 600), ("wait", 2500), ("scroll_by", 600), ("wait", 3000)],
    },
    {
        "id": "nuksan", "path": "/fasal-nuksan", "clip": "generic",
        "cases": [{"cropText": "Soybean", "cropHi": "सोयाबीन"}, {"cropText": "Paddy", "cropHi": "धान"}, {"cropText": "Wheat", "cropHi": "गेहूं"}],
        "hook": lambda c: {"label": "फ़सल खराब हुई?", "big": "72 घंटे", "sub": "बीमा क्लेम की समय सीमा", "tone": "low",
                           "say": "बारिश या ओले से फ़सल खराब हुई? बीमा क्लेम के लिए सिर्फ़ बहत्तर घंटे"},
        "steps_say": lambda c: "ताज़ा भाव का फ़सल नुकसान सबूत टूल खोलें, नुकसान का समय और कारण चुनें, खेत की जानकारी भरें, और सबूत तैयार",
        "result": lambda c: {"label": "क्लेम का सबूत", "big": "PDF तैयार", "sub": "फ़ोटो + तारीख + मौसम", "say": "फ़ोटो, तारीख और मौसम के साथ सबूत, प्रिंट करके जमा करें"},
        "title": lambda c: "फ़सल नुकसान? 72 घंटे में बीमा क्लेम का सबूत ऐसे बनाओ | PMFBY Claim Kaise Kare",
        "steps": lambda c: [("hindi",), ("wait", 1200), ("scroll_to", "#fn-when"), ("wait", 900), ("click_text", "Hailstorm|ओलावृष्टि"),
                            ("wait", 800), ("scroll_to", "#fn-crop"), ("type", "#fn-crop", c["cropText"]), ("wait", 1200),
                            ("scroll_by", 500), ("wait", 2500), ("scroll_by", 500), ("wait", 3000)],
    },
]


def pick_d(today, recent):
    """Rotate tools by day; within a tool, the case not used for longest."""
    n = len(TOOLS)
    for shift in range(n):
        tool = TOOLS[(today.toordinal() + shift) % n]
        for i in range(len(tool["cases"])):
            ci = (today.toordinal() // n + i) % len(tool["cases"])
            key = f"{tool['id']}|{ci}"
            if key not in recent:
                return tool, ci
    tool = TOOLS[today.toordinal() % n]
    return tool, 0


def build_d(today, recent):
    tool, ci = pick_d(today, recent)
    c = tool["cases"][ci]
    hook = tool["hook"](c)
    res = tool["result"](c)
    scenes = [
        {"kind": "headline", **hook},
        {"kind": "phone", "label": f"taazabhav.com{tool['path']}", "video": "rec.mp4", "say": tool["steps_say"](c)},
        {"kind": "headline", "tone": "good", **res},
        {"kind": "cta", "label": "मुफ़्त टूल, हिंदी में", "big": "लिंक कमेंट में 👇", "sub": f"taazabhav.com{tool['path']}",
         "say": "मुफ़्त है, हिंदी में है, लिंक कमेंट में"},
    ]
    url = link(tool["path"])
    desc = "\n".join([
        tool["title"](c).split("|")[0].strip(),
        f"टूल यहाँ खोलें (मुफ़्त, हिंदी में): {url}",
        "",
        "वीडियो में असली वेबसाइट की रिकॉर्डिंग है। रेट और नियम सरकारी स्रोत से, जाँच की तारीख टूल पेज पर लिखी है।",
        "Telegram: https://t.me/taazabhav",
        "#kisan #farmer #taazabhav #किसान",
    ])
    from engine.stories import _fit
    return {
        "series": "D", "key": f"{tool['id']}|{ci}", "clip": tool["clip"], "stamp": None, "scenes": scenes,
        "title": _fit(tool["title"](c)), "description": desc,
        "tags": ["kisan", "farmer tool", tool["id"], "taazabhav", "hindi"],
        "comment": f"🔗 टूल यहाँ: {url}\nकौन सा हिसाब और चाहिए? कमेंट करें 👇",
        "playlist": "D", "link": url, "tool": tool["id"], "case": ci,
    }


def _close_popups(pg):
    """Hides the "add to home screen" banner (a fixed bar) if it is showing."""
    try:
        pg.evaluate("""() => { for (const el of document.querySelectorAll('body *')) {
            if (!/ऐप की तरह|like an app|Add to home/i.test(el.innerText || '')) continue;
            let n = el;
            while (n && n !== document.body && getComputedStyle(n).position !== 'fixed') n = n.parentElement;
            if (n && n !== document.body && n.getBoundingClientRect().height < 200) n.style.display = 'none'; } }""")
    except Exception:
        pass


def record(tool_id, case_index, out_mp4, seconds=24):
    """Records the tool on the live site; writes an H.264 mp4 of at least
    `seconds` (the last frame is held if the steps finish early)."""
    from playwright.sync_api import sync_playwright
    tool = next(t for t in TOOLS if t["id"] == tool_id)
    c = tool["cases"][case_index]
    tmp = Path(out_mp4).with_suffix("")
    tmp.mkdir(parents=True, exist_ok=True)
    launch = {}
    if os.environ.get("ENGINE_CHROME"):
        launch["executable_path"] = os.environ["ENGINE_CHROME"]
    if os.environ.get("HTTPS_PROXY"):
        launch["proxy"] = {"server": os.environ["HTTPS_PROXY"]}
    with sync_playwright() as p:
        b = p.chromium.launch(**launch)
        ctx = b.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=2, locale="hi-IN", ignore_https_errors=True,
                            record_video_dir=str(tmp), record_video_size={"width": 390, "height": 844})
        t0 = time.monotonic()
        pg = ctx.new_page()
        pg.goto("https://taazabhav.com" + tool["path"], timeout=120000, wait_until="networkidle")
        start = None
        for st in tool["steps"](c):
            op = st[0]
            if op != "hindi" and start is None:
                pg.wait_for_timeout(600)
                start = time.monotonic() - t0  # skip the page-load part of the recording
            if op == "hindi":
                btn = pg.locator("button[aria-label='Toggle Hindi/English']").first
                if btn.count() and (btn.inner_text().strip() in ("हिं", "हि")):
                    btn.click()
            elif op == "wait":
                pg.wait_for_timeout(st[1])
                _close_popups(pg)
            elif op == "scroll_to":
                pg.locator(st[1]).first.evaluate("e => e.scrollIntoView({behavior: 'smooth', block: 'center'})")
                pg.wait_for_timeout(700)
            elif op == "scroll_text":
                loc = pg.get_by_text(st[1], exact=False)
                if loc.count():
                    loc.first.evaluate("e => e.scrollIntoView({behavior: 'smooth', block: 'center'})")
                    pg.wait_for_timeout(700)
            elif op == "scroll_by":
                pg.mouse.wheel(0, st[1])
            elif op == "select":
                pg.select_option(st[1], st[2])
            elif op == "type":
                pg.locator(st[1]).first.fill("")
                pg.locator(st[1]).first.type(st[2], delay=140)
            elif op == "click_text":
                for t in st[1].split("|"):
                    loc = pg.get_by_text(t, exact=False)
                    if loc.count():
                        loc.first.click()
                        break
        pg.wait_for_timeout(800)
        video = pg.video.path()
        ctx.close()
        b.close()
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{max(0.0, (start or 0) - 0.3):.2f}", "-i", str(video), "-vf", f"tpad=stop_mode=clone:stop_duration={seconds},fps=30",
                    "-t", str(seconds + 6), "-c:v", "libx264", "-pix_fmt", "yuv420p", "-an", str(out_mp4)], check=True)
    return out_mp4
