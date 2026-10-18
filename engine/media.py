# -*- coding: utf-8 -*-
"""Background clip, Hindi voice with word timings, and the Remotion render
for one Episode."""
import asyncio
import json
import os
import random
import shutil
import subprocess
from pathlib import Path

import requests

from engine.text import spoken

FPS = 30
VOICE = os.environ.get("ENGINE_VOICE", "hi-IN-MadhurNeural")
SHORTS = Path("shorts")
PUBLIC = SHORTS / "public"

# Pexels searches per clip folder. The crop list follows the Samachar crops.
CLIP_QUERIES = {
    "onion": ["onion market india", "onions pile"], "potato": ["potato harvest", "potatoes pile"],
    "tomato": ["tomato market india", "tomatoes pile"], "garlic": ["garlic bulbs pile", "garlic"],
    "soyabean": ["soybean field", "soybean harvest"], "cotton": ["cotton field", "cotton harvest"],
    "maize": ["corn field", "maize harvest"], "groundnut": ["peanut harvest", "peanuts"],
    "wheat": ["wheat field", "wheat harvest"], "paddy": ["rice paddy field", "rice harvest"],
    "mustard": ["mustard field yellow", "mustard flowers"], "bajra": ["millet field", "pearl millet"],
    "chana": ["chickpeas", "chickpea field"], "moong": ["green gram", "mung beans"], "jeera": ["cumin seeds", "spices market"],
    "generic": ["indian farmer field", "farm field sunrise", "vegetable market india"],
}
MIN_SCENE_S = {"phone": 6.0, "meter": 2.2, "compare": 2.2, "stamp": 2.0}


# ---------------------------------------------------------------- clip
def fetch_clip(folder, seed, out_path, session=requests):
    """One portrait stock clip for the crop from Pexels (free licence,
    credited). Returns {"path", "credit"} or None; a failure only means a
    plain background."""
    key = os.environ.get("PEXELS_API_KEY")
    if not key:
        return None
    from fetch_clips import pexels_candidates, trim, _blocklist
    blocked = _blocklist()
    rnd = random.Random(seed)
    for q in CLIP_QUERIES.get(folder, CLIP_QUERIES["generic"]) + CLIP_QUERIES["generic"]:
        try:
            cands = [c for c in pexels_candidates(q, key, session) if c["id"] not in blocked and c["duration"] >= 6]
        except Exception as e:
            print(f"[engine] clip search failed ({q}): {e}")
            continue
        if not cands:
            continue
        c = rnd.choice(cands[:8])
        raw = Path(out_path).with_suffix(".raw")
        try:
            with session.get(c["url"], stream=True, timeout=60) as r:
                r.raise_for_status()
                with open(raw, "wb") as fh:
                    for chunk in r.iter_content(1 << 16):
                        fh.write(chunk)
            trim(raw, out_path)
            return {"path": str(out_path), "credit": f"Video: {c['author']} / Pexels"}
        except Exception as e:
            print(f"[engine] clip download failed: {e}")
        finally:
            raw.unlink(missing_ok=True)
    return None


# ---------------------------------------------------------------- voice
def _duration(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", str(path)],
                         capture_output=True, text=True, check=True)
    return float(out.stdout.strip())


def _estimate_words(text, secs):
    words = text.split()
    total = sum(len(w) + 1 for w in words) or 1
    out, t = [], 0.0
    for w in words:
        out.append({"w": w, "t": t})
        t += secs * (len(w) + 1) / total
    return out


