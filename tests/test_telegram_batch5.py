# -*- coding: utf-8 -*-
import datetime as dt, json, os, tempfile, unittest
from unittest.mock import patch
import telegram_broadcast as tb

class Batch5Test(unittest.TestCase):
    def test_previous_only_if_exactly_yesterday(self):
        with tempfile.TemporaryDirectory() as d, patch.object(tb, "HISTORY_DIR", d):
            today = dt.date(2026, 9, 28)
            tb._save_today("UP", dt.date(2026, 9, 25), {"Onion": 2000})
            self.assertEqual(tb._load_previous("UP", today), {})  # 3 days old
            tb._save_today("UP", dt.date(2026, 9, 27), {"Onion": 2000})
            self.assertEqual(tb._load_previous("UP", today), {"Onion": 2000})
            with open(tb._history_path("UP"), "w") as f:
                json.dump({"Onion": 2000.0}, f)  # old flat format
            self.assertEqual(tb._load_previous("UP", today), {})

    def test_message_per_kg_and_trend(self):
        m = tb._build_message("UP", "27 Sep 2026", {"Onion": 2500, "Potato": 1200},
                              {"Onion": 2000, "Potato": 1200}, {"Onion": 14, "Potato": 9})
        self.assertIn("₹25/kg (₹2,500/qtl) · 14 mandi (+25% kal se)", m)
        self.assertIn("kal jaisa", m)
        self.assertIn("median", m)

if __name__ == "__main__":
    unittest.main()
