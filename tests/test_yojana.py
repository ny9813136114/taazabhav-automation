# -*- coding: utf-8 -*-
"""Series Y (योजना की बात, 3 Nov 2026): queue checks, picking rules, QA and length."""
import os
import re
import unittest
from datetime import date, timedelta
from unittest import mock

from engine import qa, yojana
from tests.test_engine import estimate_secs, fitted

TODAY = date(2026, 11, 4)
# taazabhav.com pages a Y video may send people to (all live on 3 Nov 2026).
SITE_PAGES = {
    "/pm-kisan-kist", "/farmer-id", "/kisan-credit-card", "/fasal-bima-2026", "/fasal-nuksan", "/khad-calculator",
    "/khad-rate", "/mp-khad-e-token", "/krishi-yantra-anudan", "/pm-kusum-yojana", "/bhavantar-calculator",
    "/msp-vs-mandi", "/gehu-kharid", "/dhan-kharid", "/mitti-jaanch", "/kheti-lagat-munafa", "/pala-alert",
    "/raj-kisan-sathi", "/bihar-dbt-agriculture", "/mahadbt-farmer", "/meri-fasal-mera-byora", "/rabi-buvai-2026",
}
OFFICIAL = re.compile(r"(\.gov\.in|\.nic\.in|^rbi\.org\.in|^sbi\.co\.in)$")


def state(*eps):
    return {"episodes": [{"series": "Y", "key": k, "date": d.isoformat()} for k, d in eps]}


class QueueTest(unittest.TestCase):
    def setUp(self):
        self.items = yojana.load_queue()

    def test_queue_is_well_formed(self):
        self.assertGreaterEqual(len(self.items), 30)
        ids = [i["id"] for i in self.items]
        self.assertEqual(len(ids), len(set(ids)))
        for i in self.items:
            self.assertEqual(len(i["facts"]), 3, i["id"])
            self.assertIn(i["tool"]["path"], SITE_PAGES, i["id"])
            self.assertRegex(i["source"], OFFICIAL, i["id"])
            self.assertIn(i["scope"], ("central", "state"))
            self.assertTrue(i["basis"], f"{i['id']} has no basis (which site page the facts came from)")
            for part in (i["hook"], *i["facts"], i["tool"]):
                self.assertLessEqual(len(part["big"]), 18, f"{i['id']}: {part['big']}")
                self.assertTrue(part["say"].strip(), i["id"])
            self.assertNotIn("utm_", str(i))

    def test_voice_never_reads_rupee_lakh_wrong(self):
        # spoken() turns "₹2 लाख" into "2 रुपये लाख"; voice lines must say amounts in words.
        for i in self.items:
            for part in (i["hook"], *i["facts"], i["tool"]):
                self.assertNotRegex(part["say"], r"₹\s*[\d.,]+\s*(लाख|करोड़|हज़ार)", i["id"])

    def test_every_item_passes_qa_and_fits(self):
        for n, it in enumerate(self.items):
            day = date.fromisoformat(it["validFrom"]) if it.get("validFrom") else TODAY
            ep = yojana.build_y(day, {"episodes": []}, [it])
            self.assertIsNotNone(ep, it["id"])
            qa.check_episode(ep)
            secs = estimate_secs(fitted(ep))
            lo, hi = qa.BOUNDS["Y"]
            self.assertTrue(lo <= secs <= hi, f"{it['id']}: about {secs:.1f}s, allowed {lo}-{hi}s")
            self.assertIn(f"taazabhav.com{it['tool']['path']}", ep["scenes"][-1]["sub"])
            self.assertEqual(ep["scenes"][-1]["kind"], "cta")
            self.assertIn(it["source"], ep["description"])


class PickTest(unittest.TestCase):
    items = [
        {"id": "a1", "scheme": "a"}, {"id": "a2", "scheme": "a"}, {"id": "a3", "scheme": "a"},
        {"id": "b1", "scheme": "b"}, {"id": "old", "scheme": "c", "validUntil": "2026-11-01"},
        {"id": "later", "scheme": "d", "validFrom": "2026-12-01"},
    ]

    def test_first_never_shown_in_queue_order(self):
        self.assertEqual(yojana.pick(self.items, TODAY, state())["id"], "a1")

    def test_no_repeat_within_15_days(self):
        s = state(("a1", TODAY - timedelta(days=14)), ("a2", TODAY - timedelta(days=13)), ("a3", TODAY - timedelta(days=12)), ("b1", TODAY - timedelta(days=11)))
        self.assertIsNone(yojana.pick(self.items, TODAY, s))
        s = state(("a1", TODAY - timedelta(days=15)), ("a2", TODAY - timedelta(days=13)), ("a3", TODAY - timedelta(days=12)), ("b1", TODAY - timedelta(days=11)))
        self.assertEqual(yojana.pick(self.items, TODAY, s)["id"], "a1")

    def test_scheme_at_most_twice_a_week(self):
        s = state(("a1", TODAY - timedelta(days=1)), ("a2", TODAY - timedelta(days=2)))
        self.assertEqual(yojana.pick(self.items, TODAY, s)["id"], "b1")

    def test_expired_and_not_yet_valid_are_skipped(self):
        s = state(("a1", TODAY - timedelta(days=1)), ("a2", TODAY - timedelta(days=2)), ("b1", TODAY - timedelta(days=3)))
        self.assertIsNone(yojana.pick(self.items, TODAY, s))
        self.assertEqual(yojana.pick(self.items, date(2026, 12, 1), s)["id"], "a3")

    def test_oldest_shown_goes_first_when_all_used(self):
        s = state(("a1", TODAY - timedelta(days=40)), ("a2", TODAY - timedelta(days=60)), ("a3", TODAY - timedelta(days=50)), ("b1", TODAY - timedelta(days=30)))
        self.assertEqual(yojana.pick(self.items, TODAY, s)["id"], "a2")

    def test_fresh_count(self):
        s = state(("a1", TODAY - timedelta(days=1)))
        self.assertEqual(yojana.fresh_count(self.items, TODAY, s), 3)

    def test_other_series_do_not_count(self):
        s = {"episodes": [{"series": "D", "key": "a1", "date": TODAY.isoformat()}]}
        self.assertEqual(yojana.pick(self.items, TODAY, s)["id"], "a1")


class ModeTest(unittest.TestCase):
    def test_y_is_preview_until_yojana_live(self):
        from engine.run import mode
        with mock.patch.dict(os.environ, {"ENGINE_MODE": "auto", "ENGINE_LIVE": "1", "YOJANA_LIVE": ""}):
            self.assertEqual(mode("Y"), "preview")
            self.assertEqual(mode("B"), "publish")
        with mock.patch.dict(os.environ, {"ENGINE_MODE": "auto", "ENGINE_LIVE": "1", "YOJANA_LIVE": "1"}):
            self.assertEqual(mode("Y"), "publish")
        with mock.patch.dict(os.environ, {"ENGINE_MODE": "publish", "YOJANA_LIVE": ""}):
            self.assertEqual(mode("Y"), "publish")

    def test_y_has_slot_playlist_and_meta(self):
        import meta_publish
        from engine import publish, slot_gate
        self.assertEqual(slot_gate.SLOTS["Y"], (12, 30))
        self.assertIn("Y", publish.PLAYLIST_NAMES)
        with mock.patch.dict(os.environ, {"META_ON": ""}):
            self.assertTrue(meta_publish.on_meta("Y"))
        with mock.patch.dict(os.environ, {"YT_SERIES": ""}):
            self.assertTrue(publish.on_youtube("Y"))


if __name__ == "__main__":
    unittest.main()
