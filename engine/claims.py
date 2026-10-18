# -*- coding: utf-8 -*-
"""Which PM Kisan dates other YouTube videos are claiming this week. Reads
the titles of the newest results for the kist search (YouTube Data API,
100 quota units of the free 10,000 a day) and counts specific dates. Used
only to say "this date is going around; the government has not announced
it" — never as a source for a date."""
import re
from collections import Counter
from datetime import date, datetime, timedelta, timezone

MONTH = {"अक्टूबर": 10, "october": 10, "oct": 10, "नवंबर": 11, "november": 11, "nov": 11, "दिसंबर": 12, "december": 12, "dec": 12,
         "जनवरी": 1, "january": 1, "jan": 1, "फ़रवरी": 2, "फरवरी": 2, "february": 2, "feb": 2, "मार्च": 3, "march": 3}
DATE_RE = re.compile(r"(\d{1,2})\s*(?:st|nd|rd|th)?\s*(अक्टूबर|नवंबर|दिसंबर|जनवरी|फ़रवरी|फरवरी|मार्च|october|november|december|january|february|march|oct|nov|dec|jan|feb)\b", re.I)


def dates_in(title, year):
    out = set()
    for d, m in DATE_RE.findall(title):
        try:
            out.add(date(year, MONTH[m.lower()], int(d)))
        except (ValueError, KeyError):
            continue
    return out


def top_claim(titles, today, min_count=3):
    c = Counter()
    for t in titles:
        for d in dates_in(t, today.year):
            if d >= today:
                c[d] += 1
    if not c:
        return None
    d, n = c.most_common(1)[0]
    return {"date": d.isoformat(), "count": n} if n >= min_count else None


def fetch_titles(n_next, youtube=None):
    if youtube is None:
        import pickle
        from googleapiclient.discovery import build
        with open("token.pickle", "rb") as f:
            youtube = build("youtube", "v3", credentials=pickle.load(f))
    after = (datetime.now(timezone.utc) - timedelta(days=7)).strftime("%Y-%m-%dT%H:%M:%SZ")
    r = youtube.search().list(part="snippet", q=f"PM Kisan {n_next}th installment date", type="video", regionCode="IN",
                              relevanceLanguage="hi", publishedAfter=after, maxResults=25).execute()
    return [i["snippet"]["title"] for i in r.get("items", [])]
