# -*- coding: utf-8 -*-
import datetime as dt
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import fetch_clips
import flash

RECS = [
    {"market": "Bahraich", "modal_price": "5957"},
    {"market": "Mathura", "modal_price": "4000"},
    {"market": "Konch APMC", "modal_price": "1700"},
]
D = dt.date(2026, 9, 25)


class FlashPropsTest(unittest.TestCase):
    def test_low_tone_picks_cheapest_and_contrast(self):
        p = flash.build_props(RECS, "Uttar Pradesh", "Onion", D, story="spread", slot=1)
        self.assertEqual(p["tone"], "low")
        self.assertEqual(p["perQtl"], 1700)
        self.assertEqual(p["perKg"], 17.0)
        self.assertEqual(p["compare"]["perKg"], 59.6)
        self.assertEqual(p["commodityHi"], "प्याज")

    def test_high_tone_on_even_slot_and_non_spread(self):
        self.assertEqual(flash.build_props(RECS, "Uttar Pradesh", "Onion", D, "spread", 2)["perQtl"], 5957)
        self.assertEqual(flash.build_props(RECS, "Uttar Pradesh", "Onion", D, "best", 1)["tone"], "high")

    def test_needs_two_markets(self):
        with self.assertRaises(ValueError):
            flash.build_props(RECS[:1], "Uttar Pradesh", "Onion", D)

    def test_metadata(self):
        p = flash.build_props(RECS, "Uttar Pradesh", "Onion", D, "spread", 1)
        t, d = flash.flash_metadata(p, "Onion", "Uttar Pradesh", D, 3, "Video: A / Pexels")
        self.assertLessEqual(len(t), 100)
        self.assertIn("₹17 किलो", t)
        self.assertIn("#Shorts", t)
        self.assertIn("taazabhav.com", d.split("\n")[1])
        self.assertIn("Video: A / Pexels", d)

    def test_clip_folder(self):
        self.assertEqual(flash._clip_folder("Onion"), "onion")
        self.assertEqual(flash._clip_folder("Brinjal"), "generic")

    def test_make_flash_raises_so_main_can_fall_back(self):
        with mock.patch.object(flash, "render", side_effect=RuntimeError("no node")):
            with self.assertRaises(RuntimeError):
                flash.make_flash(RECS, "Uttar Pradesh", "Onion", D, "spread", 1)


class ClipLibraryTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.old = fetch_clips.CLIPS_DIR
        fetch_clips.CLIPS_DIR = Path(self.tmp.name)

    def tearDown(self):
        fetch_clips.CLIPS_DIR = self.old
        self.tmp.cleanup()

    def test_pick_clip_rotates_and_falls_back(self):
        self.assertIsNone(fetch_clips.pick_clip("onion", D, 1))
        g = fetch_clips.CLIPS_DIR / "generic"; g.mkdir()
        (g / "x.mp4").write_bytes(b"")
        self.assertEqual(fetch_clips.pick_clip("onion", D, 1).name, "x.mp4")
        o = fetch_clips.CLIPS_DIR / "onion"; o.mkdir()
        for n in "abc":
            (o / f"{n}.mp4").write_bytes(b"")
        picks = {fetch_clips.pick_clip("onion", D, s).name for s in range(1, 6)}
        self.assertGreater(len(picks), 1)
        self.assertEqual(fetch_clips.pick_clip("onion", D, 2), fetch_clips.pick_clip("onion", D, 2))

    def test_credit_for(self):
        (fetch_clips.CLIPS_DIR / "credits.json").write_text(json.dumps({"onion/a.mp4": {"author": "A", "source": "Pexels"}}))
        self.assertEqual(fetch_clips.credit_for(Path("x/onion/a.mp4"))["author"], "A")
        self.assertIsNone(fetch_clips.credit_for(None))

    def test_pexels_parse_picks_smallest_hd(self):
        resp = mock.Mock()
        resp.json.return_value = {"videos": [{"id": 7, "duration": 12, "url": "u", "user": {"name": "N"}, "video_files": [
            {"file_type": "video/mp4", "width": 1080, "height": 1920, "link": "big"},
            {"file_type": "video/mp4", "width": 720, "height": 1280, "link": "hd"},
            {"file_type": "video/mp4", "width": 360, "height": 640, "link": "sd"}]}]}
        s = mock.Mock(); s.get.return_value = resp
        c = fetch_clips.pexels_candidates("onion", "k", s)
        self.assertEqual(c[0]["url"], "hd")
        self.assertEqual(c[0]["id"], "pexels-7")


if __name__ == "__main__":
    unittest.main()
