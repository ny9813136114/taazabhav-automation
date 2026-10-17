# -*- coding: utf-8 -*-
"""Hard checks before anything renders or posts. A failed check skips the
slot and tells the owner; a wrong video is worse than no video."""
import re

# Seconds of voice-led video allowed per series (blueprint: A 12-15 s, B 12-18 s,
# C 35-45 s, D 25-35 s), with headroom for the voice speed.
BOUNDS = {"A": (7, 26), "B": (7, 28), "C": (18, 58), "D": (14, 48)}
BAD = re.compile(r"\b(None|nan|NaN|undefined|null)\b|₹0\b|₹-")
DATE_WORD = re.compile(r"\d{1,2} (जनवरी|फ़रवरी|मार्च|अप्रैल|मई|जून|जुलाई|अगस्त|सितंबर|अक्टूबर|नवंबर|दिसंबर)")


class QAError(Exception):
    pass


def check_episode(ep):
    errs = []
    texts = [ep["title"], ep["description"], ep["comment"]]
    for s in ep["scenes"]:
        texts += [str(s.get(k) or "") for k in ("label", "big", "sub", "say")]
        if len(str(s.get("big") or "")) > 18:
            errs.append(f"big text too long: {s.get('big')}")
        if not s.get("say"):
            errs.append(f"scene {s['kind']} has no voice line")
    for t in texts:
        if BAD.search(t):
            errs.append(f"bad value in: {t[:80]}")
    if len(ep["title"]) > 100:
        errs.append("title over 100 characters")
    if ep["series"] == "B" and "|status|" in ep["key"]:
        # Kist rule: without an official date, the only dates allowed are the
        # last paid date, today's date and a quoted viral claim.
        for s in ep["scenes"]:
            if s["kind"] in ("headline", "cta") and DATE_WORD.search(" ".join(str(s.get(k) or "") for k in ("label", "big", "sub", "say"))):
                errs.append("kist video names a date in a non-claim scene")
        if not any(s["kind"] == "stamp" and "नहीं" in (s.get("big") or "") for s in ep["scenes"]):
            errs.append("kist status video lacks the 'not announced' stamp")
    if errs:
        raise QAError("; ".join(errs))


def check_length(ep, seconds):
    lo, hi = BOUNDS[ep["series"]]
    if not lo <= seconds <= hi:
        raise QAError(f"series {ep['series']} video is {seconds:.1f}s, allowed {lo}-{hi}s")
