# -*- coding: utf-8 -*-
"""PR 5: farmer jawab loop."""
import json
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest import mock

from posts import jawab

FEED = {"reports": [
    {"kind": "crop", "date": "2026-11-06", "data": {"slug": "soybean", "nameHi": "सोयाबीन", "typical": 4700}},
    {"kind": "crop", "date": "2026-11-06", "data": {"slug": "maize", "nameHi": "मक्का", "typical": 2000}},
]}


class ParseTest(unittest.TestCase):
    def test_reads_crop_mandi_price(self):
        self.assertEqual(jawab.parse("नीमच मंडी में सोयाबीन 4650 बिका"), [{"crop": "soybean", "price": 4650, "mandi": "नीमच"}])
        self.assertEqual(jawab.parse("aaj indore mandi soybean 4,720 rs"), [{"crop": "soybean", "price": 4720, "mandi": "Indore"}])
        two = jawab.parse("खातेगांव मंडी: सोयाबीन 4500, मक्का 1900")
        self.assertEqual({(r["crop"], r["price"]) for r in two}, {("soybean", 4500), ("maize", 1900)})

    def test_needs_all_three(self):
        for t in ["हमारी मंडी में धान ₹2300", "bhai link do", "सोयाबीन 4600", "instagram telegram 4500 mandi"]:
            self.assertEqual(jawab.parse(t), [], t)


class LoopTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.p = [mock.patch.object(jawab, n, self.tmp / n.lower()) for n in ("PRICES", "PARCHI", "DRAFTS", "PARCHI_POSTS")]
        for x in self.p:
            x.start()

    def tearDown(self):
        for x in self.p:
            x.stop()

    def _comments(self):
        return [("facebook", "1_a", {"id": "c1", "message": "नीमच मंडी सोयाबीन 4600", "created_time": "2026-11-05T10:00:00+0000"}),
                ("instagram", "m1", {"id": "c2", "text": "Dewas mandi soybean 4550", "timestamp": "2026-11-05T11:00:00+0000"}),
                ("facebook", "1_a", {"id": "c3", "message": "शाजापुर मंडी मक्का 1950", "created_time": "2026-11-06T09:00:00+0000"}),
                ("facebook", "1_a", {"id": "c4", "message": "nice", "created_time": "2026-11-06T09:00:00+0000"})]

    def test_collect_keeps_no_names_and_skips_seen(self):
        prices, parchi = jawab.collect(date(2026, 11, 6), "t", "ig", "taazabhav", fetch=self._comments)
        self.assertEqual(len(prices), 3)
        self.assertEqual(set(prices[0]), {"crop", "price", "mandi", "net", "post", "comment", "date"})
        again, _ = jawab.collect(date(2026, 11, 6), "t", "ig", "taazabhav", fetch=self._comments)
        self.assertEqual(again, [])

    def test_photo_comment_saved_as_parchi(self):
        c = [("facebook", "1_a", {"id": "c9", "message": "मेरी पर्ची", "created_time": "2026-11-06T09:00:00+0000",
                                  "attachment": {"type": "photo", "media": {"image": {"src": "https://cdn/x.jpg"}}}})]
        r = mock.Mock(content=b"jpg"); r.raise_for_status = lambda: None
        with mock.patch.object(jawab.requests, "get", return_value=r):
            _, parchi = jawab.collect(date(2026, 11, 6), "t", None, None, fetch=lambda: c)
        idx = json.loads((jawab.PARCHI / "index.json").read_text())
        self.assertEqual(idx[0]["file"], "2026-11-06-9.jpg")
        self.assertNotIn("image", idx[0])
        self.assertEqual((jawab.PARCHI / "2026-11-06-9.jpg").read_bytes(), b"jpg")

    def test_p1_from_farmers_hides_names_and_drops_outliers(self):
        jawab.collect(date(2026, 11, 6), "t", None, None, fetch=self._comments)
        reps = jawab.week_reports(date(2026, 11, 6))
        reps.append({"crop": "soybean", "price": 470, "mandi": "Typo", "date": "2026-11-06", "comment": "x"})
        post = jawab.build_p1_farmers(FEED, date(2026, 11, 7), reps)
        rows = post["slides"][1]["rows"]
        self.assertEqual(len(rows), 3)
        self.assertNotIn("Typo", json.dumps(post, ensure_ascii=False))
        self.assertIn("₹4,700", rows[0][1])
        self.assertIn("किसानों के कमेंट", post["trust"])

    def test_too_few_reports_no_post(self):
        self.assertIsNone(jawab.build_p1_farmers(FEED, date(2026, 11, 7), [
            {"crop": "soybean", "price": 4600, "mandi": "A", "date": "2026-11-06"}]))

    def test_approval_needs_owner_haan_after_request(self):
        jawab._save(jawab.DRAFTS / "approvals.json", {"P1-2026-11-07": {"message_id": 50, "sent": 1000}})
        msg = lambda text, when=2000, chat=7, reply=None: {"message": {"chat": {"id": chat}, "date": when, "text": text,
                                                                         **({"reply_to_message": {"message_id": reply}} if reply else {})}}
        with mock.patch.object(jawab, "_owner", return_value="7"):
            self.assertTrue(jawab.approved("P1-2026-11-07", [msg("Haan")]))
            self.assertTrue(jawab.approved("P1-2026-11-07", [msg("हाँ ठीक है", reply=50)]))
            self.assertFalse(jawab.approved("P1-2026-11-07", [msg("haan", when=900)]))
            self.assertFalse(jawab.approved("P1-2026-11-07", [msg("haan", chat=8)]))
            self.assertFalse(jawab.approved("P1-2026-11-07", [msg("hatao isko")]))
            self.assertFalse(jawab.approved("P1-2026-11-07", [msg("haan", reply=49)]))
            self.assertFalse(jawab.approved("P2-2026-11-08", [msg("haan")]))

    def test_draft_only_on_p1_p2_eve(self):
        jawab.collect(date(2026, 11, 6), "t", None, None, fetch=self._comments)
        self.assertTrue(jawab.needs_draft(date(2026, 11, 6)))   # 7 Nov is P1
        self.assertFalse(jawab.needs_draft(date(2026, 11, 3)))  # 4 Nov is not
        self.assertFalse(jawab.needs_draft(date(2026, 11, 7)))  # 8 Nov P2, no read parchi yet
        with mock.patch.object(jawab, "request_approval") as ask:
            key = jawab.make_drafts(date(2026, 11, 6), lambda: FEED, render=lambda post, d: ["a.png"])
        self.assertEqual(key, "P1-2026-11-07")
        ask.assert_called_once()
        self.assertEqual(json.loads((jawab.DRAFTS / "2026-11-07.json").read_text())["pillar"], "P1")


if __name__ == "__main__":
    unittest.main()
