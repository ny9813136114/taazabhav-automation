# -*- coding: utf-8 -*-
"""MP Mukhyamantri Kisan Kalyan daily Reel (12 Nov 2026, owner's choice).

The owner's best Facebook video was about this scheme, and asked for it every
day. There is no new official date, so each day takes one of three angles
(day number mod 3: not-announced check, status portal, fraud warning) and the look engine gives it a new theme, clip and voice
every time (engine/look.py, scheme "mpkalyan"). Facebook and Instagram only,
never YouTube (episode flag meta_only).

Facts: only what taazabhav.com's kist tracker already says and checks daily
("no official date for the 16th kist yet") plus the official portal and
general fraud advice. No date, amount or news-site number is used. When an official date appears, set it on the site;
this module then stops saying "not announced" (see build_m)."""
from engine import yojana

SCHEME = "mpkalyan"
PORTAL = "saara.mp.gov.in"
TOOL = {"path": "/mp-kisan-kalyan-kist", "label": "किस्त ट्रैकर", "big": "ताज़ा स्थिति",
        "say": "किस्त की ताज़ा स्थिति taazabhav.com पर देखें"}


def _angle(n):
    if n == 0:
        return {
            "id": "mpkk-kab", "format": "sach",
            "title": "मुख्यमंत्री किसान कल्याण योजना: 16वीं किस्त की तारीख? सच | MP Kisan Kalyan 16th Kist",
            "hook": {"label": "16वीं किस्त", "big": "तारीख कब आएगी?", "sub": "मुख्यमंत्री किसान कल्याण योजना",
                     "say": "मुख्यमंत्री किसान कल्याण योजना की सोलहवीं किस्त की तारीख क्या है?"},
            "verdict": {"big": "सरकारी तारीख नहीं", "sub": "अभी घोषित नहीं", "tone": "low",
                        "say": "सरकार ने अभी कोई तारीख घोषित नहीं की है"},
            "facts": [
                {"label": "सावधान", "big": "बिना पुष्टि की खबर", "sub": "तारीख सिर्फ़ सरकारी घोषणा से मानें",
                 "say": "बिना सरकारी पुष्टि वाली तारीख पर भरोसा न करें"},
                {"label": "सबसे पहले", "big": "तारीख आते ही", "sub": "taazabhav.com पर अपडेट",
                 "say": "सरकारी तारीख आते ही taazabhav.com पर बताई जाएगी"},
            ],
        }
    if n == 1:
        return {
            "id": "mpkk-status", "format": "portal",
            "title": "मुख्यमंत्री किसान कल्याण योजना: अपनी किस्त का स्टेटस कहां देखें? | MP Kisan Kalyan Status",
            "hook": {"label": "किस्त स्टेटस", "big": "कहां देखें?", "sub": "मुख्यमंत्री किसान कल्याण योजना",
                     "say": "मुख्यमंत्री किसान कल्याण योजना की किस्त का स्टेटस कहां देखें?"},
            "facts": [
                {"label": "सरकारी पोर्टल", "big": PORTAL, "sub": "मध्य प्रदेश सरकार",
                 "say": "स्टेटस के लिए सरकारी पोर्टल saara dot mp dot gov dot in"},
                {"label": "किस पर भरोसा", "big": "सिर्फ़ सरकारी साइट", "sub": "लिंक भेजने वालों से बचें",
                 "say": "किस्त के नाम पर आए अनजान लिंक पर अपनी जानकारी न डालें"},
            ],
        }
    return {
        "id": "mpkk-thagi", "format": "state",
        "title": "किस्त के नाम पर ठगी से बचें: मुख्यमंत्री किसान कल्याण योजना | MP Kisan Kalyan Fraud Alert",
        "hook": {"label": "ठगी से बचें", "big": "किस्त के नाम पर", "sub": "मुख्यमंत्री किसान कल्याण योजना",
                 "say": "किस्त के नाम पर आने वाले मैसेज से सावधान रहें"},
        "facts": [
            {"label": "कभी न दें", "big": "OTP और बैंक डिटेल", "sub": "किसी अनजान लिंक पर",
             "say": "अनजान लिंक पर ओटीपी या बैंक की जानकारी कभी न डालें"},
            {"label": "सही जगह", "big": PORTAL, "sub": "सिर्फ़ सरकारी पोर्टल",
             "say": "जानकारी सिर्फ़ सरकारी पोर्टल saara dot mp dot gov dot in पर देखें"},
        ],
    }


def build_m(today):
    n = today.toordinal() % 3
    a = _angle(n)
    it = {**a, "scheme": SCHEME, "scope": "state", "state": "MP", "tool": TOOL,
          "source": PORTAL, "tags": ["mp kisan kalyan yojana", "mukhyamantri kisan kalyan"],
          "checked": today.isoformat()}
    ep = yojana.build_item(it, today)
    ep["key"] = f"mpkk|{today.isoformat()}"
    ep["meta_only"] = True
    ep["stampTop"] = "मध्य प्रदेश किसान"
    return ep
