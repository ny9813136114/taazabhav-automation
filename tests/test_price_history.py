"""Phase 1B-B TEST 3 (history date), TEST 6 (arrival_date present),
TEST 7 (arrival_date missing), TEST 8 (backward compatibility).

price_history.py previously computed its own date.today() (UTC, naive)
independently of main.py's IST-derived date -- real production commits
proved this could disagree with the same run's video title (see the
Phase 1B-A investigation report). save_today_prices() now requires the
caller to supply the canonical run_date explicitly instead.

Uses a temporary HISTORY_DIR so these tests never touch the real
data/history/ files on disk.
"""
import json
import unittest
import tempfile
from datetime import date
from pathlib import Path
from unittest.mock import patch

import price_history


class PriceHistoryTestCase(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self._tmp_history_dir = Path(self._tmpdir.name)
        self._patcher = patch.object(price_history, "HISTORY_DIR", self._tmp_history_dir)
        self._patcher.start()

    def tearDown(self):
        self._patcher.stop()
        self._tmpdir.cleanup()

    def _read_raw(self, state, commodity):
        path = price_history._history_file(state, commodity)
        return json.loads(path.read_text(encoding="utf-8"))


class TestSaveTodayPricesUsesExplicitRunDate(PriceHistoryTestCase):
    """TEST 3: history writing receives and uses the explicitly-provided
    canonical date, not its own date.today()."""

    def test_history_key_is_the_supplied_run_date_not_todays_real_date(self):
        run_date = date(2020, 1, 1)  # deliberately not today, by construction
        records = [{"market": "Ludhiana APMC", "modal_price": "800", "arrival_date": "01/01/2020"}]

        price_history.save_today_prices("Punjab", "Potato", records, run_date)

        stored = self._read_raw("Punjab", "Potato")
        self.assertIn("2020-01-01", stored)
        self.assertNotIn(date.today().isoformat(), stored)

    def test_date_today_is_never_called(self):
        run_date = date(2026, 9, 12)
        records = [{"market": "Ludhiana APMC", "modal_price": "800"}]
        with patch("price_history.date") as mock_date_cls:
            mock_date_cls.today.side_effect = AssertionError(
                "save_today_prices() must not call date.today() when run_date is supplied"
            )
            price_history.save_today_prices("Punjab", "Potato", records, run_date)
        mock_date_cls.today.assert_not_called()


class TestArrivalDatePresent(PriceHistoryTestCase):
    """TEST 6: a source record containing arrival_date preserves the
    exact source value, unmodified, not replaced by run_date or anything
    else."""

    def test_arrival_date_is_preserved_exactly(self):
        run_date = date(2026, 9, 12)
        records = [{"market": "Ludhiana APMC", "modal_price": "800", "arrival_date": "13/09/2026"}]

        price_history.save_today_prices("Punjab", "Potato", records, run_date)

        stored = self._read_raw("Punjab", "Potato")
        entry = stored["2026-09-12"]["Ludhiana APMC"]
        self.assertEqual(entry["arrival_date"], "13/09/2026")
        # The source's own arrival_date must NOT be silently replaced by
        # the pipeline's run_date, even though the two happen to be close
        # here -- they are deliberately independent pieces of information
        # (Phase 1B-B Part 6's explicit rule).
        self.assertEqual(entry["modal_price"], "800")


class TestArrivalDateMissing(PriceHistoryTestCase):
    """TEST 7: a missing arrival_date does not crash the pipeline and does
    not invent a value."""

    def test_missing_arrival_date_stores_null_not_a_crash_or_invented_value(self):
        run_date = date(2026, 9, 12)
        records = [{"market": "Ludhiana APMC", "modal_price": "800"}]  # no arrival_date key at all

        price_history.save_today_prices("Punjab", "Potato", records, run_date)  # must not raise

        stored = self._read_raw("Punjab", "Potato")
        entry = stored["2026-09-12"]["Ludhiana APMC"]
        self.assertIsNone(entry["arrival_date"])
        self.assertEqual(entry["modal_price"], "800")


class TestBackwardCompatibility(PriceHistoryTestCase):
    """TEST 8: historical records written before Phase 1B-B (a bare
    modal_price number, no arrival_date, no wrapping object at all) must
    remain readable -- no migration, no rewriting of old entries."""

    def test_old_format_file_is_still_readable(self):
        path = price_history._history_file("Punjab", "Potato")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({
            "2026-09-05": {"Tanda Urmur APMC": 1100, "Patti APMC": 0.08},
        }), encoding="utf-8")

        yesterday = price_history.load_yesterday_prices("Punjab", "Potato")

        self.assertEqual(yesterday, {"Tanda Urmur APMC": 1100, "Patti APMC": 0.08})

    def test_compute_trend_handles_old_bare_number_format(self):
        old_format_yesterday = {"Ludhiana APMC": 1000}
        result = price_history.compute_trend(old_format_yesterday, "Ludhiana APMC", 1100)
        self.assertEqual(result, ("up", 10.0))

    def test_compute_trend_handles_new_wrapped_format(self):
        new_format_yesterday = {"Ludhiana APMC": {"modal_price": 1000, "arrival_date": "11/09/2026"}}
        result = price_history.compute_trend(new_format_yesterday, "Ludhiana APMC", 1100)
        self.assertEqual(result, ("up", 10.0))

    def test_a_file_mixing_old_and_new_format_entries_across_dates_works(self):
        """The realistic transition case: an existing file with old-format
        dates on disk gets a NEW-format date appended by save_today_prices()
        without rewriting the old ones (Phase 1B-B Part 7's explicit "do not
        rewrite all historical files" rule)."""
        path = price_history._history_file("Punjab", "Potato")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({
            "2026-09-05": {"Tanda Urmur APMC": 1100},
        }), encoding="utf-8")

        run_date = date(2026, 9, 12)
        records = [{"market": "Tanda Urmur APMC", "modal_price": "1150", "arrival_date": "12/09/2026"}]
        price_history.save_today_prices("Punjab", "Potato", records, run_date)

        stored = self._read_raw("Punjab", "Potato")
        # Old entry untouched, still a bare number.
        self.assertEqual(stored["2026-09-05"]["Tanda Urmur APMC"], 1100)
        # New entry uses the new wrapped shape.
        self.assertEqual(stored["2026-09-12"]["Tanda Urmur APMC"]["modal_price"], "1150")

        # And a trend computed the day after must still work correctly
        # reading back yesterday's (new-format) entry.
        yesterday = price_history.load_yesterday_prices("Punjab", "Potato")
        trend = price_history.compute_trend(yesterday, "Tanda Urmur APMC", "1200")
        self.assertIsNotNone(trend)


if __name__ == "__main__":
    unittest.main()
