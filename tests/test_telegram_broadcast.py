"""Covers a review finding on the Phase 1A branch: _fetch_all_commodities()
had narrowed its exception handling to `except DataFetchError` only, with
no surrounding try/except at its call site in main() -- so any OTHER
exception type from a single commodity's concurrent fetch (e.g. a
malformed/non-JSON response) crashed the entire broadcast for all 5
states, silently, before any Telegram alert could fire. Fixed by
broadening back to `except Exception`, matching the original
_fetch_commodity()'s "one item's failure never stops the whole run"
guarantee. These tests would have failed against the pre-fix code.
"""
import os
import unittest
from unittest.mock import patch

os.environ.setdefault("DATA_GOV_API_KEY", "test-key-not-real")

import telegram_broadcast  # noqa: E402


class TestFetchAllCommoditiesResilience(unittest.TestCase):
    def test_non_data_fetch_error_exception_does_not_crash(self):
        """A commodity fetch raising something other than DataFetchError
        (e.g. a JSONDecodeError from a malformed response body) must be
        caught and recorded as None for that commodity only -- every other
        commodity must still be fetched."""
        commodity_names = [name for name, _, _ in telegram_broadcast.COMMODITY_POOL]
        failing_name = commodity_names[0]

        def fake_fetch(name):
            if name == failing_name:
                raise ValueError("Expecting value: line 1 column 1 (char 0)")
            return [{"state": "Uttar Pradesh", "market": "Test APMC", "modal_price": "1000"}]

        with patch("telegram_broadcast.fetch_all_states", side_effect=fake_fetch):
            results = telegram_broadcast._fetch_all_commodities()

        self.assertIsNone(results[failing_name])
        other_names = [n for n in commodity_names if n != failing_name]
        self.assertTrue(all(results[n] is not None for n in other_names))
        self.assertEqual(len(results), len(commodity_names))


class TestMainDoesNotCrashOnFetchException(unittest.TestCase):
    def test_main_completes_and_reports_failure_instead_of_crashing(self):
        """Integration-level check on the actual regression: main() itself
        must not raise even if every commodity fetch raises unexpectedly --
        it should complete, report the failures, and return a non-zero
        exit code, not propagate an uncaught exception out of the process."""
        with patch.dict(os.environ, {"TELEGRAM_BOT_TOKEN": "test-token"}), \
             patch("telegram_broadcast.fetch_all_states", side_effect=ValueError("boom")), \
             patch("telegram_broadcast._post_to_channel") as mock_post, \
             patch("telegram_broadcast.send_telegram_alert") as mock_alert, \
             patch("telegram_broadcast.time.sleep", return_value=None):
            exit_code = telegram_broadcast.main()

        self.assertEqual(exit_code, 1)
        mock_post.assert_not_called()  # no data for any commodity -- nothing to post
        mock_alert.assert_called()  # the maintainer must still be notified


if __name__ == "__main__":
    unittest.main()
