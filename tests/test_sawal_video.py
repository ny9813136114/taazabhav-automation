# -*- coding: utf-8 -*-
"""Batch 8: daily "सवाल-जवाब" explainer (queue picking, spoken text,
metadata, props, preview/publish mode)."""
import json
import os
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import sawal_video as sv


def item(id_, frm="2026-10-06", to=None, **kw):
    base = {
        "id": id_, "pillar": "khad", "page": "https://taazabhav.com/khad-calculator",
        "page_utm": "https://taazabhav.com/khad-calculator?utm_source={src}&utm_medium=social&utm_campaign=sawal-jawab",
        "title": "DAP की बोरी का सही रेट ₹1,350 | DAP Price Today 2026 #Shorts",
        "hook_hi": "डीएपी की बोरी ₹1,350 से ज़्यादा में मिली?",
        "points_hi": ["a", "b", "c"], "cta_hi": "हिसाब taazabhav.com/khad-calculator पर।",
        "checked_on": "2026-10-06", "valid_from": frm, "valid_to": to,
    }
    base.update(kw)
    return base


class TestQueue(unittest.TestCase):
    def test_repo_queue_is_valid(self):
        items = sv.load_queue()
        self.assertGreaterEqual(len(items), 30)
        self.assertEqual(len({i["id"] for i in items}), len(items))
        for i in items:
            self.assertIn(i["pillar"], sv.PILLAR)
            self.assertLessEqual(len(i["title"]), 100, i["id"])
            self.assertEqual(len(i["points_hi"]), 3, i["id"])
            self.assertIn("{src}", i["page_utm"])
            self.assertTrue(i["page"].startswith("https://taazabhav.com/"))
            date.fromisoformat(i["checked_on"])

    def test_pick_first_fresh_in_window(self):
        items = [item("a", to="2026-10-01"), item("b", frm="2026-11-01"), item("c"), item("d")]
        self.assertEqual(sv.pick(items, {}, date(2026, 10, 6))["id"], "c")
        self.assertEqual(sv.pick(items, {"c": "2026-10-06"}, date(2026, 10, 7))["id"], "d")

    def test_repeat_only_after_60_days(self):
        items = [item("c"), item("d")]
        pub = {"c": "2026-10-06", "d": "2026-10-07"}
        self.assertIsNone(sv.pick(items, pub, date(2026, 11, 1)))
        self.assertEqual(sv.pick(items, pub, date(2026, 12, 6))["id"], "c")

    def test_published_roundtrip(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "x" / "pub.json"
            sv.mark_published("c", date(2026, 10, 6), p)
            self.assertEqual(sv.load_published(p), {"c": "2026-10-06"})


class TestSpoken(unittest.TestCase):
    def test_rupees_percent_links(self):
        self.assertEqual(sv.spoken("₹1,350 की बोरी"), "1,350 रुपये की बोरी")
        self.assertEqual(sv.spoken("प्रीमियम 1.5% तक"), "प्रीमियम 1.5 प्रतिशत तक")
        self.assertEqual(sv.spoken("हिसाब taazabhav.com/khad-calculator पर।"), "हिसाब ताज़ा भाव डॉट कॉम पर।")
        self.assertEqual(sv.spoken("₹2,441/क्विंटल"), "2,441 रुपये प्रति क्विंटल")

    def test_helplines_digit_by_digit(self):
        self.assertEqual(sv.spoken("14447 पर कॉल"), "1 4 4 4 7 पर कॉल")
        self.assertEqual(sv.spoken("1800-180-1551 पर"), "1 8 0 0 1 8 0 1 5 5 1 पर")
        self.assertEqual(sv.spoken("₹2,000"), "2,000 रुपये")  # comma amounts untouched
        self.assertIn("120, 60, 40", sv.spoken("120:60:40 किलो"))


class TestOutputs(unittest.TestCase):
    def test_metadata(self):
        title, desc, tags, comment = sv.metadata(item("c"), date(2026, 10, 6))
        self.assertLessEqual(len(title), 100)
        self.assertIn("utm_source=youtube", desc)
        self.assertIn("6 अक्टूबर 2026", desc)
        self.assertIn("https://t.me/taazabhav", desc)
        self.assertIn("DAP Price Today 2026", tags)
        self.assertIn("utm_source=youtube", comment)

    def test_telegram_and_caption_links(self):
        self.assertIn("utm_source=telegram", sv.telegram_text(item("c")))
        cap = sv.meta_caption(item("c"))
        self.assertIn("taazabhav.com/khad-calculator", cap)
        self.assertNotIn("utm_", cap)

    def test_props_timing_follows_voice(self):
        voice = [(f"voice/line{i}.mp3", 2.0) for i in range(5)]
        p = sv.build_props(item("c"), voice, date(2026, 10, 6))
        self.assertEqual([l["from"] for l in p["lines"]], [0, 64, 128, 192, 256])
        self.assertEqual(p["lines"][0]["text"], item("c")["hook_hi"])
        self.assertEqual(p["frames"], 256 + 60 + 4 + 36)
        self.assertEqual(p["link"], "taazabhav.com/khad-calculator")
        self.assertEqual(p["label"], "खाद का सही रेट")

    def test_mode(self):
        with mock.patch.dict(os.environ, {"SAWAL_MODE": "", "SAWAL_LIVE": ""}):
            self.assertEqual(sv.mode(), "preview")
        with mock.patch.dict(os.environ, {"SAWAL_MODE": "", "SAWAL_LIVE": "1"}):
            self.assertEqual(sv.mode(), "publish")
        with mock.patch.dict(os.environ, {"SAWAL_MODE": "preview", "SAWAL_LIVE": "1"}):
            self.assertEqual(sv.mode(), "preview")
        with mock.patch.dict(os.environ, {"SAWAL_MODE": "publish", "SAWAL_LIVE": ""}):
            self.assertEqual(sv.mode(), "publish")


class TestMainPaths(unittest.TestCase):
    def _run(self, mode, items):
        calls = {}
        with tempfile.TemporaryDirectory() as d, \
             mock.patch.object(sv, "PUBLISHED", Path(d) / "pub.json"), \
             mock.patch.object(sv, "load_queue", return_value=items), \
             mock.patch.object(sv, "load_published", return_value={}), \
             mock.patch.object(sv, "make_voice", return_value=[("v.mp3", 2.0)] * 5), \
             mock.patch.object(sv, "render", side_effect=lambda p, o: calls.setdefault("render", p)), \
             mock.patch.object(sv, "send_preview", side_effect=lambda *a: calls.setdefault("preview", a)), \
             mock.patch.object(sv, "mark_published", side_effect=lambda *a: calls.setdefault("marked", a)), \
             mock.patch.object(sv, "_tg", side_effect=lambda *a, **k: calls.setdefault("tg", a)), \
             mock.patch("notify.send_telegram_alert", side_effect=lambda m: calls.setdefault("alert", m)), \
             mock.patch.dict(os.environ, {"SAWAL_MODE": mode, "SAWAL_LIVE": ""}), \
             mock.patch.dict(sys.modules, {"upload_youtube": mock.Mock(upload_video=lambda *a, **k: "VID"),
                                           "meta_publish": mock.Mock(enabled=lambda: False)}):
            rc = sv.main()
        return rc, calls

    def test_preview_never_publishes(self):
        rc, calls = self._run("preview", [item("c")])
        self.assertEqual(rc, 0)
        self.assertIn("preview", calls)
        self.assertNotIn("marked", calls)
        self.assertNotIn("tg", calls)

    def test_publish_marks_and_posts_telegram(self):
        rc, calls = self._run("publish", [item("c")])
        self.assertEqual(rc, 0)
        self.assertEqual(calls["marked"][0], "c")
        self.assertEqual(calls["tg"][0], "sendMessage")

    def test_empty_queue_alerts(self):
        rc, calls = self._run("publish", [item("old", frm="2026-01-01", to="2026-01-02")])
        self.assertEqual(rc, 0)
        self.assertIn("queue is empty", calls["alert"])


if __name__ == "__main__":
    unittest.main()
