# -*- coding: utf-8 -*-
"""No-repeat ledger for everything the Page posts on Facebook + Instagram.

One small JSON file per post in data/posts/ledger/, so two workflows that
post on the same day never hit a git conflict on a shared file. Every
photo/carousel post is checked before it goes out; Reels (the engine and
mela alerts) are only recorded, so a photo post never repeats today's Reel.

Rules (TaazaBhav FB/IG Content Engine plan, section 6, 21 Oct 2026):
  hook   the first caption line is never used twice (hash of the text)
  crop   one single-crop photo post per crop per day
  tool   a post about a tool (the old tool carousel, pillar P3) at most
         once in 14 days, and never the tool of today's Reel. Series D
         shows one tool every day, so Reels are not counted in the 14 days;
         pillars that only link a tool (P2 parchi -> mandi hisab, P8 ->
         sarkari paisa, ...) are weekly by design and not counted either
  topic  pillar + crop + state + angle once in 30 days
  claim  a "sach ya jhooth" claim once, until its govt order changes
         (claim id + order date is the key)

The daily bhav round-up names 7 crops; it is a round-up, not a crop post,
so it fills no crop slot."""
import hashlib
import json
import re
from datetime import date, timedelta
from pathlib import Path

DIR = Path("data/posts/ledger")
TOOL_DAYS = 14
TOPIC_DAYS = 30
TOOL_PILLARS = ("tool", "P3")
# P1 and P3 rotate through these, oldest first (plan, section 6).
STATES = ["madhya-pradesh", "rajasthan", "maharashtra", "uttar-pradesh",
          "gujarat", "haryana", "punjab", "karnataka"]


def hook_of(caption):
    """First non-empty caption line."""
    return next((l.strip() for l in (caption or "").splitlines() if l.strip()), "")


def hook_hash(text):
    """Same hook despite case, spacing or punctuation -> same hash."""
    norm = re.sub(r"[\s\W_]+", " ", (text or "").lower(), flags=re.UNICODE).strip()
    return hashlib.sha1(norm.encode("utf-8")).hexdigest()[:16]


def topic_key(e):
    parts = [e.get("pillar"), e.get("crop"), e.get("state"), e.get("angle")]
    if not any(parts[1:]):
        return None
    return "|".join(str(p or "").lower() for p in parts)


def load(root=DIR):
    out = []
    for f in sorted(Path(root).glob("*.json")):
        try:
            out.append(json.loads(f.read_text(encoding="utf-8")))
        except (OSError, ValueError):
            continue
    return out


def entry(*, day, slot, fmt, pillar, post_id, caption="", hook=None, crop=None, state=None,
          tool=None, angle=None, claim=None, crops=None, facebook=None, instagram=None):
    h = hook if hook is not None else hook_of(caption)
    e = {"date": day.isoformat() if isinstance(day, date) else day, "slot": slot, "format": fmt,
         "pillar": pillar, "id": post_id, "hook": h, "hook_hash": hook_hash(h),
         "crop": crop, "state": state, "tool": tool, "angle": angle, "claim": claim,
         "crops": crops, "facebook": facebook, "instagram": instagram}
    return {k: v for k, v in e.items() if v not in (None, [], "")}


def problems(e, ledger, today, skip=()):
    """Reasons this photo post would repeat something; [] = OK to post.
    skip names rules a format is exempt from ("hook", "crop", "tool",
    "tool_days", "topic", "claim")."""
    out = []
    since = lambda days: (today - timedelta(days=days)).isoformat()
    day = today.isoformat()
    if "hook" not in skip and e.get("hook") and any(x.get("hook_hash") == e["hook_hash"] for x in ledger):
        out.append(f"hook already used: {e['hook'][:60]}")
    if "crop" not in skip and e.get("crop"):
        if any(x.get("format") == "photo" and x.get("crop") == e["crop"] and x["date"] == day for x in ledger):
            out.append(f"{e['crop']} already had a photo post today")
    about_tool = e.get("tool") and e.get("pillar") in TOOL_PILLARS
    if "tool" not in skip and about_tool:
        if any(x.get("format") == "reel" and x.get("tool") == e["tool"] and x["date"] == day for x in ledger):
            out.append(f"{e['tool']} is today's Reel")
    if "tool_days" not in skip and about_tool:
        if any(x.get("format") == "photo" and x.get("pillar") in TOOL_PILLARS and x.get("tool") == e["tool"]
               and x["date"] > since(TOOL_DAYS) for x in ledger):
            out.append(f"{e['tool']} had a photo post in the last {TOOL_DAYS} days")
    t = topic_key(e)
    if "topic" not in skip and t and any(topic_key(x) == t and x["date"] > since(TOPIC_DAYS) for x in ledger):
        out.append(f"topic used in the last {TOPIC_DAYS} days: {t}")
    if "claim" not in skip and e.get("claim") and any(x.get("claim") == e["claim"] for x in ledger):
        out.append(f"claim already checked: {e['claim']}")
    return out


def next_state(ledger, pillar, states=STATES):
    """State this pillar used longest ago (never used first)."""
    last = {}
    for x in ledger:
        if x.get("pillar") == pillar and x.get("state") in states:
            last[x["state"]] = max(last.get(x["state"], ""), x["date"])
    return min(states, key=lambda s: (last.get(s, ""), states.index(s)))


def record(e, root=DIR):
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    name = re.sub(r"[^a-z0-9-]+", "-", f"{e['date']}-{e.get('slot', '')}-{e.get('pillar', '')}-{e.get('id', '')}".lower()).strip("-")
    path = root / f"{name}.json"
    path.write_text(json.dumps(e, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return path


def safe_record(e, root=DIR):
    """Recording must never break a post that already went out."""
    try:
        return record(e, root)
    except Exception as ex:
        print(f"[ledger] could not record {e.get('id')}: {ex}")
        return None
