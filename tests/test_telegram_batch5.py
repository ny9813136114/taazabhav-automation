# -*- coding: utf-8 -*-
import datetime as dt, json, os, tempfile, unittest
from unittest.mock import patch
import telegram_broadcast as tb

def rec(state, market, modal, date="27/09/2026"):
    return {"state": state, "market": market, "modal_price": str(modal), "arrival_date": date}

class Batch5Test(unittest.TestCase):
    def test_state_price_is_median_of_mandis_not_first_row(self):
        rows = [rec("UP", "A", "9000.4"), rec("UP", "B", 2000), rec("UP", "C", 3000),
                rec("UP", "C", 3100), rec("UP", "C", 2900)]  # C has 3 variety rows
        self.assertEqual(tb._state_price(rows), (3000, 3))

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

    def test_probe_failure_exits_fast_with_one_alert(self):
        with patch.dict(os.environ, {"TELEGRAM_BOT_TOKEN": "t"}), \
             patch.object(tb, "fetch_all_states", side_effect=RuntimeError("timeout")) as f, \
             patch.object(tb, "send_telegram_alert") as alert, \
             patch.object(tb, "_post_to_channel") as post:
            self.assertEqual(tb.main(), 1)
        self.assertEqual(f.call_count, 1)
        self.assertEqual(alert.call_count, 1)
        post.assert_not_called()

    def test_data_date(self):
        self.assertEqual(tb._data_date([rec("UP", "A", 1, "26/09/2026"), rec("UP", "B", 1, "27/09/2026"), {}]),
                         dt.date(2026, 9, 27))

if __name__ == "__main__":
    unittest.main()
