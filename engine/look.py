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


# --- the same scheme never looks the same twice (owner, 10 Nov 2026) --------
# "PM Kisan gets posted three or four times: each time the transition, design
# and UI must be different." Every published video records its scheme and
# look; the next video of that scheme takes a theme, clip and voice it has
# used least recently, and never the theme of the previous video of the day.

def _least_recent(options, used):
    """First option never used, else the one used longest ago. `used` is oldest first."""
    for o in options:
        if o not in used:
            return o
    return min(options, key=lambda o: max(i for i, u in enumerate(used) if u == o))


def pick_theme(scheme, today, past, n=THEME_COUNT, avoid=None):
    """past: [(scheme, theme)] oldest first. Theme for `scheme` today."""
    order = [(today.toordinal() + k) % n for k in range(n)]
    used = [t for s, t in past if s == scheme]
    last = past[-1][1] if past else None
    options = [t for t in order if t != last and t != avoid] or order
    return _least_recent(options, used)


def pick_look(scheme, today, episodes, scheme_hint=""):
    """-> {"theme", "clip", "voice"} for a video of `scheme`; episodes = the
    engine log (entries with a "look" count, older ones are ignored)."""
    seen = [e for e in episodes if e.get("look")]
    mine = [e["look"] for e in seen if e.get("scheme") == scheme]
    first = clip_for(scheme, today, scheme_hint)
    clips = [first] + [c for c in ROTATE if c != first]
    clip = _least_recent(clips, [m["clip"] for m in mine])
    voice = "female" if mine and mine[-1]["voice"] == "male" else "male" if mine else ("male" if today.toordinal() % 2 == 0 else "female")
    return {"theme": pick_theme(scheme, today, [(e["scheme"], e["look"]["theme"]) for e in seen]), "clip": clip, "voice": voice}
