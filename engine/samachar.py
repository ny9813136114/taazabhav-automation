# -*- coding: utf-8 -*-
"""Series V "मंडी समाचार" (24 Nov 2026, owner: "drop Shorts, we make 1-2 minute
videos"). One mandi, its main crops, in about a minute and a half: today's
price per kg, the week's move, the MSP check where it is news, a plain-words
summary and the usual comment question. Every number comes from the same
checked feed and sanity rules as the one-crop bhav video (stories.bhav_candidates).
A mandi with fewer than 3 checked crops, or prices older than 2 days, gives
no video (the slot stays quiet)."""
from datetime import date

from engine import stories as S
from engine.text import day_hi, inr, link, pct_text

MIN_CROPS, MAX_CROPS = 3, 4
MAX_STALE_DAYS = 2
MANDI_GAP_DAYS = 5


def _pick_mandi(cands, recent_markets):
    by = {}
    for x in cands:
        by.setdefault(x[0]["market"], []).append(x)
    ok = {k: v for k, v in by.items() if len(v) >= MIN_CROPS and k not in recent_markets}
    if not ok:
        return None
    # most crops with a week's history first, then the one not used for longest (dict order = feed order)
    return max(ok.values(), key=lambda v: (sum(1 for c in v if c[2]), len(v)))


def build_v(feed, today, recent_markets):
    latest = feed.get("latestDate")
    if not latest or (today - date.fromisoformat(latest)).days > MAX_STALE_DAYS:
        print(f"[engine] V: newest prices are from {latest}, too old")
        return None
    group = _pick_mandi(S.bhav_candidates(feed, today), recent_markets)
    if not group:
        return None
    group = group[:MAX_CROPS]
    m = group[0][0]
    mandi, place = m["marketHi"], m["market"].title()
    names = [S.HI_NAME[c["commodity"]] for _, c, *_ in group]
    scenes = [{"kind": "headline", "tone": "white", "label": f"{mandi} मंडी", "big": "आज का हाल", "sub": f"{len(group)} फ़सलों के भाव",
               "say": f"{mandi} मंडी में आज {', '.join(names[:-1])} और {names[-1]} का भाव क्या है? एक मिनट में पूरा हाल।"}]
    movers = []
    for i, (_, c, wk, pct, nat) in enumerate(group):
        crop = names[i]
        kg_text, kg_count = S.per_kg(c["modal"])
        tone = "steady" if pct is None or abs(pct) < 3 else ("up" if pct > 0 else "down")
        scenes.append({"kind": "number", "label": f"{crop}, आज", "big": kg_text.split("/")[0], "count": kg_count,
                       "sub": f"प्रति किलो · {inr(c['modal'])}/क्विंटल", "tone": tone,
                       "say": f"{crop} का भाव {kg_text.split('/')[0]} किलो, यानी {inr(c['modal'])} क्विंटल।"})
        if wk:
            diff = c["modal"] - wk[1]
            movers.append((abs(pct or 0), i))
            arrow = "▲" if diff > 0 else "▼" if diff < 0 else "•"
            scenes.append({"kind": "move", "big": f"{arrow} {inr(abs(diff))}", "label": f"{crop}, पिछले हफ़्ते से",
                           "sub": f"{day_hi(wk[0])} को {inr(wk[1])}", "tone": tone,
                           "say": f"{crop} का भाव हफ़्ते भर में " + ("वही रहा।" if diff == 0 else f"{abs(diff)} रुपये {'बढ़ा' if diff > 0 else 'गिरा'}।")})
        msp = nat.get("msp")
        if msp and c["modal"] < msp and not nat.get("perishable"):
            scenes.append({"kind": "compare", "label": f"{crop}: MSP से तुलना", "tone": "white",
                           "bars": [{"label": f"{mandi} मंडी", "value": c["modal"], "text": inr(c["modal"]), "tone": "low"},
                                    {"label": "MSP", "value": msp, "text": inr(msp), "tone": "white"}],
                           "say": f"{crop} का मंडी भाव एमएसपी से {msp - c['modal']} रुपये कम है।"})
    top = max(group, key=lambda x: x[1]["modal"])
    scenes.append({"kind": "compare", "label": "आज के भाव एक नज़र (क्विंटल)", "tone": "white",
                   "bars": [{"label": names[i], "value": g[1]["modal"], "text": inr(g[1]["modal"]), "tone": "good" if g is top else "white"} for i, g in enumerate(group)],
                   "say": f"सबसे ऊँचा भाव {S.HI_NAME[top[1]['commodity']]} का है, {inr(top[1]['modal'])} क्विंटल।"})
    if movers:
        _, j = max(movers)
        _, c, wk, pct, nat = group[j]
        pos, line, vtone = S.bhav_verdict(pct, bool(nat.get("msp") and c["modal"] < nat["msp"]), bool(nat.get("perishable")))
        scenes.append({"kind": "meter", "label": f"{names[j]}: इस हफ़्ते का रुख", "pos": pos, "sub": line, "tone": vtone,
                       "left": "रोकें", "right": "बेचें", "say": line})
    scenes.append({"kind": "cta", "label": "आपकी मंडी कौन सी?", "big": "कमेंट में लिखें 👇", "sub": "taazabhav.com",
                   "say": "आपकी मंडी कौन सी है? कमेंट में लिखिए, अगला वीडियो उसी का।"})

    title = S._fit(f"{mandi} मंडी भाव आज | {', '.join(names)} का पूरा हाल | {day_hi(group[0][1]['date'])}", tail="")
    lines = [f"{day_hi(group[0][1]['date'], True)}: {mandi} मंडी ({m['state']}) के आज के भाव (मॉडल, प्रति क्विंटल):"]
    for i, (_, c, wk, pct, nat) in enumerate(group):
        w = f" ({pct_text(pct, arrow=False)} पिछले हफ़्ते से)" if wk else ""
        lines.append(f"• {names[i]}: {inr(c['modal'])} (न्यूनतम {inr(c['min'])}, अधिकतम {inr(c['max'])}){w}")
    desc = "\n".join(lines + ["", f"{mandi} मंडी के सभी भाव: {link(m['path'])}", "",
                              "स्रोत: Agmarknet / data.gov.in (सरकारी मंडी आँकड़े)। भाव थोक (मंडी) के हैं।", S.DISCLAIMER, "",
                              "आपकी मंडी कौन सी है? कमेंट करें, अगला वीडियो उसी का।", "Telegram: https://t.me/taazabhav",
                              f"#मंडीभाव #{place.replace(' ', '')}Mandi #kisan #taazabhav"])
    return {"series": "V", "key": m["market"], "clip": S.CLIP.get(group[0][1]["commodity"], "generic"),
            "stamp": day_hi(group[0][1]["date"]), "badge": "मंडी समाचार", "scheme": "samachar", "scenes": scenes, "title": title,
            "description": desc,
            "tags": [f"{place} mandi bhav", f"{place} mandi bhav today", f"{mandi} मंडी भाव"] + names + ["mandi bhav", "aaj ka mandi bhav", "taazabhav"],
            "comment": f"📍 {mandi} मंडी के सभी भाव: {link(m['path'])}\nआपकी मंडी कौन सी है? कमेंट करें 👇",
            "playlist": "V", "link": link(m["path"])}
