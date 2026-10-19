# -*- coding: utf-8 -*-
"""Content engine (engine/): story picking, QA rules and props timing on a
fixed copy of the /api/yt-feed response. No network, no rendering."""
import os
import unittest
from datetime import date
from pathlib import Path

from engine import feed as F
from engine import media, qa, stories, tools
from engine.claims import top_claim
from engine.text import inr, spoken

FIXTURE = Path(__file__).parent / "fixtures" / "engine_feed.json"
TODAY = date(2026, 10, 17)  # a Saturday


def load():
    os.environ["ENGINE_FEED_FILE"] = str(FIXTURE)
    try:
        return F.load_feed(TODAY)
    finally:
        del os.environ["ENGINE_FEED_FILE"]


def fake_voice(ep):
    return [{"audio": f"voice/s{i}.mp3", "secs": 2.0, "words": [{"w": "क", "t": 0.0}]} for i, _ in enumerate(ep["scenes"])]


class TextTest(unittest.TestCase):
    def test_inr_indian_grouping(self):
        self.assertEqual(inr(1234567), "₹12,34,567")
        self.assertEqual(inr(950), "₹950")

    def test_spoken_rewrites_money_and_percent(self):
        self.assertEqual(spoken("₹5,180 ▲ 10%"), "5180 रुपये 10 प्रतिशत")


class SeriesATest(unittest.TestCase):
    def test_picks_biggest_priority_state_move(self):
        ep = stories.build_a(load(), TODAY, set())
        self.assertEqual(ep["key"], "Onion|Lasalgaon")  # -14.7% beats +10.2%
        qa.check_episode(ep)
        self.assertLessEqual(len(ep["title"]), 100)

    def test_skips_recent_story(self):
        ep = stories.build_a(load(), TODAY, {"Onion|Lasalgaon"})
        self.assertEqual(ep["key"], "Soyabean|Indore")


class SeriesBTest(unittest.TestCase):
    def test_no_date_without_official_date(self):
        ep = stories.build_b(load(), TODAY, set(), claim={"date": "2026-10-20", "count": 5})
        qa.check_episode(ep)
        self.assertEqual(ep["key"].split("|")[0], "pmkisan")
        for s in ep["scenes"]:
            self.assertNotIn("20 अक्टूबर को आएगी", s.get("say", ""))

    def test_official_date_goes_first(self):
        feed = load()
        feed["kist"][1]["next"]["officialDate"] = "2026-10-25"
        ep = stories.build_b(feed, TODAY, set())
        self.assertEqual(ep["key"], "mpkalyan|announced|2026-10-25")


class SeriesCTest(unittest.TestCase):
    def test_three_news_items(self):
        ep = stories.build_c(load(), TODAY, set())
        qa.check_episode(ep)
        self.assertEqual(len([s for s in ep["scenes"] if s["kind"] == "news"]), 3)


class SeriesDTest(unittest.TestCase):
    def test_rotates_tools(self):
        first = tools.build_d(TODAY, set())
        second = tools.build_d(TODAY, {first["key"]})
        self.assertNotEqual(first["key"], second["key"])
        qa.check_episode(first)


class PropsTest(unittest.TestCase):
    def test_scenes_are_back_to_back_with_loop_beat(self):
        ep = stories.build_a(load(), TODAY, set())
        props = media.build_props(ep, fake_voice(ep))
        end = 0
        for s in props["scenes"]:
            self.assertEqual(s["from"], end)
            end += s["frames"]
        self.assertEqual(end, props["frames"])
        self.assertEqual(props["scenes"][-1]["frames"], 15)
        qa.check_length(ep, props["frames"] / media.FPS)

    def test_a_voice_is_short(self):
        # 19 Oct 2026: A ran 30.7 s with the Madhur voice (limit 26 s) and the
        # slot was skipped. About 13 spoken characters a second, so stay near 12-15 s.
        ep = stories.build_a(load(), TODAY, set())
        self.assertLess(sum(len(spoken(s["say"])) for s in ep["scenes"]), 160)
        self.assertTrue(any(s.get("optional") for s in ep["scenes"]))


# Real Madhur voice speed at +8%, measured on the 19 Oct 2026 B run: about
# 315 spoken characters gave 31.9 s of video. Kept slightly pessimistic.
CHARS_PER_SEC = 10.0


def estimate_secs(ep):
    total = 0.5
    for s in ep["scenes"]:
        total += max(len(spoken(s["say"])) / CHARS_PER_SEC + 0.25, media.MIN_SCENE_S.get(s["kind"], 1.4))
    return total


