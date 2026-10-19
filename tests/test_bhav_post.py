# -*- coding: utf-8 -*-
import unittest
from datetime import date

from posts import bhav

DAY = "2026-10-19"


def crop(slug, name, typical, markets=5, msp=None, pct=None, day=DAY):
    return {"date": day, "kind": "crop", "data": {
        "slug": slug, "nameHi": name, "typical": typical, "markets": markets, "msp": msp, "pct": pct,
        "states": [{"state": "Madhya Pradesh", "stateHi": "मध्य प्रदेश", "markets": 3, "typical": typical - 100},
                   {"state": "Gujarat", "stateHi": "गुजरात", "markets": 2, "typical": typical + 100}],
        "top": [{"marketHi": "सैलाना", "stateHi": "मध्य प्रदेश", "modal": typical + 700},
                {"marketHi": "भेसन", "stateHi": "गुजरात", "modal": typical + 400}]}}


FEED = {"latestDate": DAY, "reports": [
    crop("onion", "प्याज़", 4290),
    crop("soybean", "सोयाबीन", 6600, msp=5708, pct=-0.9),
    crop("cotton", "कपास", 8825, msp=8267),
    crop("rare", "दुर्लभ", 1000, markets=1),
    crop("wheat", "गेहूं", 2550, day="2026-10-18"),
    {"date": DAY, "kind": "state", "data": {"slug": "x"}},
]}


class BhavPostTest(unittest.TestCase):
    def test_rupee_format(self):
        self.assertEqual(bhav.rs(6600), "₹6,600")
        self.assertEqual(bhav.rs(123456), "₹1,23,456")
        self.assertEqual(bhav.rs(950), "₹950")

    def test_picks_todays_main_crops_in_priority(self):
        names = [r["data"]["slug"] for r in bhav.crop_reports(FEED, DAY)]
        self.assertEqual(names, ["soybean", "cotton", "onion"])  # no thin, old or state reports

    def test_post_fits_meta_limits(self):
        p = bhav.build(FEED, date(2026, 10, 19))
        self.assertEqual(p["id"], "bhav-2026-10-19")
        self.assertTrue(2 <= len(p["slides"]) <= 10)
        self.assertEqual(p["slides"][0]["kind"], "hook")
        self.assertEqual(p["slides"][-1]["kind"], "cta")
        self.assertLessEqual(len(p["caption"]), 2200)
        soy = p["slides"][1]
        self.assertEqual(soy["title"], "सोयाबीन: आम भाव ₹6,600")
        self.assertEqual(soy["total"], ["MSP", "₹5,708"])
        self.assertIn(["सबसे ऊंचा: सैलाना, मध्य प्रदेश", "₹7,300"], soy["rows"])
        self.assertIn("-0.9%", soy["note"])
        self.assertNotIn("total", p["slides"][3])  # onion has no MSP
        self.assertIn("सोयाबीन: ₹6,600", p["caption"])

    def test_max_crops(self):
        feed = {"reports": [crop(f"c{i}", f"फसल{i}", 1000 + i) for i in range(12)]}
        p = bhav.build(feed, date(2026, 10, 19))
        self.assertEqual(len(p["slides"]), bhav.MAX_CROPS + 2)

    def test_no_post_without_todays_prices(self):
        self.assertIsNone(bhav.build(FEED, date(2026, 10, 20)))


if __name__ == "__main__":
    unittest.main()
