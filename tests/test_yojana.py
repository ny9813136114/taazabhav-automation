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
    "/bigha-to-acre", "/sarkari-paisa",
}
OFFICIAL = re.compile(r"(\.gov\.in|\.nic\.in|^rbi\.org\.in|^sbi\.co\.in|\.mahait\.org)$")  # mahait.org: Maharashtra govt IT


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
            self.assertIn(len(i["facts"]), (2, 3), i["id"])
            self.assertIn(i["format"], yojana.FORMATS, i["id"])
            if i["format"] == "sach":
                self.assertIn("verdict", i, i["id"])
            self.assertIn(i["tool"]["path"], SITE_PAGES, i["id"])
            self.assertRegex(i["source"], OFFICIAL, i["id"])
            self.assertIn(i["scope"], ("central", "state"))
            self.assertTrue(i["basis"], f"{i['id']} has no basis (which site page the facts came from)")
            for part in (i["hook"], *i["facts"], i["tool"]):
                self.assertLessEqual(len(part.get("big", "")), 18, f"{i['id']}: {part.get('big')}")
                for it in part.get("items", []):
                    self.assertLessEqual(len(it["value"]), 16, i["id"])
                self.assertTrue(part["say"].strip(), i["id"])
            self.assertNotIn("utm_", str(i))

    def test_voice_never_reads_rupee_lakh_wrong(self):
        # spoken() turns "₹2 लाख" into "2 रुपये लाख"; voice lines must say amounts in words.
        for i in self.items:
            for part in (i["hook"], *i["facts"], i["tool"], *([i["verdict"]] if "verdict" in i else [])):
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
    # TODAY (4 Nov 2026) is a Wednesday: format "kitna".
    items = [
        {"id": "s1", "scheme": "a", "format": "state", "state": "TG"},
        {"id": "k1", "scheme": "a", "format": "kitna"},
        {"id": "k2", "scheme": "b", "format": "kitna"},
        {"id": "s2", "scheme": "c", "format": "state", "state": "TG"},
        {"id": "old", "scheme": "d", "format": "kitna", "validUntil": "2026-11-01"},
        {"id": "later", "scheme": "e", "format": "kitna", "validFrom": "2026-12-01"},
    ]

    def test_todays_format_first(self):
        self.assertEqual(TODAY.weekday(), 2)
        self.assertEqual(yojana.pick(self.items, TODAY, state())["id"], "k1")
        self.assertEqual(yojana.pick(self.items, TODAY - timedelta(days=2), state())["id"], "s1")  # Monday

    def test_never_repeats_an_item(self):
        s = state(*[(i["id"], TODAY - timedelta(days=300)) for i in self.items])
        self.assertIsNone(yojana.pick(self.items, TODAY, s))

    def test_scheme_gap(self):
        s = state(("s1", TODAY - timedelta(days=13)))
        self.assertEqual(yojana.pick(self.items, TODAY, s)["id"], "k2")
        s = state(("s1", TODAY - timedelta(days=14)))
        self.assertEqual(yojana.pick(self.items, TODAY, s)["id"], "k1")

    def test_state_gap(self):
        s = state(("s1", TODAY - timedelta(days=6)), ("k1", TODAY - timedelta(days=40)), ("k2", TODAY - timedelta(days=40)))
        self.assertIsNone(yojana.pick(self.items, TODAY, s))
        s = state(("s1", TODAY - timedelta(days=7)), ("k1", TODAY - timedelta(days=40)), ("k2", TODAY - timedelta(days=40)))
        self.assertEqual(yojana.pick(self.items, TODAY, s)["id"], "s2")

    def test_other_format_when_today_is_empty(self):
        s = state(("k1", TODAY - timedelta(days=30)), ("k2", TODAY - timedelta(days=30)))
        self.assertEqual(yojana.pick(self.items, TODAY, s)["id"], "s1")

    def test_dates(self):
        s = state(("s1", TODAY - timedelta(days=30)), ("k1", TODAY - timedelta(days=30)), ("k2", TODAY - timedelta(days=30)), ("s2", TODAY - timedelta(days=30)))
        self.assertIsNone(yojana.pick(self.items, TODAY, s))
        self.assertEqual(yojana.pick(self.items, date(2026, 12, 2), s)["id"], "later")

    def test_fresh_count(self):
        self.assertEqual(yojana.fresh_count(self.items, TODAY, state(("s1", TODAY))), 3)

    def test_other_series_do_not_count(self):
        s = {"episodes": [{"series": "D", "key": "k1", "date": TODAY.isoformat()}]}
        self.assertEqual(yojana.pick(self.items, TODAY, s)["id"], "k1")


