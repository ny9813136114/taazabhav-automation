# -*- coding: utf-8 -*-
"""Batch 3 (27 Sep 2026): the story engine picks each slot's state/crop
from the data instead of a fixed list. No network: fetch is injected."""
import os
import shutil
import tempfile
import unittest
from datetime import date
from pathlib import Path

os.environ.setdefault("DATA_GOV_API_KEY", "test-key-not-real")

import pick_story  # noqa: E402
from fetch_prices import DataFetchError  # noqa: E402

RUN_DATE = date(2026, 9, 28)


def rows(state, prices, names=None):
    names = names or [f"M{i} APMC" for i in range(len(prices))]
    return [{"state": state, "market": n, "modal_price": str(p)} for n, p in zip(names, prices)]


def fake_fetch(data):
    def _f(commodity):
        v = data.get(commodity)
        if isinstance(v, Exception):
            raise v
        return v or []
    return _f


class TestScoring(unittest.TestCase):
    def test_too_few_markets_scores_zero(self):
        score, story, _ = pick_story.score_pair(rows("Punjab", [800, 900]))
        self.assertEqual(score, 0.0)
        self.assertIsNone(story)

    def test_wide_gap_is_a_spread_story(self):
        score, story, d = pick_story.score_pair(rows("UP", [5983, 4042, 3000]))
        self.assertEqual(story, "spread")
        self.assertAlmostEqual(d["spread"], 0.994, places=2)

    def test_flat_prices_are_best_mandi_story(self):
        _, story, _ = pick_story.score_pair(rows("UP", [1000, 1010, 1020]))
        self.assertEqual(story, "best")

    def test_big_move_since_yesterday_is_shock(self):
        today = rows("MH", [2600, 2550, 2500])
        yesterday = {"A": {"modal_price": 2000}, "B": 2050, "C": "2000"}
        _, story, d = pick_story.score_pair(today, yesterday)
        self.assertEqual(story, "shock")
        self.assertGreater(d["shock"], 0.2)

    def test_searched_mandi_gets_credit(self):
        plain, _, _ = pick_story.score_pair(rows("Madhya Pradesh", [4000, 4050, 4100]))
        named, story, d = pick_story.score_pair(rows(
            "Madhya Pradesh", [4000, 4050, 4100], ["Mandsaur APMC", "Ratlam APMC", "Ujjain APMC"]))
        self.assertGreater(named, plain)
        self.assertEqual(story, "searched")
        self.assertEqual(d["searched_mandi_volume"], 4126)


class TestRanking(unittest.TestCase):
    def test_ranks_across_crops_and_skips_failed_fetch(self):
        data = {
            "Onion": rows("Uttar Pradesh", [5983, 4042, 3000]) + rows("Punjab", [800, 810, 820]),
            "Garlic": DataFetchError("502 after retries"),
        }
        ranked = pick_story.rank_candidates(
            fetch=fake_fetch(data), load_yesterday=lambda s, c: {},
            commodities=["Onion", "Garlic"], states=["Uttar Pradesh", "Punjab"])
        self.assertEqual([(c["state"], c["commodity"]) for c in ranked],
                         [("Uttar Pradesh", "Onion"), ("Punjab", "Onion")])
        # records are cleaned + sorted highest first, ready for the video
        self.assertEqual(ranked[0]["records"][0]["modal_price"], 5983)


