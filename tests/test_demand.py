import unittest
from datetime import date
from unittest import mock

from engine import demand, stories


class DemandTest(unittest.TestCase):
    def test_only_on_mp_kist_days(self):
        d = stories.ALT_START
        days = [date.fromordinal(d.toordinal() + i) for i in range(8)]
        for day in days:
            self.assertEqual(demand.demand_day(day), stories.alt_scheme(day) == "mpkalyan")

    def test_stale_feed_gives_no_reel(self):
        feed = {"latestDate": "2026-11-19", "mandis": [{"x": 1}]}
        with mock.patch.object(demand.F, "load_feed", return_value=feed):
            self.assertIsNone(demand.build_n(date(2026, 11, 23), {}))

    def test_fresh_feed_marks_demand(self):
        feed = {"latestDate": "2026-11-23", "mandis": [{"x": 1}]}
        ep = {"series": "A", "key": "k", "title": "t"}
        with mock.patch.object(demand.F, "load_feed", return_value=feed), \
             mock.patch.object(stories, "build_bhav", return_value=ep):
            out = demand.build_n(date(2026, 11, 23), {})
        self.assertTrue(out["demand"] and out["meta_only"])


if __name__ == "__main__":
    unittest.main()
