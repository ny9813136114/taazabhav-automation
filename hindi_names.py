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


def page_url(commodity, state, source="youtube", medium="shorts"):
    return (f"{SITE}/mandi-bhav/{slug(commodity)}/{slug(state)}"
            f"?utm_source={source}&utm_medium={medium}")


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
