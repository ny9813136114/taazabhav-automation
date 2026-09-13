"""Covers Phase 1A requirement 5: historical-record validation.

Uses crafted temp fixtures shaped exactly like the real
data/history/*.json schema, including a reproduction of the actual
confirmed 2026-09-04 uttar-pradesh-onion.json contamination pattern, so
this test would have caught that incident had it existed at the time.
"""
import json
import unittest
import tempfile
from pathlib import Path

import validate_history


class TestValidateHistory(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.dir = Path(self._tmpdir.name)

    def tearDown(self):
        self._tmpdir.cleanup()

    def _write(self, filename, content):
        path = self.dir / filename
        path.write_text(json.dumps(content), encoding="utf-8")
        return path

    def test_clean_file_has_no_findings(self):
        path = self._write("uttar-pradesh-onion.json", {
            "2026-09-05": {"Lucknow APMC": 3500, "Agra APMC": 2500},
            "2026-09-06": {"Lucknow APMC": 3600, "Agra APMC": 2600},
        })
        report = validate_history.validate_file(path)
        self.assertEqual(report["findings"], [])
        self.assertEqual(report["dates_scanned"], 2)
        self.assertEqual(report["records_scanned"], 4)

    def test_detects_wrong_state_contamination(self):
        # Reproduces the actual confirmed 2026-09-04 incident: a
        # uttar-pradesh-onion.json date entry containing ONLY Tamil Nadu
        # Uzhavar Sandhai markets.
        path = self._write("uttar-pradesh-onion.json", {
            "2026-09-04": {
                "Perundurai(Uzhavar Sandhai )": 5750,
                "Namakkal(Uzhavar Sandhai )": 5300,
            },
            "2026-09-05": {"Lucknow APMC": 3500},
        })
        report = validate_history.validate_file(path)
        contamination_findings = [f for f in report["findings"] if f["type"] == "wrong_state_contamination"]
        self.assertEqual(len(contamination_findings), 1)
        self.assertEqual(contamination_findings[0]["date"], "2026-09-04")
        self.assertEqual(contamination_findings[0]["detected_state"], "Tamil Nadu")

    def test_does_not_flag_a_single_matching_market_as_contamination(self):
        # A day with at least one genuine in-state market must NOT be
        # flagged -- the contamination check is deliberately strict
        # (100% of that day's markets must carry the other-state
        # signature) so it never fires on a coincidental substring match.
        path = self._write("uttar-pradesh-onion.json", {
            "2026-09-04": {"Lucknow APMC": 3500, "Perundurai(Uzhavar Sandhai )": 5750},
        })
        report = validate_history.validate_file(path)
        contamination_findings = [f for f in report["findings"] if f["type"] == "wrong_state_contamination"]
        self.assertEqual(contamination_findings, [])

    def test_detects_implausible_price_magnitude(self):
        path = self._write("maharashtra-onion.json", {
            "2026-09-05": {"APMC Nagpur": 4750, "APMC Pune": 4200, "APMC Nasik": 4500, "APMC Satara": 4000, "APMC Solapur": 4100},
            "2026-09-06": {"Pune(Moshi)": 18},  # matches the real anomaly found in this exact file
        })
        report = validate_history.validate_file(path)
        outlier_findings = [f for f in report["findings"] if f["type"] == "implausible_price_magnitude"]
        self.assertEqual(len(outlier_findings), 1)
        self.assertEqual(outlier_findings[0]["market"], "Pune(Moshi)")

    def test_detects_empty_market_name_and_invalid_price(self):
        path = self._write("punjab-potato.json", {
            "2026-09-05": {"": 500, "Ludhiana APMC": "not-a-number"},
        })
        report = validate_history.validate_file(path)
        types_found = {f["type"] for f in report["findings"]}
        self.assertIn("empty_market_name", types_found)
        self.assertIn("invalid_price_value", types_found)

    def test_na_placeholder_is_not_flagged_as_invalid(self):
        # price_history.save_today_prices() legitimately writes "N/A" when
        # a record has no modal_price -- this must not be flagged.
        path = self._write("karnataka-tomato.json", {
            "2026-09-05": {"Doddaballapur APMC": "N/A"},
        })
        report = validate_history.validate_file(path)
        self.assertEqual(report["findings"], [])

    def test_missing_dates_in_range_detected(self):
        path = self._write("west-bengal-potato.json", {
            "2026-09-04": {"Siliguri APMC": 620},
            "2026-09-07": {"Siliguri APMC": 640},
        })
        report = validate_history.validate_file(path)
        gap_findings = [f for f in report["findings"] if f["type"] == "missing_dates_in_range"]
        self.assertEqual(len(gap_findings), 1)
        self.assertEqual(gap_findings[0]["dates"], ["2026-09-05", "2026-09-06"])

    def test_unreadable_file_is_reported_not_raised(self):
        path = self.dir / "broken.json"
        path.write_text("{not valid json", encoding="utf-8")
        report = validate_history.validate_file(path)
        self.assertEqual(report["findings"][0]["type"], "unreadable_file")

    def test_scan_all_covers_every_file_in_directory(self):
        self._write("uttar-pradesh-onion.json", {"2026-09-05": {"Lucknow APMC": 3500}})
        self._write("punjab-potato.json", {"2026-09-05": {"Ludhiana APMC": 700}})
        reports = validate_history.scan_all(self.dir)
        self.assertEqual(len(reports), 2)


class TestPhase1BBSchemaCompatibility(unittest.TestCase):
    """Phase 1B-B added an `arrival_date` field alongside modal_price
    (price_history.py now stores {"modal_price": ..., "arrival_date": ...}
    instead of a bare number, going forward). validate_history.py must
    keep validating correctly against the NEW shape without producing
    false positives, and must keep working against OLD (bare-number)
    entries already on disk -- the two shapes coexist in the same real
    files (Part 7's explicit "do not rewrite historical files" rule)."""

    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.dir = Path(self._tmpdir.name)

    def tearDown(self):
        self._tmpdir.cleanup()

    def _write(self, filename, content):
        path = self.dir / filename
        path.write_text(json.dumps(content), encoding="utf-8")
        return path

    def test_new_wrapped_format_is_not_flagged_as_invalid(self):
        path = self._write("punjab-potato.json", {
            "2026-09-12": {
                "Ludhiana APMC": {"modal_price": 800, "arrival_date": "12/09/2026"},
                "Rajpura APMC": {"modal_price": 850, "arrival_date": "12/09/2026"},
            },
        })
        report = validate_history.validate_file(path)
        self.assertEqual(report["findings"], [])
        self.assertEqual(report["records_scanned"], 2)

    def test_new_format_na_placeholder_still_not_flagged(self):
        path = self._write("karnataka-tomato.json", {
            "2026-09-05": {"Doddaballapur APMC": {"modal_price": "N/A", "arrival_date": None}},
        })
        report = validate_history.validate_file(path)
        self.assertEqual(report["findings"], [])

    def test_new_format_implausible_magnitude_still_detected(self):
        path = self._write("punjab-potato.json", {
            "2026-09-05": {
                "Quadian APMC": {"modal_price": 500, "arrival_date": "05/09/2026"},
                "Rajpura APMC": {"modal_price": 800, "arrival_date": "05/09/2026"},
                "Tanda APMC": {"modal_price": 1100, "arrival_date": "05/09/2026"},
                "Raikot APMC": {"modal_price": 670, "arrival_date": "05/09/2026"},
                "Patti APMC": {"modal_price": 0.04, "arrival_date": "05/09/2026"},
            },
        })
        report = validate_history.validate_file(path)
        outlier_findings = [f for f in report["findings"] if f["type"] == "implausible_price_magnitude"]
        self.assertEqual(len(outlier_findings), 1)
        self.assertEqual(outlier_findings[0]["market"], "Patti APMC")

    def test_a_file_mixing_old_bare_numbers_and_new_wrapped_entries_validates_cleanly(self):
        path = self._write("uttar-pradesh-onion.json", {
            # Consecutive dates -- no gap -- so this test only exercises the
            # old/new per-market value shapes, not the unrelated
            # missing_dates_in_range check.
            "2026-09-11": {"Lucknow APMC": 3500},  # old format, untouched on disk
            "2026-09-12": {"Lucknow APMC": {"modal_price": 3600, "arrival_date": "12/09/2026"}},  # new format
        })
        report = validate_history.validate_file(path)
        self.assertEqual(report["findings"], [])
        self.assertEqual(report["records_scanned"], 2)


if __name__ == "__main__":
    unittest.main()
