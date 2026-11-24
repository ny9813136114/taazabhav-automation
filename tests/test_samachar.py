import unittest
from datetime import date

from engine import qa, samachar


def crop(name, modal, hist, date_="2026-11-23"):
    return {"commodity": name, "variety": "x", "date": date_, "modal": modal, "min": modal - 100, "max": modal + 100,
            "history": [{"date": "2026-11-17", "modal": hist}]}


FEED = {"latestDate": "2026-11-23", "reports": [], "mandis": [
    {"state": "MP", "market": "Betul APMC", "marketHi": "बैतूल", "path": "/mandi-bhav/state/madhya-pradesh/betul",
     "crops": [crop("Soyabean", 4500, 4400), crop("Wheat", 2600, 2580), crop("Maize", 2100, 2150)]},
    {"state": "MP", "market": "Small APMC", "marketHi": "छोटी", "path": "/x", "crops": [crop("Wheat", 2600, 2580)]},
]}


class SamacharTest(unittest.TestCase):
    def test_builds_a_checked_long_video(self):
        ep = samachar.build_v(FEED, date(2026, 11, 24), set())
        self.assertEqual(ep["series"], "V")
        self.assertEqual(ep["key"], "Betul APMC")
        qa.check_episode(ep)
        self.assertGreater(len(ep["scenes"]), 8)
        self.assertNotIn("#Shorts", ep["title"])

    def test_mandi_not_repeated_and_small_mandi_skipped(self):
        self.assertIsNone(samachar.build_v(FEED, date(2026, 11, 24), {"Betul APMC"}))

    def test_stale_prices_give_no_video(self):
        self.assertIsNone(samachar.build_v(FEED, date(2026, 11, 28), set()))


if __name__ == "__main__":
    unittest.main()
