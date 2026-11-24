"""Brand-search line for every caption and description (24 Nov 2026).

Nobody searches "taazabhav" on Google yet (0 brand impressions in Search
Console). Brand searches are a strong trust signal for a young site, so every
post, reel and video now asks viewers to search the name once.

add_brand_line() is idempotent, puts the line just above the closing hashtag
line when there is one, and skips it rather than cut the text past `limit`.
"""

BRAND_LINE = "🔍 Google में लिखें: taazabhav"
MARK = "Google में लिखें: taazabhav"


def add_brand_line(text, limit=2200):
    text = text or ""
    if MARK in text:
        return text
    if len(text) + len(BRAND_LINE) + 2 > limit:
        return text
    head, sep, last = text.rstrip().rpartition("\n")
    if sep and last.lstrip().startswith("#"):
        return f"{head}\n{BRAND_LINE}\n{last}"
    return f"{text.rstrip()}\n\n{BRAND_LINE}" if text.strip() else BRAND_LINE
