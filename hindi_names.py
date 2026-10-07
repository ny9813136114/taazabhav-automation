# -*- coding: utf-8 -*-
"""Hindi names, site links and number formatting shared by the script,
titles/descriptions and cards (Batch 2, 26 Sep 2026).

Why a separate file: before this, narration said "Onion" and "Uttar
Pradesh" in the middle of Hindi sentences, titles were English-only, and
nothing linked back to taazabhav.com. One table here keeps every surface
(voice, card, title, description, comment) using the same words.

Unknown names fall back to the original English string -- a missing entry
is a visible, harmless gap, never a wrong claim.
"""
import re

COMMODITY_HI = {
    "onion": "प्याज",
    "potato": "आलू",
    "tomato": "टमाटर",
    "wheat": "गेहूं",
    "soyabean": "सोयाबीन",
    "cotton": "कपास",
    "maize": "मक्का",
    "mustard": "सरसों",
    "garlic": "लहसुन",
    "ginger": "अदरक",
    "green chilli": "हरी मिर्च",
    "cauliflower": "फूलगोभी",
    "cabbage": "पत्तागोभी",
    "brinjal": "बैंगन",
    "bhindi(ladies finger)": "भिंडी",
    "bhindi": "भिंडी",
    "groundnut": "मूंगफली",
    "bajra(pearl millet/cumbu)": "बाजरा",
    "bajra": "बाजरा",
    "paddy(common)": "धान",
    "paddy": "धान",
    "banana": "केला",
    "apple": "सेब",
    "lemon": "नींबू",
}

STATE_HI = {
    "uttar pradesh": "उत्तर प्रदेश",
    "maharashtra": "महाराष्ट्र",
    "west bengal": "पश्चिम बंगाल",
    "karnataka": "कर्नाटक",
    "punjab": "पंजाब",
    "haryana": "हरियाणा",
    "rajasthan": "राजस्थान",
    "madhya pradesh": "मध्य प्रदेश",
    "gujarat": "गुजरात",
    "bihar": "बिहार",
    "odisha": "ओडिशा",
    "telangana": "तेलंगाना",
    "andhra pradesh": "आंध्र प्रदेश",
    "tamil nadu": "तमिलनाडु",
    "kerala": "केरल",
    "himachal pradesh": "हिमाचल प्रदेश",
    "uttarakhand": "उत्तराखंड",
    "chattisgarh": "छत्तीसगढ़",
    "chhattisgarh": "छत्तीसगढ़",
    "jharkhand": "झारखंड",
    "nct of delhi": "दिल्ली",
    "delhi": "दिल्ली",
}

MONTH_HI = ["जनवरी", "फ़रवरी", "मार्च", "अप्रैल", "मई", "जून", "जुलाई",
            "अगस्त", "सितंबर", "अक्टूबर", "नवंबर", "दिसंबर"]

SITE = "https://taazabhav.com"


def commodity_hi(commodity):
    return COMMODITY_HI.get(str(commodity).strip().lower(), str(commodity))


def state_hi(state):
    return STATE_HI.get(str(state).strip().lower(), str(state))


def date_hi(d):
    """date(2026, 9, 27) -> "27 सितंबर" """
    return f"{d.day} {MONTH_HI[d.month - 1]}"


def slug(text):
    """Same shape as the website's URLs: "Uttar Pradesh" -> "uttar-pradesh",
    "Onion Green" -> "onion-green", "Paddy(Common)" -> "paddycommon"."""
    s = re.sub(r"[^a-z0-9\s-]", "", str(text).strip().lower())
    return re.sub(r"[\s-]+", "-", s).strip("-")


# Crop URLs exactly as the website builds them (taazabhav-website
# lib/slug.ts COMMODITY_SLUGS + slugify, 7 Oct 2026): the big crops get the
# word farmers type ("dhan-paddy", "moong", "soybean"), every other bracket
# becomes a hyphen. Keep this table in sync with the website.
COMMODITY_SLUGS = {
    "soyabean": "soybean",
    "paddy(common)": "dhan-paddy",
    "paddy(dhan)(common)": "dhan-paddy-common",
    "paddy(basmati)": "basmati-dhan",
    "bajra(pearl millet/cumbu)": "bajra",
    "jowar(sorghum)": "jowar",
    "ragi(finger millet)": "ragi",
    "green gram(moong)(whole)": "moong",
    "green gram dal(moong dal)": "moong-dal",
    "bengal gram(gram)(whole)": "chana",
    "bengal gram dal(chana dal)": "chana-dal",
    "black gram(urd beans)(whole)": "urad",
    "black gram dal(urd dal)": "urad-dal",
    "red gram/arhar/tur(whole)": "arhar-tur",
    "red gram split/arhar dal/tur dal": "arhar-dal",
    "kulthi(horse gram)": "kulthi",
    "bhindi(ladies finger)": "bhindi",
    "ginger(green)": "ginger",
    "ginger(dry)": "ginger-dry",
}