def synth(texts, out_dir):
    """One mp3 per scene. Returns [{"audio", "secs", "words": [{"w", "t"}]}]
    with word start times from edge-tts (WordBoundary). ENGINE_SILENT=1
    writes silent clips of estimated length (local previews only)."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    res = []
    if os.environ.get("ENGINE_SILENT") == "1":
        for i, t in enumerate(texts):
            secs = max(1.0, len(t) / 13.5)
            f = out_dir / f"s{i}.mp3"
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono", "-t", f"{secs:.2f}", str(f)], check=True)
            res.append({"audio": f"voice/s{i}.mp3", "secs": secs, "words": _estimate_words(t, secs)})
        return res
    import edge_tts

    async def one(i, text):
        say = spoken(text)
        comm = edge_tts.Communicate(say, VOICE, rate="+8%", boundary="WordBoundary")
        audio, words = bytearray(), []
        async for ch in comm.stream():
            if ch["type"] == "audio":
                audio.extend(ch["data"])
            elif ch["type"] == "WordBoundary":
                words.append({"w": ch["text"], "t": ch["offset"] / 1e7})
        f = out_dir / f"s{i}.mp3"
        f.write_bytes(bytes(audio))
        secs = _duration(f)
        return {"audio": f"voice/s{i}.mp3", "secs": secs, "words": words or _estimate_words(say, secs)}

    def fallback(i, text):
        # gTTS (Google) when the Edge voice is refused; word times are estimated.
        from gtts import gTTS
        say = spoken(text)
        raw = out_dir / f"g{i}.mp3"
        gTTS(say, lang="hi").save(str(raw))
        f = out_dir / f"s{i}.mp3"
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(raw), "-filter:a", "atempo=1.15", str(f)], check=True)
        raw.unlink(missing_ok=True)
        secs = _duration(f)
        return {"audio": f"voice/s{i}.mp3", "secs": secs, "words": _estimate_words(say, secs)}

    async def go():
        res = []
        for i, t in enumerate(texts):
            try:
                res.append(await one(i, t))
            except Exception as e:
                print(f"[engine] Edge voice failed ({e}); using Google voice")
                return None
        return res
    res = asyncio.run(go())
    return res if res is not None else [fallback(i, t) for i, t in enumerate(texts)]


# ---------------------------------------------------------------- props + render
def build_props(ep, voice, clip=None, rec_secs=None):
    scenes, frame = [], 0
    vi = iter(voice)
    for s in ep["scenes"]:
        v = next(vi)
        secs = max(v["secs"] + 0.25, MIN_SCENE_S.get(s["kind"], 1.4))
        if s["kind"] == "phone" and rec_secs:
            secs = min(secs, rec_secs)
        n = round(secs * FPS)
        sc = {k: val for k, val in s.items() if k != "say"}
        sc.update({"from": frame, "frames": n, "audio": v["audio"],
                   "words": [{"w": w["w"], "from": frame + round(w["t"] * FPS)} for w in v["words"]]})
        scenes.append(sc)
        frame += n
    # Loop beat: the first scene's picture again (no voice), so the replay seam is invisible.
    first = {k: val for k, val in scenes[0].items() if k not in ("audio", "words")}
    first.update({"from": frame, "frames": 15, "count": None})
    scenes.append(first)
    frame += 15
    return {
        "series": ep["series"], "clip": "clip.mp4" if clip else None, "credit": (clip or {}).get("credit"),
        "stamp": ep.get("stamp"), "stampTop": ep.get("stampTop"), "scenes": scenes, "frames": frame,
    }


def render(props, out_path, clip=None, rec=None):
    (PUBLIC / "fonts").mkdir(parents=True, exist_ok=True)
    for f in ("Baloo2-Bold.ttf", "IBMPlexMono-SemiBold.ttf"):
        shutil.copyfile(Path("assets/fonts") / f, PUBLIC / "fonts" / f)
    if clip:
        shutil.copyfile(clip["path"], PUBLIC / "clip.mp4")
    if rec:
        shutil.copyfile(rec, PUBLIC / "rec.mp4")
    pf = (SHORTS / "props.json").resolve()
    pf.write_text(json.dumps(props, ensure_ascii=False), encoding="utf-8")
    cmd = ["npx", "remotion", "render", "src/Root.tsx", "Desk", str(Path(out_path).resolve()), f"--props={pf}", "--log=error"]
    if os.environ.get("REMOTION_BROWSER_EXECUTABLE"):
        cmd.append(f"--browser-executable={os.environ['REMOTION_BROWSER_EXECUTABLE']}")
    subprocess.run(cmd, cwd=SHORTS, check=True, timeout=1200)
    return out_path
