# -*- coding: utf-8 -*-
"""FB/IG yojana carousels: own pool, build, picking rules."""
import json
import unittest
from datetime import date

from engine import yojana
from posts import yojana_post as yp

TODAY = date(2026, 11, 11)


class YojanaPost(unittest.TestCase):
    def setUp(self):
        self.items = yojana.load_queue(yp.QUEUE)

    def test_pool_is_separate_from_video_queue(self):
        video = {i["id"] for i in yojana.load_queue()}
        self.assertFalse(video & {i["id"] for i in self.items})
        self.assertNotEqual(yp.QUEUE, yojana.QUEUE)

    def test_items_have_official_source_and_build(self):
        for i in self.items:
            self.assertRegex(i["source"], r"\.(gov|nic)\.in$|\.gov\.in$")
            self.assertTrue(i["checked"])
            p = yp.build(i, TODAY, "am")
            self.assertTrue(p["slides"][0]["kind"] == "hook" and p["slides"][-1]["kind"] == "cta")
            self.assertIn("स्रोत", p["trust"])
            self.assertNotIn("utm", p["caption"].lower())
            self.assertIn(i["source"], p["caption"])

    def test_used_item_never_picked_again(self):
        state = {"history": [], "preview": []}
        seen = set()
        for n in range(len(self.items)):
            it, _ = yp.pick_item("am", date.fromordinal(TODAY.toordinal() + n * 20), state)
            if not it:
                break
            self.assertNotIn(it["id"], seen)
            seen.add(it["id"])
            state["history"].append({"date": TODAY.isoformat(), "slot": "am", "id": it["id"]})
        it, left = yp.pick_item("pm", date(2027, 5, 1), state)
        self.assertEqual(left, 0)
        self.assertIsNone(it)

    def test_slot_prefers_its_formats(self):
        it, _ = yp.pick_item("pm", TODAY, {"history": [], "preview": []})
        self.assertIn(it["format"], yp.SLOTS["pm"]["formats"])


def _rep(slug, name, typical, pct, msp=None, top=3):
    d = {"slug": slug, "nameHi": name, "typical": typical, "markets": 9, "pct": pct, "msp": msp, "states": [],
         "top": [{"marketHi": f"मंडी{i}", "stateHi": "राज्य", "modal": typical + 100 * (top - i)} for i in range(top)]}
    return {"kind": "crop", "date": TODAY.isoformat(), "data": d}


FEED = {"reports": [_rep("wheat", "गेहूं", 2600, 2.5, 2585), _rep("soybean", "सोयाबीन", 4200, -3, 5328),
                    _rep("onion", "प्याज़", 1500, 55), _rep("chana", "चना", 6000, -1.5, 5875)]}


class BhavPosts(unittest.TestCase):
    def test_chaal_drops_glitch_moves(self):
        p = yp.build_bhav("chaal", FEED, TODAY)
        text = json.dumps(p["slides"], ensure_ascii=False)
        self.assertIn("गेहूं", text)
        self.assertNotIn("प्याज़", text)  # +55% in one report: data glitch, not news

    def test_msp_marks_below_msp(self):
        p = yp.build_bhav("msp", FEED, TODAY)
        self.assertIn("सोयाबीन", p["slides"][0]["big"])
        self.assertEqual(p["slides"][-1]["kind"], "cta")

    def test_oonchi_and_thin_data(self):
        self.assertTrue(yp.build_bhav("oonchi", FEED, TODAY))
        self.assertIsNone(yp.build_bhav("oonchi", {"reports": FEED["reports"][:2]}, TODAY))
        self.assertIsNone(yp.build_bhav("msp", {"reports": []}, TODAY))

    def test_price_post_ledger_entry(self):
        p = yp.build_bhav("msp", FEED, TODAY)
        e = yp.ledger_entry(p, TODAY, "pm", None)
        self.assertEqual(e["pillar"], "bhav2")
        self.assertEqual(e["angle"], "msp")


if __name__ == "__main__":
    unittest.main()