def fitted(ep):
    """What engine.run does at normal speed: drop optional scenes while too long."""
    ep = {**ep, "scenes": list(ep["scenes"])}
    while estimate_secs(ep) > qa.BOUNDS[ep["series"]][1]:
        spare = next((s for s in ep["scenes"] if s.get("optional")), None)
        if not spare:
            break
        ep["scenes"].remove(spare)
    return ep


class LengthTest(unittest.TestCase):
    """19 Oct 2026: A (30.7 s) and then B (31.9 s) were skipped for running over
    their limit. Every series and variant must fit at normal voice speed, so the
    faster-voice fallback in engine.run is only a safety net."""

    def episodes(self):
        feed = load()
        yield stories.build_a(feed, TODAY, set())
        yield stories.build_b(feed, TODAY, set(), claim={"date": "2026-10-25", "count": 7})
        yield stories.build_b(feed, TODAY, set())
        announced = load()
        announced["kist"][0]["next"]["officialDate"] = "2026-10-25"
        yield stories.build_b(announced, TODAY, set())
        yield stories.build_c(feed, TODAY, set())
        seen = set()
        while True:
            ep = tools.build_d(TODAY, seen)
            if not ep or ep["key"] in seen:
                break
            seen.add(ep["key"])
            yield ep

    def test_every_series_fits_at_normal_speed(self):
        n = 0
        for ep in self.episodes():
            n += 1
            secs = estimate_secs(fitted(ep))
            lo, hi = qa.BOUNDS[ep["series"]]
            self.assertLessEqual(secs, hi, f"{ep['series']} {ep['key']}: about {secs:.1f}s, limit {hi}s")
            self.assertGreaterEqual(secs, lo, f"{ep['series']} {ep['key']}: about {secs:.1f}s, minimum {lo}s")
        self.assertGreater(n, 5)

    def test_speed_fallback_steps(self):
        from engine.run import SPEEDS
        self.assertEqual(SPEEDS[0], "+8%")
        self.assertEqual([media._speed(r) for r in SPEEDS], [1.08, 1.18, 1.28])


class StateTest(unittest.TestCase):
    def test_recent_keys_window(self):
        state = {"episodes": []}
        F.mark(state, "A", "Onion|Lasalgaon", date(2026, 10, 10))
        F.mark(state, "A", "Garlic|Neemuch", date(2026, 10, 16))
        self.assertEqual(F.recent_keys(state, "A", TODAY, 7), {"Garlic|Neemuch"})


class ClaimTest(unittest.TestCase):
    def test_top_claim_needs_three_titles(self):
        titles = ["PM Kisan 24th kist 20 October ko", "24वीं किस्त 20 अक्टूबर", "pm kisan 20 oct date fix", "kist 25 October"]
        self.assertEqual(top_claim(titles, TODAY)["date"], "2026-10-20")
        self.assertIsNone(top_claim(titles[:2], TODAY))


if __name__ == "__main__":
    unittest.main()


class MetaReelsTest(unittest.TestCase):
    EP = {"series": "A", "title": "₹4,500 सोयाबीन! | Soybean Rate Today #Shorts",
          "description": "भाव: https://taazabhav.com/x\n#मंडीभाव"}

    def test_caption_drops_shorts_tag_keeps_plain_links(self):
        from engine.publish import meta_caption
        cap = meta_caption(self.EP)
        self.assertTrue(cap.startswith("₹4,500 सोयाबीन! | Soybean Rate Today\n\n"))
        self.assertNotIn("#Shorts", cap)
        self.assertIn("https://taazabhav.com/x\n", cap)
        self.assertNotIn("utm_", cap)

    def test_meta_error_only_alerts(self):
        from unittest import mock
        import meta_publish
        from engine.publish import meta_reels
        alerts = []
        with mock.patch.object(meta_publish, "enabled", return_value=True), \
                mock.patch.object(meta_publish, "publish_all", side_effect=RuntimeError("boom")):
            meta_reels("x.mp4", self.EP, alerts.append)
        self.assertEqual(len(alerts), 1)
        self.assertIn("boom", alerts[0])

    def test_skipped_without_secrets(self):
        from unittest import mock
        import meta_publish
        from engine.publish import meta_reels
        with mock.patch.object(meta_publish, "enabled", return_value=False), \
                mock.patch.object(meta_publish, "publish_all") as pa:
            self.assertIsNone(meta_reels("x.mp4", self.EP, print))
        pa.assert_not_called()