class FormatTest(unittest.TestCase):
    def test_every_weekday_has_items(self):
        fmts = {i["format"] for i in yojana.load_queue()}
        self.assertEqual(fmts, set(yojana.WEEKDAY_FORMAT))

    def test_sach_shows_claim_then_verdict(self):
        it = next(i for i in yojana.load_queue() if i["format"] == "sach")
        ep = yojana.build_y(TODAY, {"episodes": []}, [it])
        self.assertEqual([s["kind"] for s in ep["scenes"][:2]], ["claim", "stamp"])
        self.assertEqual(ep["badge"], "सच या झूठ")

    def test_deadline_counts_down_and_expires(self):
        it = next(i for i in yojana.load_queue() if i["id"] == "rabi-buvai")
        ep = yojana.build_y(date(2026, 11, 10), {"episodes": []}, [it])
        self.assertEqual(ep["scenes"][1]["big"], "10 दिन बाकी")
        self.assertIsNone(yojana.build_y(date(2026, 11, 21), {"episodes": []}, [it]))


class ModeTest(unittest.TestCase):
    def test_y_posts_unless_yojana_live_0(self):
        from engine.run import mode
        with mock.patch.dict(os.environ, {"ENGINE_MODE": "auto", "ENGINE_LIVE": "1", "YOJANA_LIVE": ""}):
            self.assertEqual(mode("Y"), "publish")
        with mock.patch.dict(os.environ, {"ENGINE_MODE": "auto", "ENGINE_LIVE": "1", "YOJANA_LIVE": "0"}):
            self.assertEqual(mode("Y"), "preview")
            self.assertEqual(mode("B"), "publish")

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


class MpKalyanDailyTest(unittest.TestCase):
    """12 Nov 2026: MP Kisan Kalyan daily Meta Reel (engine/mpkalyan.py)."""

    def test_three_angles_pass_qa_and_fit(self):
        from engine import mpkalyan
        seen = set()
        for n in range(6):
            ep = mpkalyan.build_m(date(2026, 11, 13) + timedelta(days=n))
            qa.check_episode(ep)
            seen.add(ep["title"])
            self.assertTrue(ep["meta_only"])
            self.assertEqual(ep["scheme"], "mpkalyan")
            self.assertEqual(ep["series"], "Y")
            self.assertTrue(estimate_secs(fitted(ep)) <= qa.BOUNDS["Y"][1], ep["key"])
        self.assertEqual(len(seen), 3)

    def test_no_made_up_numbers(self):
        from engine import mpkalyan
        for n in range(3):
            ep = mpkalyan.build_m(date(2026, 11, 13) + timedelta(days=n))
            blob = " ".join(s.get("big", "") + s.get("say", "") for s in ep["scenes"])
            self.assertNotRegex(blob, r"₹\s*\d")

    def test_meta_only_skips_youtube(self):
        from engine import mpkalyan, publish
        ep = mpkalyan.build_m(date(2026, 11, 13))
        with mock.patch.object(publish, "meta_reels") as m, mock.patch("upload_youtube.upload_video") as up:
            self.assertIsNone(publish.publish("x.mp4", ep, lambda *_: None))
        up.assert_not_called()
        m.assert_called_once()
