# -*- coding: utf-8 -*-
"""Hindi text helpers for the content engine: rupees, dates, percentages,
and what the voice should say for a line written for the screen."""
import re
from datetime import date

MONTHS = ["जनवरी", "फ़रवरी", "मार्च", "अप्रैल", "मई", "जून", "जुलाई", "अगस्त", "सितंबर", "अक्टूबर", "नवंबर", "दिसंबर"]
SITE = "https://taazabhav.com"


def inr(n):
    """9560 -> '₹9,560' (Indian grouping)."""
    n = int(round(float(n)))
    s = str(abs(n))
    if len(s) > 3:
        head, tail = s[:-3], s[-3:]
        head = re.sub(r"(\d)(?=(\d{2})+$)", r"\1,", head)
        s = f"{head},{tail}"
    return f"{'-' if n < 0 else ''}₹{s}"


def day_hi(iso_or_date, year=False):
    d = date.fromisoformat(iso_or_date) if isinstance(iso_or_date, str) else iso_or_date
    return f"{d.day} {MONTHS[d.month - 1]}" + (f" {d.year}" if year else "")


def pct_text(p, arrow=True):
    """12.34 -> '▲ 12%' / -5.5 -> '▼ 5.5%'. Under 10 keeps one decimal."""
    a = abs(p)
    num = f"{a:.0f}" if a >= 10 else f"{a:.1f}".rstrip("0").rstrip(".")
    if not arrow:
        return f"{num}%"
    return f"{'▲' if p > 0 else '▼' if p < 0 else '•'} {num}%"


def pct_spoken(p):
    a = abs(p)
    return f"{a:.0f}" if a >= 10 else f"{a:.1f}".rstrip("0").rstrip(".")


def link(path, src=None):
    """Plain site link. Owner, 19 Oct 2026: no UTM tags on links."""
    return f"{SITE}{path}"


def spoken(text):
    """Screen text -> voice text: ₹ amounts, percent and the site name are
    rewritten so the Hindi voice reads them the way a farmer says them."""
    t = text.replace("taazabhav.com", "ताज़ा भाव डॉट कॉम")
    t = re.sub(r"₹\s*([\d,]+)", lambda m: m.group(1).replace(",", "") + " रुपये", t)
    t = re.sub(r"(\d+(?:\.\d+)?)\s*%", r"\1 प्रतिशत", t)
    t = t.replace("MSP", "एमएसपी").replace("/क्विंटल", " प्रति क्विंटल")
    t = re.sub(r"[▲▼•👇🔔✓❌📍]", "", t)
    return re.sub(r"\s+", " ", t).strip()
