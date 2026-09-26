"""Batch 1 (26 Sep 2026): on-screen prices use whole rupees with Indian
digit grouping, and the hero price always matches records[0] once records
come through fetch_prices.clean_records()."""
import os
import unittest

os.environ.setdefault("DATA_GOV_API_KEY", "test-key-not-real")

import render_card  # noqa: E402
import fetch_prices  # noqa: E402


class TestInr(unittest.TestCase):
    def test_grouping(self):
        self.assertEqual(render_card._inr(5983), "5,983")
        self.assertEqual(render_card._inr("2311.09"), "2,311")
        self.assertEqual(render_card._inr(598300), "5,98,300")
        self.assertEqual(render_card._inr(999), "999")
        self.assertEqual(render_card._inr("N/A"), "N/A")


class TestHeroMatchesTopMarket(unittest.TestCase):
    def test_top_price_is_first_record_after_cleaning(self):
        # The 25 Sep bug: hero showed the max price but labelled it with
        # records[0], which was a different (cheaper) row.
        raw = [
            {"market": "Tilhar APMC", "modal_price": "3000"},
            {"market": "Najibabad APMC", "modal_price": "5983"},
            {"market": "Ghaziabad APMC", "modal_price": "4042.26"},
        ]
        recs = fetch_prices.clean_records(raw)
        self.assertEqual(render_card._top_price(recs), recs[0]["modal_price"])
        self.assertEqual(recs[0]["market"], "Najibabad APMC")


if __name__ == "__main__":
    unittest.main()
