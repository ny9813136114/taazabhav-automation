# -*- coding: utf-8 -*-
"""Builds the stock-clip library for "भाव फ्लैश" Shorts (Batch 4, 27 Sep 2026).

Run by .github/workflows/clips.yml (manual "Run workflow", e.g. once a month),
NOT by the daily pipeline -- the 5 AM runs only read clips already committed
to assets/clips/, so a Pexels/Pixabay outage can never block a daily video.

Per crop it searches Pexels videos first (PEXELS_API_KEY), then Pixabay
videos (PIXABAY_API_KEY, optional), keeps up to CLIPS_PER_CROP clips that are
long enough, trims each to 8 s, crops to 720x1280 (9:16), strips audio, and
writes assets/clips/<crop>/<source>-<id>.mp4 plus assets/clips/credits.json
({file: {source, author, url}}) for on-screen / description credit.

Both licences allow free commercial use (Pexels licence; Pixabay content
licence). We credit anyway. Never pull clips from YouTube/Instagram.

Curation: search results are not always on-topic (e.g. "onion" → kitchen
cooking). Queries lead with market/heap/field words, and assets/clips/
blocklist.txt lists clip ids to skip forever. After a run, check
assets/clips/preview.jpg (first frame of every clip) and add bad ids to the
blocklist, then re-run.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

import requests

CLIPS_DIR = Path("assets/clips")
CLIPS_PER_CROP = 8
MIN_SECONDS = 6
CLIP_SECONDS = 8
TIMEOUT = 30

QUERIES = {
    "onion": ["onion market india", "onions pile", "red onions market", "onion harvest"],
    "potato": ["potato market india", "potatoes pile", "potato harvest"],
    "tomato": ["tomato market india", "tomatoes pile", "tomato harvest"],
    "garlic": ["garlic market", "garlic bulbs pile", "garlic"],
    "soyabean": ["soybean field", "soybeans", "soybean harvest"],
    "cotton": ["cotton field", "cotton harvest", "cotton plant"],
    "maize": ["corn field", "maize harvest", "corn cobs"],
    "groundnut": ["peanuts", "peanut harvest", "groundnut"],
    "generic": ["indian vegetable market", "farmer india field", "vegetable market"],
}


def _blocklist():
    p = CLIPS_DIR / "blocklist.txt"
    if not p.exists():
        return set()
    return {ln.strip() for ln in p.read_text(encoding="utf-8").splitlines() if ln.strip() and not ln.startswith("#")}


def pexels_candidates(query, key, session=requests):
    """[{id, url, author, page, duration, w, h}] best file per video."""
    r = session.get(
        "https://api.pexels.com/videos/search",
        params={"query": query, "orientation": "portrait", "per_page": 15},
        headers={"Authorization": key}, timeout=TIMEOUT,
    )
    r.raise_for_status()
    out = []
    for v in r.json().get("videos", []):
        files = [f for f in v.get("video_files", []) if f.get("file_type") == "video/mp4" and f.get("width") and f.get("height")]
        # smallest file that is still >= 720 px wide in portrait (fast download)
        files = sorted((f for f in files if min(f["width"], f["height"]) >= 720), key=lambda f: f["width"] * f["height"])
        if not files:
            continue
        out.append({
            "id": f"pexels-{v['id']}", "url": files[0]["link"], "duration": v.get("duration", 0),
            "author": (v.get("user") or {}).get("name", "Pexels"), "page": v.get("url", ""), "source": "Pexels",
        })
    return out


def pixabay_candidates(query, key, session=requests):
    r = session.get(
        "https://pixabay.com/api/videos/",
        params={"key": key, "q": query, "per_page": 20, "safesearch": "true"}, timeout=TIMEOUT,
    )
    r.raise_for_status()
    out = []
    for h in r.json().get("hits", []):
        vids = h.get("videos") or {}
        f = vids.get("medium") or vids.get("large") or vids.get("small")
        if not f or not f.get("url"):
            continue
        out.append({
            "id": f"pixabay-{h['id']}", "url": f["url"], "duration": h.get("duration", 0),
            "author": h.get("user", "Pixabay"), "page": h.get("pageURL", ""), "source": "Pixabay",
        })
    return out


def trim(src, dst):
    """8 s, 720x1280 centre crop, no audio, small file."""
    subprocess.run([
        "ffmpeg", "-y", "-loglevel", "error", "-i", str(src), "-t", str(CLIP_SECONDS),
        "-vf", "scale=720:1280:force_original_aspect_ratio=increase,crop=720:1280,fps=30",
        "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "27", "-movflags", "+faststart", str(dst),
    ], check=True, timeout=180)


def build(crops=None, session=requests):
    pexels_key = os.environ.get("PEXELS_API_KEY")
    pixabay_key = os.environ.get("PIXABAY_API_KEY")
    if not pexels_key and not pixabay_key:
        sys.exit("No PEXELS_API_KEY or PIXABAY_API_KEY set.")
    CLIPS_DIR.mkdir(parents=True, exist_ok=True)
    credits_path = CLIPS_DIR / "credits.json"
    credits = json.loads(credits_path.read_text(encoding="utf-8")) if credits_path.exists() else {}
    blocked = _blocklist()

    for crop in (crops or QUERIES):
        folder = CLIPS_DIR / crop
        folder.mkdir(exist_ok=True)
        have = {p.stem for p in folder.glob("*.mp4")}
        for query in QUERIES[crop]:
            if len(have) >= CLIPS_PER_CROP:
                break
            cands = []
            try:
                if pexels_key:
                    cands += pexels_candidates(query, pexels_key, session)
                if pixabay_key:
                    cands += pixabay_candidates(query, pixabay_key, session)
            except requests.RequestException as e:
                print(f"[clips] {crop} / {query}: search failed ({e})")
                continue
            for c in cands:
                if len(have) >= CLIPS_PER_CROP:
                    break
                if c["id"] in have or c["id"] in blocked or c["duration"] < MIN_SECONDS:
                    continue
                raw = folder / f"_{c['id']}.raw"
                dst = folder / f"{c['id']}.mp4"
                try:
                    with session.get(c["url"], stream=True, timeout=TIMEOUT) as resp:
                        resp.raise_for_status()
                        with open(raw, "wb") as fh:
                            for chunk in resp.iter_content(1 << 16):
                                fh.write(chunk)
                    trim(raw, dst)
                except Exception as e:  # one bad clip never stops the library build
                    print(f"[clips] skip {c['id']}: {e}")
                    dst.unlink(missing_ok=True)
                    continue
                finally:
                    raw.unlink(missing_ok=True)
                have.add(c["id"])
                credits[f"{crop}/{dst.name}"] = {"source": c["source"], "author": c["author"], "url": c["page"]}
                print(f"[clips] + {crop}/{dst.name} ({c['source']}: {c['author']})")
        print(f"[clips] {crop}: {len(have)} clips")

    credits_path.write_text(json.dumps(credits, ensure_ascii=False, indent=2), encoding="utf-8")
    make_preview()


def make_preview():
    """assets/clips/preview.jpg: first frame of every clip, labelled, for a
    quick human check of relevance."""
    try:
        from PIL import Image, ImageDraw
    except ImportError:
        return
    clips = sorted(CLIPS_DIR.glob("*/*.mp4"))
    if not clips:
        return
    thumbs = []
    for c in clips:
        png = c.with_suffix(".jpg")
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", "1", "-i", str(c), "-frames:v", "1",
                        "-vf", "scale=144:256", str(png)], check=False, timeout=60)
        if png.exists():
            im = Image.open(png).convert("RGB")
            ImageDraw.Draw(im).text((4, 4), f"{c.parent.name}/{c.stem}"[:26], fill=(255, 255, 0))
            thumbs.append(im)
            png.unlink()
    cols = 8
    rows = (len(thumbs) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * 144, rows * 256), "black")
    for i, im in enumerate(thumbs):
        sheet.paste(im, ((i % cols) * 144, (i // cols) * 256))
    sheet.save(CLIPS_DIR / "preview.jpg", quality=80)


def pick_clip(crop, run_date, slot=1):
    """Deterministic rotation: a different clip each day and slot, never
    random (so re-runs of the same day reuse the same clip). Falls back to the
    generic folder, then None (renderer then uses a plain background)."""
    for folder in (CLIPS_DIR / crop, CLIPS_DIR / "generic"):
        clips = sorted(folder.glob("*.mp4"))
        if clips:
            i = (run_date.toordinal() * 5 + int(slot)) % len(clips)
            return clips[i]
    return None


def credit_for(clip_path):
    p = CLIPS_DIR / "credits.json"
    if not clip_path or not p.exists():
        return None
    key = f"{Path(clip_path).parent.name}/{Path(clip_path).name}"
    return json.loads(p.read_text(encoding="utf-8")).get(key)


if __name__ == "__main__":
    build(sys.argv[1:] or None)
