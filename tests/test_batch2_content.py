# -*- coding: utf-8 -*-
"""Batch 2 (26 Sep 2026): story-first Hindi script, Hindi-first titles with
the price, and a taazabhav.com link in every description and comment.

Records are built through fetch_prices.clean_records() so they arrive the
way the real pipeline delivers them: whole rupees, highest price first.
"""
import os
import unittest
from datetime import date

os.environ.setdefault("DATA_GOV_API_KEY", "test-key-not-real")

import fetch_prices  # noqa: E402
import generate_script  # noqa: E402
import hindi_names  # noqa: E402
import main  # noqa: E402

RAW = [
    {"market": "Tilhar APMC", "modal_price": "3000"},
    {"market": "Lakhimpur APMC", "modal_price": "5983"},
    {"market": "Ghaziabad APMC", "modal_price": "4042.26"},
]
RECORDS = fetch_prices.clean_records(RAW)
FLAT = fetch_prices.clean_records([
    {"market": "Ludhiana APMC", "modal_price": "800"},
    {"market": "Jalandhar APMC", "modal_price": "820"},
])


class TestHindiScript(unittest.TestCase):
    def test_opens_with_story_not_greeting(self):
        for offset in range(3):  # every rotation variant
            d = date(2026, 9, 27 + offset)
            script, captions = generate_script.build_script_and_captions(
                RECORDS, "Uttar Pradesh", "Onion", d, lang="hi")
            first_line = script.splitlines()[0]
            self.assertNotIn("नमस्कार", first_line)
            self.assertIn("प्याज", first_line)          # Hindi crop name, not "Onion"
            self.assertNotIn("Onion", script)
            self.assertIn(d.strftime("%d %B %Y"), captions["intro"])  # canonical date kept
            self.assertTrue("5983" in first_line or "2983" in first_line)

    def test_spread_story_needs_real_gap(self):
        script, _ = generate_script.build_script_and_captions(
            FLAT, "Punjab", "Potato", date(2026, 9, 27), lang="hi")
        self.assertNotIn("फ़र्क", script)
        self.assertNotIn("अंतर", script)
        self.assertIn("820", script.splitlines()[0])

    def test_market_lines_follow_record_order_and_skip_min_max(self):
        _, captions = generate_script.build_script_and_captions(
            RECORDS, "Uttar Pradesh", "Onion", date(2026, 9, 27), lang="hi")
        self.assertEqual(len(captions["markets"]), 3)
        self.assertIn("Lakhimpur", captions["markets"][0])
        self.assertIn("5983", captions["markets"][0])
        for line in captions["markets"]:
            self.assertNotIn("न्यूनतम", line)
            self.assertNotIn("APMC", line)

    def test_other_languages_unchanged(self):
        script, _ = generate_script.build_script_and_captions(
            RECORDS, "Maharashtra", "Onion", date(2026, 9, 27), lang="mr")
        self.assertIn("नमस्कार मित्रांनो", script)


class TestMetadata(unittest.TestCase):
    def test_title_is_hindi_first_with_price_and_keyword(self):
        title, _, _, _ = main.build_metadata("Onion", "Uttar Pradesh", RECORDS, date(2026, 9, 27))
        self.assertTrue(title.startswith("प्याज का भाव ₹3,000–₹5,983"))
        self.assertIn("Onion Rate Today", title)
        self.assertIn("#Shorts", title)
        self.assertLessEqual(len(title), 100)

    def test_long_state_title_still_fits(self):
        title, _, _, _ = main.build_metadata(
            "Bajra(Pearl Millet/Cumbu)", "Dadra and Nagar Haveli and Daman and Diu",
            RECORDS, date(2026, 9, 27))
        self.assertLessEqual(len(title), 100)

    def test_description_and_comment_link_to_the_right_page(self):
        _, desc, tags, comment = main.build_metadata("Onion", "Uttar Pradesh", RECORDS, date(2026, 9, 27))
        url = "https://taazabhav.com/mandi-bhav/onion/uttar-pradesh?utm_source=youtube&utm_medium=shorts"
        self.assertIn(url, desc.splitlines()[1])
        self.assertIn(url, comment)
        self.assertIn("Lakhimpur APMC", comment)  # best mandi really is the top one
        self.assertIn("onion rate today", tags)
        self.assertIn("data.gov.in", desc)


class TestHindiNames(unittest.TestCase):
    def test_slug_matches_site(self):
        self.assertEqual(hindi_names.slug("Uttar Pradesh"), "uttar-pradesh")
        self.assertEqual(hindi_names.slug("Onion Green"), "onion-green")
        self.assertEqual(hindi_names.slug("Paddy(Common)"), "paddycommon")

    def test_spoken_market(self):
        self.assertEqual(hindi_names.spoken_market("Mukerian(Talwara) APMC"), "Mukerian")
        self.assertEqual(hindi_names.spoken_market("APMC Lasalgaon"), "Lasalgaon")

    def test_unknown_names_fall_back(self):
        self.assertEqual(hindi_names.commodity_hi("Dragon Fruit"), "Dragon Fruit")
        self.assertEqual(hindi_names.state_hi("Goa"), "Goa")


if __name__ == "__main__":
    unittest.main()
