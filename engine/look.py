# -*- coding: utf-8 -*-
"""What makes one engine video look and sound different from the last
(owner, 10 Nov 2026: "background and transitions should change, voice
sometimes male and sometimes female, the same-same feeling must go").

  * theme: one of shorts/src/desk/theme.ts THEMES (tint, camera move, scene
    transition). It follows the date, so two days in a row never match.
  * clip: the stock-video topic, chosen from the scheme's own words when
    there is a match (solar pump -> solar), else it rotates by date.
  * voice: engine.media.voice_for (a man one day, a woman the next).
"""
THEME_COUNT = 5

# id/scheme word -> clip folder (see engine.media.CLIP_QUERIES)
CLIP_HINTS = (
    (("kusum", "solar", "pump"), "solar"),
    (("sinchai", "irrigation", "drip", "pipeline"), "irrigation"),
    (("kcc", "credit", "loan", "bank", "bima", "insurance", "samman", "kist", "kisan-id", "farmer-id"), "bank"),
    (("tractor", "yantra", "machine", "subsidy"), "tractor"),
    (("rabi", "buvai", "gehu", "wheat", "mustard", "chana"), "wheat"),
    (("dhan", "paddy", "kharif", "msp", "kharid", "mandi"), "paddy"),
    (("pashu", "dairy", "gau", "cow", "milk", "murgi"), "dairy"),
)
ROTATE = ("village", "tractor", "farmer", "market", "rain", "harvest", "generic")


def theme_for(today):
    return today.toordinal() % THEME_COUNT


def clip_for(item_id, today, scheme=""):
    text = f"{item_id} {scheme}".lower()
    for words, folder in CLIP_HINTS:
        if any(w in text for w in words):
            return folder
    return ROTATE[today.toordinal() % len(ROTATE)]
