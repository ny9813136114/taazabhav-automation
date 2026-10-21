# -*- coding: utf-8 -*-
import json
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest import mock

from posts import ledger as L
from posts import run

TODAY = date(2026, 11, 3)
POSTS = json.loads(Path("content/tool_posts.json").read_text(encoding="utf-8"))["posts"]


def photo(**kw):
    base = dict(day=TODAY, slot="09:30", fmt="photo", pillar="P3", post_id="x", hook="नया हुक")
    base.update(kw)
    return L.entry(**base)


class RulesTest(unittest.TestCase):
    def test_hook_never_repeats_even_with_spacing_changes(self):
        old = [photo(day=date(2025, 1, 1), hook="सोयाबीन ₹4,800 मिला!")]
        self.assertTrue(L.problems(photo(hook="सोयाबीन  ₹4,800 मिला"), old, TODAY))
        self.assertFalse(L.problems(photo(hook="सोयाबीन ₹4,900 मिला"), old, TODAY))

    def test_one_photo_per_crop_per_day_reels_and_roundups_dont_count(self):
        day = [photo(hook="a", crop="soybean")]
        self.assertTrue(L.problems(photo(hook="b", crop="soybean"), day, TODAY))
        reel = [L.entry(day=TODAY, slot="07:30", fmt="reel", pillar="A", post_id="k", hook="r", crop="soybean")]
        self.assertFalse(L.problems(photo(hook="b", crop="soybean"), reel, TODAY))
        roundup = [L.entry(day=TODAY, slot="14:30", fmt="photo", pillar="bhav", post_id="b", hook="r", crops=["soybean"])]
        self.assertFalse(L.problems(photo(hook="b", crop="soybean"), roundup, TODAY))
        yesterday = [photo(day=date(2026, 11, 2), hook="a", crop="soybean", angle="msp")]
        self.assertFalse(L.problems(photo(hook="b", crop="soybean", angle="bhavantar"), yesterday, TODAY))

    def test_tool_14_days_and_never_todays_reel(self):
        old = [photo(day=date(2026, 10, 21), hook="a", tool="khad")]
        self.assertTrue(L.problems(photo(hook="b", tool="khad"), old, TODAY))
        older = [photo(day=date(2026, 10, 20), hook="a", tool="khad")]
        self.assertFalse(L.problems(photo(hook="b", tool="khad"), older, TODAY))
        reel = [L.entry(day=TODAY, slot="12:30", fmt="reel", pillar="D", post_id="khad|1", hook="r", tool="khad")]
        self.assertTrue(L.problems(photo(hook="b", tool="khad"), reel, TODAY))
        self.assertTrue(L.problems(photo(hook="b", tool="khad"), reel, TODAY, skip=("tool_days",)))
        self.assertFalse(L.problems(photo(hook="b", tool="khad"), old, TODAY, skip=("tool_days",)))

    def test_tool_rule_only_for_posts_about_a_tool(self):
        old = [photo(day=date(2026, 10, 27), hook="a", pillar="P2", tool="hisab")]
        self.assertFalse(L.problems(photo(hook="b", pillar="P2", tool="hisab"), old, TODAY))
        p3 = [photo(day=date(2026, 10, 27), hook="a", pillar="P3", tool="hisab")]
        self.assertFalse(L.problems(photo(hook="b", pillar="P2", tool="hisab"), p3, TODAY))
        self.assertTrue(L.problems(photo(hook="b", pillar="tool", tool="hisab"), p3, TODAY))

    def test_topic_30_days(self):
        old = [photo(day=date(2026, 10, 5), hook="a", crop="wheat", state="rajasthan", angle="khad")]
        self.assertTrue(L.problems(photo(hook="b", crop="wheat", state="rajasthan", angle="khad"), old, TODAY))
        self.assertFalse(L.problems(photo(hook="b", crop="wheat", state="haryana", angle="khad"), old, TODAY))
        self.assertFalse(L.problems(photo(day=date(2026, 11, 4), hook="b", crop="wheat", state="rajasthan", angle="khad"),
                                    old, date(2026, 11, 4)))

    def test_claim_once_until_new_order(self):
        old = [photo(day=date(2025, 1, 1), hook="a", pillar="P5", claim="pmkisan-6000-to-12000|2026-02-01")]
        self.assertTrue(L.problems(photo(hook="b", pillar="P5", claim="pmkisan-6000-to-12000|2026-02-01"), old, TODAY))
        self.assertFalse(L.problems(photo(hook="b", pillar="P5", claim="pmkisan-6000-to-12000|2026-11-01"), old, TODAY))

    def test_state_rotation_oldest_first(self):
        led = [photo(day=date(2026, 10, 27), hook="a", state="madhya-pradesh"),
               photo(day=date(2026, 10, 28), hook="b", state="rajasthan")]
        self.assertEqual(L.next_state(led, "P3"), "maharashtra")
        led = [photo(day=date(2026, 10, 1 + i), hook=str(i), state=s) for i, s in enumerate(L.STATES)]
        self.assertEqual(L.next_state(led, "P3"), "madhya-pradesh")
        self.assertEqual(L.next_state(led, "P1"), "madhya-pradesh")

    def test_record_and_load_one_file_per_post(self):
        with tempfile.TemporaryDirectory() as d:
            L.record(photo(hook="a", post_id="one"), d)
            L.record(L.entry(day=TODAY, slot="12:30", fmt="reel", pillar="D", post_id="khad|1", hook="r"), d)
            self.assertEqual(len(list(Path(d).glob("*.json"))), 2)
            self.assertEqual({e["id"] for e in L.load(d)}, {"one", "khad|1"})

    def test_seeded_ledger_loads(self):
        led = L.load()
        self.assertTrue(any(e["id"] == "bigha-mp" for e in led))
        for e in led:
            self.assertEqual(e["hook_hash"], L.hook_hash(e["hook"]))