class TestChooseForSlot(unittest.TestCase):
    RANKED = [
        {"state": "Uttar Pradesh", "commodity": "Onion", "score": 2.0, "story": "spread", "details": {}, "records": ["x"]},
        {"state": "Maharashtra", "commodity": "Onion", "score": 1.8, "story": "spread", "details": {}, "records": ["y"]},
        {"state": "Madhya Pradesh", "commodity": "Garlic", "score": 1.5, "story": "searched", "details": {}, "records": ["z"]},
    ]

    def test_first_slot_takes_top_story(self):
        state, commodity, recs, _ = pick_story.choose_for_slot(1, RUN_DATE, lambda d, s, c: False, self.RANKED)
        self.assertEqual((state, commodity, recs), ("Uttar Pradesh", "Onion", ["x"]))

    def test_later_slot_skips_published_and_prefers_new_crop(self):
        published = {("Uttar Pradesh", "Onion")}
        state, commodity, _, _ = pick_story.choose_for_slot(
            2, RUN_DATE, lambda d, s, c: (s, c) in published, self.RANKED)
        # MH onion scores higher, but onion is already done today -> garlic
        self.assertEqual((state, commodity), ("Madhya Pradesh", "Garlic"))

    def test_nothing_left_falls_back_to_old_fixed_target(self):
        state, commodity, recs, reason = pick_story.choose_for_slot(4, RUN_DATE, lambda d, s, c: True, self.RANKED)
        self.assertEqual((state, commodity, recs), ("Karnataka", "Tomato", None))
        self.assertIn("fallback", reason)

    def test_empty_ranking_falls_back(self):
        state, commodity, _, _ = pick_story.choose_for_slot(3, RUN_DATE, lambda d, s, c: False, [])
        self.assertEqual((state, commodity), ("West Bengal", "Potato"))


class TestSnapshot(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self._old = pick_story.STORIES_DIR
        pick_story.STORIES_DIR = Path(self.tmp) / "stories"

    def tearDown(self):
        pick_story.STORIES_DIR = self._old
        shutil.rmtree(self.tmp)

    def test_later_slots_reuse_ranking_without_refetching(self):
        calls = []
        ranked = [{"state": "Uttar Pradesh", "commodity": "Onion", "score": 2.0,
                   "story": "spread", "details": {"spread": 0.99}, "records": [{"market": "A"}]}]
        pick_story.save_snapshot(RUN_DATE, ranked)
        orig = pick_story.rank_candidates
        pick_story.rank_candidates = lambda *a, **k: calls.append(1) or []
        try:
            again = pick_story.ranked_for_today(RUN_DATE)
        finally:
            pick_story.rank_candidates = orig
        self.assertEqual(calls, [])
        self.assertEqual(again[0]["commodity"], "Onion")
        self.assertIsNone(again[0]["records"])  # caller fetches its own pair

    def test_no_snapshot_for_other_day(self):
        pick_story.save_snapshot(RUN_DATE, [{"state": "A", "commodity": "B", "score": 1, "story": "best", "details": {}, "records": []}])
        self.assertIsNone(pick_story.load_snapshot(date(2026, 9, 29)))


if __name__ == "__main__":
    unittest.main()


class TestMainSlotWiring(unittest.TestCase):
    """main() with YT_SLOT set must ask the story engine, then pass the
    chosen pair AND its pre-fetched records to run_pipeline (no refetch)."""

    def test_slot_run_uses_story_engine(self):
        from unittest.mock import patch
        import main
        ranked = [{"state": "Madhya Pradesh", "commodity": "Garlic", "score": 1.5,
                   "story": "searched", "details": {}, "records": [{"market": "Mandsaur APMC", "modal_price": 9000}]}]
        with patch.dict(os.environ, {"YT_SLOT": "1"}, clear=False), \
             patch("pick_story.ranked_for_today", return_value=ranked), \
             patch("main.publish_state.is_published", return_value=False), \
             patch("main.run_pipeline", return_value=main.RESULT_SUCCESS) as rp:
            os.environ.pop("YT_STATE", None)
            code = main.main()
        self.assertEqual(code, 0)
        args, kwargs = rp.call_args
        self.assertEqual(args[:2], ("Madhya Pradesh", "Garlic"))
        self.assertEqual(kwargs["records"][0]["market"], "Mandsaur APMC")

    def test_story_engine_crash_falls_back(self):
        from unittest.mock import patch
        import main
        with patch.dict(os.environ, {"YT_SLOT": "2"}, clear=False), \
             patch("pick_story.ranked_for_today", side_effect=RuntimeError("boom")), \
             patch("main.run_pipeline", return_value=main.RESULT_SUCCESS) as rp:
            main.main()
        self.assertEqual(rp.call_args.args[:2], ("Maharashtra", "Onion"))
        self.assertIsNone(rp.call_args.kwargs["records"])
