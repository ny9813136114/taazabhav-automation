"""Phase 1B-B TEST 2 (script date): covers the independently-verified
production bug where generate_script.py computed its own date.today()
(UTC, naive) for the Hindi narration's opening line ("aaj {date} hai"),
completely independent of the date already shown in the video's own
title/thumbnail. Confirmed real via two production commit timestamps (see
the Phase 1B-A investigation report and docs/RELIABILITY.md) -- this is
not a theoretical risk.

These tests call generate_script.py's real functions directly (not through
main.py), since that's the most direct way to prove the narration text
itself reflects the explicitly-supplied canonical date and not an
independently-read clock.
"""
import unittest
from datetime import date
from unittest.mock import patch

import generate_script

SAMPLE_RECORDS = [
    {"market": "Ludhiana APMC", "min_price": "700", "max_price": "900", "modal_price": "800"},
]


class TestBuildScriptAndCaptionsUsesExplicitRunDate(unittest.TestCase):
    """build_script_and_captions() is the function main.py actually calls
    in production -- it must use exactly the run_date it's given."""

    def test_narration_intro_contains_the_supplied_run_date(self):
        run_date = date(2026, 9, 12)
        expected_date_text = run_date.strftime("%d %B %Y")

        script_text, captions = generate_script.build_script_and_captions(
            SAMPLE_RECORDS, "Punjab", "Potato", run_date, lang="hi",
        )

        self.assertIn(expected_date_text, script_text)
        self.assertIn(expected_date_text, captions["intro"])

    def test_does_not_call_date_today_when_run_date_is_supplied(self):
        """Verifies independence, not just correctness: even if the real
        current date were something else entirely, the narration must
        reflect the SUPPLIED run_date, not whatever date.today() would
        return right now. This is what actually distinguishes "receives
        and uses the explicit date" from "happens to also be today"."""
        run_date = date(2020, 1, 1)  # deliberately not today, by construction
        wrong_date_text_if_bug_reintroduced = date.today().strftime("%d %B %Y")

        script_text, _captions = generate_script.build_script_and_captions(
            SAMPLE_RECORDS, "Punjab", "Potato", run_date, lang="hi",
        )

        self.assertIn(run_date.strftime("%d %B %Y"), script_text)
        if wrong_date_text_if_bug_reintroduced != run_date.strftime("%d %B %Y"):
            self.assertNotIn(wrong_date_text_if_bug_reintroduced, script_text)

    def test_date_today_is_never_called_at_all(self):
        """Belt-and-suspenders: patches generate_script.date.today to raise,
        proving the code path genuinely never reaches it when run_date is
        supplied -- not just that the output happens to look right."""
        run_date = date(2026, 9, 12)
        with patch("generate_script.date") as mock_date_cls:
            mock_date_cls.today.side_effect = AssertionError(
                "build_script_and_captions() must not call date.today() when run_date is supplied"
            )
            script_text, _captions = generate_script.build_script_and_captions(
                SAMPLE_RECORDS, "Punjab", "Potato", run_date, lang="hi",
            )
        mock_date_cls.today.assert_not_called()
        self.assertIn(run_date.strftime("%d %B %Y"), script_text)


class TestBuildScriptBackwardCompatibility(unittest.TestCase):
    """build_script() (used only by the manual test_script.py/test_preview.py
    smoke-test scripts, never by the real pipeline) must keep working
    unchanged when called the old way, with no run_date at all -- Phase
    1B-B intentionally did not touch those scripts (see the implementation
    report's Part 4)."""

    def test_build_script_without_run_date_falls_back_to_today(self):
        script_text = generate_script.build_script(
            SAMPLE_RECORDS, "Punjab", "Potato", lang="hi",
        )
        self.assertIn(date.today().strftime("%d %B %Y"), script_text)

    def test_build_script_with_explicit_run_date_uses_it(self):
        run_date = date(2026, 9, 12)
        script_text = generate_script.build_script(
            SAMPLE_RECORDS, "Punjab", "Potato", lang="hi", run_date=run_date,
        )
        self.assertIn(run_date.strftime("%d %B %Y"), script_text)


if __name__ == "__main__":
    unittest.main()
