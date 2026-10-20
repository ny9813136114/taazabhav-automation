# -*- coding: utf-8 -*-
import unittest
from datetime import datetime, timedelta, timezone

from engine.slot_gate import IST, SLOTS, decide


def utc(h, m=0, day=18):
    return datetime(2026, 10, day, h, m, tzinfo=timezone.utc)


class SlotGateTest(unittest.TestCase):
    def test_on_time_run_goes(self):
        self.assertEqual(decide("D", utc(7, 0), {}, False), (True, "2026-10-18", ""))

    def test_late_fallback_after_clock_run_skips(self):
        self.assertEqual(decide("D", utc(11, 54), {"D": "2026-10-18"}, True)[:2], (False, "2026-10-18"))

    def test_late_fallback_without_clock_runs_and_says_so(self):
        self.assertEqual(decide("D", utc(11, 54), {"D": "2026-10-17"}, True), (True, "2026-10-18", "clock missed"))

    def test_evening_slot_after_midnight_belongs_to_yesterday(self):
        # B is 20:30 IST (15:00 UTC); 19:00 UTC is 00:30 IST next day: night, skipped.
        self.assertEqual(decide("B", utc(19, 0), {}, True), (False, "2026-10-18", "too late"))
        self.assertEqual(decide("B", utc(19, 0), {"B": "2026-10-18"}, True)[0], False)

    def test_late_evening_backup_before_23_ist_still_runs(self):
        # 17:00 UTC = 22:30 IST, two hours after B's slot.
        self.assertEqual(decide("B", utc(17, 0), {}, True), (True, "2026-10-18", "clock missed"))

    def test_no_series_posts_at_night(self):
        # 20 Oct: GitHub backup at 20:18 UTC (01:48 IST) posted B. Every
        # series, every quarter hour from 23:00 to 05:45 IST, must skip.
        for series in ("A", "B", "C", "D"):
            for minutes in range(0, 7 * 60, 15):
                now = utc(17, 30) + timedelta(minutes=minutes)
                run, _, note = decide(series, now, {}, True)
                self.assertFalse(run, f"{series} at {now.astimezone(IST):%H:%M} IST")
                self.assertEqual(note, "too late")

    def test_every_slot_runs_on_time(self):
        for series, (h, m) in SLOTS.items():
            now = datetime(2026, 10, 18, h, m, tzinfo=IST)
            self.assertEqual(decide(series, now, {}, False), (True, "2026-10-18", ""), series)

    def test_too_late_is_skipped(self):
        self.assertEqual(decide("B", utc(22, 0), {}, True), (False, "2026-10-18", "too late"))

    def test_slightly_early_start_counts_as_today(self):
        self.assertEqual(decide("A", utc(1, 50), {}, False)[1], "2026-10-18")


if __name__ == "__main__":
    unittest.main()


class YoutubeLoginCheckTest(unittest.TestCase):
    def test_missing_login_is_reported_not_raised(self):
        import os
        import tempfile
        from engine.publish import youtube_login_problem
        cwd = os.getcwd()
        with tempfile.TemporaryDirectory() as d:
            os.chdir(d)
            try:
                self.assertIn("token.pickle", youtube_login_problem())
            finally:
                os.chdir(cwd)