class ToolQueueTest(unittest.TestCase):
    def test_every_queued_post_has_its_own_hook(self):
        hashes = [L.hook_hash(L.hook_of(p["caption"])) for p in POSTS]
        self.assertEqual(len(hashes), len(set(hashes)))

    def test_pick_skips_posts_the_ledger_rejects(self):
        q = [{"id": "a", "tool": "khad", "caption": "हुक a"}, {"id": "b", "tool": "bigha", "caption": "हुक b"}]
        used = [run.ledger_entry(q[0], date(2026, 10, 1))]
        with mock.patch.object(run, "d_tool", return_value="none"):
            self.assertEqual(run.pick(q, [], TODAY, used)["id"], "b")
            self.assertIsNone(run.pick(q, [], TODAY, used + [run.ledger_entry(q[1], date(2026, 10, 2))]))

    def test_pick_never_takes_todays_reel_tool(self):
        q = [{"id": "a", "tool": "khad", "caption": "हुक a"}]
        reel = [L.entry(day=TODAY, slot="12:30", fmt="reel", pillar="D", post_id="khad|1", hook="r", tool="khad")]
        with mock.patch.object(run, "d_tool", return_value="none"):
            self.assertIsNone(run.pick(q, [], TODAY, reel))

    def test_engine_reel_is_recorded(self):
        from engine import publish
        ep = {"series": "D", "key": "khad|2", "title": "खाद का हिसाब #Shorts", "tool": "khad"}
        with tempfile.TemporaryDirectory() as d, mock.patch.object(L, "DIR", Path(d)):
            with mock.patch("posts.ledger.safe_record", side_effect=lambda e, root=Path(d): L.record(e, root)):
                publish.ledger_record(ep, {"facebook": "f1", "instagram": None}, TODAY)
            (e,) = L.load(d)
        self.assertEqual((e["format"], e["pillar"], e["tool"], e["slot"], e["hook"]), ("reel", "D", "khad", "12:30", "खाद का हिसाब"))


if __name__ == "__main__":
    unittest.main()
