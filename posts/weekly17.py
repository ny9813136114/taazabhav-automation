# -*- coding: utf-8 -*-
"""17 unique weekly TaazaBhav feed concepts + matching 9:16 Story review assets.

Safety: preview-only. Stories are NOT posted to Meta by this module; the
account's Story publishing permissions/endpoint must be separately tested.
Existing automated feed workflows are not altered.
"""
import base64
import hashlib
import html
import json
import sys
from datetime import date, datetime
from pathlib import Path

import requests

from posts import ledger
from posts.run import IST, send_preview
from posts.render import render

ROOT = Path("data/posts/weekly17")
BRAND = "https://raw.githubusercontent.com/ny9813136114/Taazabhav-website/main/public/brand/taazabhav-logo.svg"
# Day index, title, website path, key message, question. All paths from the website repo.
PLAN = [
 (0,"गेहूं का मंडी भाव","/mandi-bhav/wheat","मंडी और भाव की तारीख जरूर जांचें","आपकी मंडी कौन-सी है?"),
 (0,"खेती लागत-मुनाफा","/kheti-lagat-munafa","खर्च और बिक्री जोड़कर अपना मुनाफा निकालें","सबसे बड़ा खर्च किसमें है?"),
 (0,"किसान सवाल","/learn","खेती का एक नया सवाल पूछें और जानकारी समझें","इस हफ्ते किस विषय पर जानकारी चाहिए?"),
 (1,"मंडी तुलना","/compare","अलग-अलग मंडियों के भाव के साथ ढुलाई भी जोड़ें","कौन-सी मंडियां तुलना में रखें?"),
 (1,"खाद कैलकुलेटर","/khad-calculator","अपने खेत के हिसाब से खाद का खर्च समझें","खाद की लागत कितनी आती है?"),
 (2,"आज का मौसम","/aaj-ka-mausam","स्थानीय मौसम देखकर खेती के काम तय करें","आपके इलाके में मौसम कैसा है?"),
 (2,"फसल बीमा","/fasal-bima-2026","बीमा की शर्तें और आधिकारिक सूचना जांचें","फसल बीमा को लेकर क्या सवाल है?"),
 (2,"मंडी हिसाब","/mandi-hisab","बिक्री की रकम और कटौती का हिसाब रखें","मंडी पर्ची में क्या समझना मुश्किल है?"),
 (3,"सरकारी सहायता","/sarkari-paisa","पात्रता और आवेदन की स्थिति आधिकारिक स्रोत से जांचें","किस योजना की जानकारी चाहिए?"),
 (3,"बीघा से एकड़","/bigha-to-acre","बीघा का माप इलाके के हिसाब से बदलता है","आप किस जिले से हैं?"),
 (4,"MSP या मंडी","/msp-vs-mandi","MSP, मंडी भाव और खर्च को साथ समझें","आप किस फसल की तुलना करेंगे?"),
 (4,"स्प्रे कैलकुलेटर","/spray-calculator","लेबल निर्देशों और स्थानीय सलाह को प्राथमिकता दें","स्प्रे का हिसाब कैसे रखते हैं?"),
 (4,"खेती की उपयोगी जानकारी","/khet","काम की खेती जानकारी एक जगह पढ़ें","अगला विषय क्या हो?"),
 (5,"रोकूं या बेचूं","/rokun-ya-bechun","भंडारण और ब्याज जोड़कर फैसला समझें","आप कौन-सी फसल स्टोर करते हैं?"),
 (5,"मिट्टी जांच","/mitti-jaanch","मिट्टी की जांच से पोषक तत्वों को समझें","मिट्टी जांच कब करवाई थी?"),
 (6,"खेती सीखें","/learn","एक उपयोगी खेती विषय आज सीखें","किस विषय पर आसान गाइड चाहिए?"),
 (6,"साप्ताहिक किसान चेकलिस्ट","/khet","मंडी, मौसम और खर्च का साप्ताहिक रिव्यू करें","अगले हफ्ते की प्राथमिकता क्या है?"),
]
ANGLES = ["काम की जानकारी", "फैसले से पहले", "किसान की चेकलिस्ट", "आज का सवाल", "स्मार्ट खेती टिप", "अपना हिसाब समझें", "एक मिनट में सीखें", "खेत से मंडी तक"]


def post_for(index, angle):
    day, title, path, message, question = PLAN[index]
    label = ANGLES[angle]
    ident = f"weekly17-{index:02d}-a{angle}"
    url = "https://taazabhav.com" + path
    hook = f"{label}: {title} — {message}"
    caption = (f"🌾 {hook}\n\n{message}।\n\n"
               f"📲 खुद देखें: {url}\n\n💬 {question}\n\n"
               "#TaazaBhav #किसान #खेती #AgricultureIndia")
    return {"id": ident, "title": title, "path": path, "caption": caption,
            "group": f"किसान भाइयों, {message}।\n{url}\n{question}",
            "link": url, "question": question,
            "slides": [
                {"kind":"hook","label":label,"big":title,"sub":message},
                {"kind":"list","title":"ध्यान देने वाली बात","items":[message,"अपनी जगह और तारीख के अनुसार जानकारी जांचें","वेबसाइट पर खुद विवरण देखें"]},
                {"kind":"cta","big":"अभी TaazaBhav पर देखें","url":"taazabhav.com"+path},
            ]}


