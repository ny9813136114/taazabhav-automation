# -*- coding: utf-8 -*-
"""The channel broadcast reads taazabhav.com (18 Oct 2026), not data.gov.in."""
import datetime as dt
import json
import os
import tempfile
import unittest
from unittest.mock import patch

import telegram_broadcast as tb

SITE = json.load(open(os.path.join(os.path.dirname(__file__), "fixtures", "site_state_up.json"), encoding="utf-8"))


class SitePricesTest(unittest.TestCase):
    def test_pool_names_map_to_site_names(self):
        prices, counts, pct, newest = tb.state_prices(SITE)
        self.assertEqual(prices["Bhindi"], 2000)          # "Bhindi(Ladies Finger)"
        self.assertEqual(prices["Bitter Gourd"], 2500)    # site writes "Bitter gourd"
        self.assertEqual(prices["Ginger"], 4000)          # Green, not Dry
        self.assertEqual(counts["Onion"], 40)
        self.assertEqual(pct["Bhindi"], 3.2)
        self.assertNotIn("Onion", pct)                    # null change is not a change
        self.assertNotIn("Apple", prices)                 # not on the site for this state
        self.assertEqual(newest, "2026-10-18")

    def test_message_uses_site_change(self):
        prices, counts, pct, _ = tb.state_prices(SITE)
        m = tb._build_message("Uttar Pradesh", "18 Oct 2026", prices, {}, counts, pct)
        self.assertIn("Bhindi: ₹20/kg (₹2,000/qtl) · 3 mandi (+3% kal se)", m)
        self.assertIn("TRENDING", m)

    def test_fetch_retries_then_raises(self):
        class R:
            status_code = 503
        with patch.object(tb.requests, "get", return_value=R()) as g, patch.object(tb.time, "sleep"):
            with self.assertRaises(RuntimeError):
                tb.fetch_state("Uttar Pradesh")
        self.assertEqual(g.call_count, 3)
        self.assertIn("/api/home-tools/state/uttar-pradesh", g.call_args[0][0])


class MainTest(unittest.TestCase):
    def run_main(self, fetch, d):
        with patch.dict(os.environ, {"TELEGRAM_BOT_TOKEN": "t"}), \
             patch.object(tb, "HISTORY_DIR", d), patch.object(tb, "LAST_POST", os.path.join(d, "_last.json")), \
             patch.object(tb, "fetch_state", side_effect=fetch), \
             patch.object(tb, "_post_to_channel") as post, \
             patch.object(tb, "send_telegram_alert") as alert, \
             patch.object(tb.time, "sleep"):
            code = tb.main()
        return code, post, alert

    def test_posts_every_state_once_a_day(self):
        with tempfile.TemporaryDirectory() as d:
            code, post, alert = self.run_main(lambda s: SITE, d)
            self.assertEqual(code, 0)
            self.assertEqual(post.call_count, len(tb.STATES))
            alert.assert_not_called()
            code, post, alert = self.run_main(lambda s: SITE, d)  # late fallback run
            self.assertEqual(code, 0)
            post.assert_not_called()

    def test_site_down_alerts_owner(self):
        def boom(state):
            raise RuntimeError("HTTP 502")
        with tempfile.TemporaryDirectory() as d:
            code, post, alert = self.run_main(boom, d)
        self.assertEqual(code, 1)
        post.assert_not_called()
        alert.assert_called_once()

    def test_one_state_failing_still_posts_others(self):
        def one_bad(state):
            if state == "Punjab":
                raise RuntimeError("HTTP 502")
            return SITE
        with tempfile.TemporaryDirectory() as d:
            code, post, alert = self.run_main(one_bad, d)
        self.assertEqual(code, 1)
        self.assertEqual(post.call_count, len(tb.STATES) - 1)
        self.assertIn("Punjab", alert.call_args[0][0])


if __name__ == "__main__":
    unittest.main()
