# -*- coding: utf-8 -*-
"""PR 4: Somvar Meta report."""
import unittest
from datetime import date, datetime
from unittest import mock

from posts import report as r
from posts.run import IST


def resp(body, code=200):
    m = mock.Mock(); m.status_code = code; m.json.return_value = body; m.content = b"x"; return m


ROWS = [
    {"net": "facebook", "id": "1_a", "format": "Bhav carousel", "reach": 100, "shares": 4, "comments": 2, "reactions": 5, "link": "https://fb/a", "hook": "भाव"},
    {"net": "instagram", "id": "ia", "format": "Bhav carousel", "reach": 50, "shares": 1, "saves": 3, "comments": 0, "reactions": 2, "link": "https://ig/a", "hook": "भाव"},
    {"net": "facebook", "id": "1_b", "format": "Kist ka Sach Reel", "reach": 20, "shares": 0, "comments": 0, "reactions": 1, "link": "https://fb/b", "hook": "किस्त"},
]


class ReportTest(unittest.TestCase):
    def test_week_is_previous_monday_to_sunday_ist(self):
        start, end = r.week_of(date(2026, 10, 26))
        self.assertEqual(start, datetime(2026, 10, 19, tzinfo=IST))
        self.assertEqual(end, datetime(2026, 10, 26, tzinfo=IST))

    def test_slot_by_time(self):
        self.assertEqual(r.slot_of(datetime(2026, 10, 20, 2, 5, tzinfo=r._ts("2026-10-20T00:00:00+0000").tzinfo)), "Bhav Dhamaka Reel")

    def test_format_from_ledger_then_hook(self):
        idx = r.ledger_index([{"pillar": "A", "facebook": "887", "instagram": "179"}, {"pillar": "P3", "facebook": "1_x"}])
        self.assertEqual(r.format_of({"id": "z", "link": "https://www.facebook.com/reel/887/", "time": "2026-10-20T15:00:00+05:30"}, idx), "Bhav Dhamaka Reel")
        self.assertEqual(r.format_of({"id": "1_x", "link": "", "time": "2026-10-20T15:00:00+05:30"}, idx), "P3 Kisan ka Hisaab")
        self.assertEqual(r.format_of({"id": "q", "link": "", "hook": "आज के मंडी भाव, 20", "time": "2026-10-20T19:36:00+05:30"}, idx), "Bhav carousel")

    def test_five_line_message_baseline_then_change(self):
        s = r.summarise(ROWS)
        self.assertEqual(s["total"]["shares"], 5)
        msg = r.message(date(2026, 10, 19), s, ROWS)
        lines = msg.split("\n")
        self.assertEqual(len(lines), 5)
        self.assertIn("Bhav carousel", lines[1])
        self.assertIn("Kist ka Sach Reel", lines[2])
        self.assertIn("https://fb/a", lines[3])
        self.assertIn("baseline", lines[4])
        prev = {"summary": {"total": {"reach": 100, "shares": 1, "comments": 0, "saves": 0}}}
        self.assertIn("shares +4", r.message(date(2026, 10, 19), s, ROWS, prev))

    def test_ig_metric_not_supported_is_skipped(self):
        s = mock.Mock()
        s.get.side_effect = [resp({"data": [{"values": [{"value": 80}]}]}),
                             resp({"error": {"message": "unsupported"}}, 400),
                             resp({"data": [{"values": [{"value": 3}]}]}),
                             resp({"data": []}), resp({"data": []})]
        self.assertEqual(r.ig_insights(s, "m1", "t"), {"reach": 80, "saved": 3})

    def test_no_activity_line(self):
        rows = [dict(ROWS[2])]
        self.assertIn("nahi aaya", r.message(date(2026, 10, 19), r.summarise(rows), rows))


if __name__ == "__main__":
    unittest.main()