def story(post, dest):
    """Branded 1080x1920 Story PNG; verified original SVG is downloaded."""
    from playwright.sync_api import sync_playwright
    response = requests.get(BRAND, timeout=20)
    response.raise_for_status()
    if "<svg" not in response.text[:1000]:
        raise ValueError("Original brand logo not available; cannot render story")
    logo = "data:image/svg+xml;base64," + base64.b64encode(response.content).decode()
    title = html.escape(post["title"])
    msg = html.escape(PLAN[int(post["id"].split("-")[1])][3])
    url = html.escape(post["link"])
    markup = f"""<!doctype html><html lang="hi"><meta charset="utf-8"><style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+Devanagari:wght@400;700;900&display=swap');
    *{{box-sizing:border-box}}body{{margin:0;width:1080px;height:1920px;font-family:'Noto Sans Devanagari',sans-serif;background:linear-gradient(155deg,#0B4A2C,#0F6B3E 58%,#17261D);color:white;overflow:hidden}}
    .sun{{position:absolute;width:850px;height:850px;top:230px;right:-390px;border-radius:50%;background:#E09A12;filter:blur(170px);opacity:.34}}
    .wrap{{position:relative;padding:150px 85px;height:100%;display:flex;flex-direction:column;justify-content:space-between}}
    .logo{{background:#F7F5EE;padding:35px;border-radius:32px;width:560px}}.logo img{{width:100%;height:95px;object-fit:contain}}
    .eyebrow{{font-size:48px;color:#FFD65A;font-weight:700}}h1{{font-size:112px;line-height:1.16;margin:36px 0}}.msg{{font-size:55px;line-height:1.45}}
    .cta{{background:#E09A12;color:#17261D;border-radius:30px;padding:42px;font-size:46px;font-weight:900;text-align:center}}
    .url{{font-size:35px;text-align:center;margin-top:25px;overflow-wrap:anywhere}}.small{{font-size:32px;opacity:.85}}
    </style><div class="sun"></div><div class="wrap">
    <div class="logo"><img src="{logo}"></div>
    <section><div class="eyebrow">किसानों के लिए काम की जानकारी</div><h1>{title}</h1><div class="msg">{msg}</div></section>
    <div><div class="cta">पूरी जानकारी वेबसाइट पर देखें</div><div class="url">{url}</div><p class="small">जानकारी की तारीख और अपने क्षेत्र की स्थिति जांचें</p></div>
    </div></html>"""
    dest.parent.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width":1080,"height":1920}, device_scale_factor=1)
        page.set_content(markup, wait_until="load")
        page.evaluate("document.fonts.ready")
        page.screenshot(path=str(dest))
        browser.close()


def main():
    today = date.fromisoformat(sys.argv[1]) if len(sys.argv)>1 else datetime.now(IST).date()
    day = today.weekday()
    week = today.isocalendar()
    key = f"{week.year}-W{week.week:02d}"
    existing = ledger.load()
    used = {e.get("id") for e in existing}
    hooks = {e.get("hook_hash") for e in existing}
    out = ROOT / key
    out.mkdir(parents=True, exist_ok=True)
    prepared = []
    for idx, item in enumerate(PLAN):
        if item[0] != day:
            continue
        candidate = None
        for angle in range(len(ANGLES)):
            p = post_for(idx, angle)
            h = ledger.hook_hash(ledger.hook_of(p["caption"]))
            if p["id"] not in used and h not in hooks:
                candidate = p
                break
        if candidate is None:
            print(f"[weekly17] no new angle for {idx}; skipped rather than repeat")
            continue
        paths = render(candidate, out / candidate["id"])
        story_path = out / f"{candidate['id']}-story.png"
        story(candidate, story_path)
        payload = {"date":today.isoformat(),"post":candidate,"feed_images":list(map(str,paths)),
                   "story_image":str(story_path),"facebook_group_copy":candidate["group"],
                   "status":"REVIEW_ONLY","note":"No FB, IG or Stories publishing performed"}
        (out / f"{candidate['id']}.json").write_text(json.dumps(payload,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        send_preview(candidate, paths)
        # Story delivered as an image to Telegram; no Meta Story API calls.
        from posts.run import _tg, _owner
        with open(story_path,"rb") as fh:
            _tg("sendPhoto",{"chat_id":_owner(),"caption":f"STORY PREVIEW: {candidate['id']} (not published)","disable_notification":"true"},files={"photo":fh})
        prepared.append(candidate["id"])
        used.add(candidate["id"])
        hooks.add(ledger.hook_hash(ledger.hook_of(candidate["caption"])))
    print(json.dumps({"date":today.isoformat(),"prepared":prepared,"review_only":True},ensure_ascii=False))
    return 0


if __name__=="__main__":
    sys.exit(main())
