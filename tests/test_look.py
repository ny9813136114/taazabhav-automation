# -*- coding: utf-8 -*-
import os
import unittest
from datetime import date, timedelta
from unittest import mock

from engine import look, media, yojana


class LookTest(unittest.TestCase):
    def test_voice_alternates_by_day(self):
        with mock.patch.dict(os.environ, {"ENGINE_VOICE": ""}):
            names = [media.voice_for(date(2026, 11, 1) + timedelta(days=i)) for i in range(6)]
        self.assertEqual(set(names), set(media.VOICES.values()))
        self.assertTrue(all(a != b for a, b in zip(names, names[1:])))

    def test_engine_voice_forces_one(self):
        with mock.patch.dict(os.environ, {"ENGINE_VOICE": "hi-IN-SwaraNeural"}):
            self.assertEqual({media.voice_for(date(2026, 11, d)) for d in range(1, 8)}, {"hi-IN-SwaraNeural"})

    def test_theme_changes_every_day(self):
        days = [date(2026, 11, 1) + timedelta(days=i) for i in range(30)]
        themes = [look.theme_for(d) for d in days]
        self.assertTrue(all(a != b for a, b in zip(themes, themes[1:])))
        self.assertEqual(set(themes), set(range(look.THEME_COUNT)))

    def test_theme_count_matches_remotion(self):
        src = open("shorts/src/desk/theme.ts", encoding="utf-8").read()
        self.assertEqual(src.count("enter: \""), look.THEME_COUNT)

    def test_clip_folders_exist(self):
        for folder in [f for _, f in look.CLIP_HINTS] + list(look.ROTATE):
            self.assertIn(folder, media.CLIP_QUERIES)

    def test_clip_follows_scheme_words(self):
        d = date(2026, 11, 11)
        self.assertEqual(look.clip_for("kusum-solar-pump", d), "solar")
        self.assertEqual(look.clip_for("kcc-5-lakh", d), "bank")
        self.assertIn(look.clip_for("something-else", d), look.ROTATE)

    def test_queue_gets_varied_clips(self):
        items = yojana.load_queue()
        clips = {look.clip_for(i["id"], date(2026, 11, 11), i.get("scheme", "")) for i in items}
        self.assertGreaterEqual(len(clips), 4)

    def test_y_episode_carries_theme_and_clip(self):
        ep = yojana.build_y(date(2026, 11, 11), {"episodes": []}, yojana.load_queue())
        self.assertEqual(ep["theme"], look.theme_for(date(2026, 11, 11)))
        self.assertIn(ep["clip"], media.CLIP_QUERIES)


if __name__ == "__main__":
    unittest.main()
