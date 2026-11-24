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


class SameSchemeNewLook(unittest.TestCase):
    def ep(self, scheme, day, look):
        return {"scheme": scheme, "look": look, "date": day.isoformat()}

    def test_pm_kisan_five_times_five_different_looks(self):
        eps, seen = [], []
        for n in range(5):
            d = date(2026, 11, 11) + timedelta(days=3 * n)
            lk = look.pick_look("pmkisan", d, eps, "pmkisan")
            eps.append(self.ep("pmkisan", d, lk))
            seen.append(lk)
        self.assertEqual(len({x["theme"] for x in seen}), 5)
        self.assertEqual(len({x["clip"] for x in seen}), 5)
        for a, b in zip(seen, seen[1:]):
            self.assertNotEqual(a["voice"], b["voice"])

    def test_two_videos_one_day_never_share_clip_or_voice(self):
        # 13 Nov 2026: Y bhavantar and M mpkalyan both got "harvest" + female voice.
        d = date(2026, 11, 13)
        eps = []
        for scheme in ("bhavantar", "mpkalyan", "pmkisan", "kcc", "other", "more"):
            lk = look.pick_look(scheme, d, eps, scheme)
            if eps:
                self.assertNotEqual(lk["clip"], eps[-1]["look"]["clip"])
                self.assertNotEqual(lk["voice"], eps[-1]["look"]["voice"])
                self.assertNotEqual(lk["theme"], eps[-1]["look"]["theme"])
            eps.append(self.ep(scheme, d, lk))

    def test_never_the_theme_of_the_last_video_of_any_scheme(self):
        eps = [self.ep("kcc", date(2026, 11, 10), {"theme": 2, "clip": "bank", "voice": "male"})]
        for _ in range(10):
            lk = look.pick_look("other", date(2026, 11, 11), eps, "")
            self.assertNotEqual(lk["theme"], 2)

    def test_old_log_entries_without_a_look_are_ignored(self):
        lk = look.pick_look("kcc", date(2026, 11, 11), [{"series": "Y", "key": "kcc"}], "kcc")
        self.assertIn(lk["theme"], range(look.THEME_COUNT))


class StoryStyleTest(unittest.TestCase):
    def test_story_style_never_repeats_within_three_videos(self):
        from datetime import date
        from engine import look
        eps, today = [], date(2026, 11, 23)
        for i in range(20):
            lk = look.pick_look("yojana-x", date.fromordinal(today.toordinal() + i), eps, "x")
            self.assertTrue(0 <= lk["story"] < look.STORY_COUNT)
            self.assertNotIn(lk["story"], [e["look"]["story"] for e in eps[-look.RECENT_STORIES:]])
            eps.append({"scheme": "yojana-x", "look": lk})


class RenderFontsTest(unittest.TestCase):
    def test_every_skin_font_is_shipped_with_the_repo(self):
        import re
        from pathlib import Path
        src = Path("shorts/src/desk/skins.tsx").read_text(encoding="utf-8")
        files = re.findall(r'\["\w+", "([\w.-]+\.ttf)"\]', src)
        self.assertGreaterEqual(len(files), 5)
        media_src = Path("engine/media.py").read_text(encoding="utf-8")
        for f in files:
            self.assertTrue((Path("assets/fonts") / f).exists(), f)
            self.assertIn(f, media_src, f"{f} is not copied by media.render")


class BhavSameWeekTest(unittest.TestCase):
    def test_unchanged_week_does_not_print_rupee_zero(self):
        from engine import qa, stories
        feed = {"latestDate": "2026-11-23", "reports": [], "mandis": [{"state": "MP", "market": "Betul APMC", "marketHi": "बैतूल", "path": "/x",
                "crops": [{"commodity": "Soyabean", "variety": "x", "date": "2026-11-23", "modal": 4500, "min": 4400, "max": 4600,
                           "history": [{"date": "2026-11-17", "modal": 4500}]}]}]}
        ep = stories.build_bhav(feed, date(2026, 11, 24), [])
        qa.check_episode(ep)
        self.assertTrue(any(s.get("big") == "भाव वही" for s in ep["scenes"]))