def site_slugify(value):
    """lib/slug.ts slugify(): lower, drop brackets, non-alnum runs -> "-"."""
    s = re.sub(r"[()]", "", str(value).lower())
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")


def commodity_slug(commodity):
    """lib/slug.ts commodityToSlug(): "Paddy(Common)" -> "dhan-paddy",
    "Soyabean" -> "soybean", "Onion" -> "onion"."""
    key = re.sub(r"\s+", " ", str(commodity).lower()).strip()
    return COMMODITY_SLUGS.get(key) or site_slugify(re.sub(r"[()/]", " ", str(commodity)))


def market_slug(market):
    """lib/slug.ts marketToSlug(): "Neemuch APMC" -> "neemuch"."""
    m = re.sub(r"^\s*APMC\s+", "", str(market), flags=re.I)
    m = re.sub(r"\s*APMC\s*$", "", m, flags=re.I).strip()
    return site_slugify(m)


def _utm(source, medium):
    return f"?utm_source={source}&utm_medium={medium}" if source else ""


def page_url(commodity, state, source="youtube", medium="shorts", hi=False):
    """Crop + state page (https://taazabhav.com[/hi]/mandi-bhav/<crop>/<state>)."""
    base = f"{SITE}/hi" if hi else SITE
    return f"{base}/mandi-bhav/{commodity_slug(commodity)}/{site_slugify(state)}{_utm(source, medium)}"


def crop_url(commodity, source="youtube", medium="shorts", hi=False):
    """Crop page (https://taazabhav.com[/hi]/mandi-bhav/<crop>)."""
    base = f"{SITE}/hi" if hi else SITE
    return f"{base}/mandi-bhav/{commodity_slug(commodity)}{_utm(source, medium)}"


def mandi_url(state, market, source="youtube", medium="shorts", hi=False):
    """Mandi page (https://taazabhav.com[/hi]/mandi-bhav/state/<state>/<mandi>)."""
    base = f"{SITE}/hi" if hi else SITE
    return f"{base}/mandi-bhav/state/{site_slugify(state)}/{market_slug(market)}{_utm(source, medium)}"


def date_hi_full(d):
    """date(2026, 10, 8) -> "8 अक्टूबर 2026" (pass the IST run date)."""
    return f"{date_hi(d)} {d.year}"


def search_phrase(commodity, d, place):
    """The exact Hindi search query, key phrase first (plan P1-9, 7 Oct 2026):
    "प्याज का भाव आज 8 अक्टूबर 2026 | नीमच मंडी". Google fills the top of
    Hindi mandi-price searches with FB/YT/IG posts whose title is this
    query, so every daily title and the first caption line start with it.
    place: "<मंडी> मंडी" for a mandi-specific post, else the Hindi state."""
    head = f"{commodity_hi(commodity)} का भाव आज {date_hi_full(d)}"
    return f"{head} | {place}" if place else head


def fit_title(key, extras=(), tail=" #Shorts", limit=100):
    """key first, then each extra (" | extra") only while the whole title,
    tail included, stays within limit (YouTube: 100 chars)."""
    title = key
    for extra in extras:
        if extra and len(f"{title} | {extra}{tail}") <= limit:
            title = f"{title} | {extra}"
    if len(title + tail) > limit:
        return (title[:limit - len(tail)].rstrip(" |") + tail) if tail else title[:limit]
    return title + tail


def inr(v):
    """Whole rupees with Indian grouping: 598300 -> "5,98,300"."""
    try:
        n = int(round(float(str(v).replace(",", ""))))
    except (TypeError, ValueError):
        return str(v)
    sign = "-" if n < 0 else ""
    d = str(abs(n))
    if len(d) <= 3:
        return sign + d
    head, tail = d[:-3], d[-3:]
    groups = []
    while len(head) > 2:
        groups.insert(0, head[-2:])
        head = head[:-2]
    if head:
        groups.insert(0, head)
    return sign + ",".join(groups + [tail])


def spoken_market(name):
    """Market name as the Hindi voice should say it: drops the "APMC"
    label and bracketed sub-names ("Mukerian(Talwara) APMC" -> "Mukerian")."""
    s = re.sub(r"\(.*?\)", "", str(name))
    s = re.sub(r"\bAPMC\b", "", s, flags=re.I)
    return re.sub(r"\s+", " ", s).strip(" ,-") or str(name).strip()


def price_int(v):
    try:
        return int(round(float(str(v).replace(",", ""))))
    except (TypeError, ValueError):
        return None
