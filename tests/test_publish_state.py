"""Covers Phase 1A requirements 6-7:
  6. Duplicate-upload detection.
  7. Successful upload state recording.
(Requirement 8, "failed upload does not incorrectly mark content as
published", is an integration behavior of main.run_pipeline() and is
covered in test_main_pipeline.py, since publish_state.py itself has no
concept of "upload failed" -- it only ever records confirmed successes.)

Uses a temporary file for LOG_PATH so this never touches the real
data/published/published_log.json on disk.
"""
import unittest
import tempfile
from pathlib import Path
from unittest.mock import patch

import publish_state


class TestPublishState(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self._tmp_log_path = Path(self._tmpdir.name) / "published_log.json"
        self._patcher = patch.object(publish_state, "LOG_PATH", self._tmp_log_path)
        self._patcher.start()

    def tearDown(self):
        self._patcher.stop()
        self._tmpdir.cleanup()

    def test_unpublished_by_default(self):
        self.assertFalse(publish_state.is_published("2026-09-12", "Punjab", "Potato"))

    def test_mark_then_is_published(self):
        publish_state.mark_published("2026-09-12", "Punjab", "Potato", "abc123")
        self.assertTrue(publish_state.is_published("2026-09-12", "Punjab", "Potato"))

    def test_identity_is_date_state_commodity(self):
        publish_state.mark_published("2026-09-12", "Punjab", "Potato", "abc123")
        # Different date, same state/commodity -> not published.
        self.assertFalse(publish_state.is_published("2026-09-13", "Punjab", "Potato"))
        # Same date, different commodity -> not published.
        self.assertFalse(publish_state.is_published("2026-09-12", "Punjab", "Onion"))
        # Same date, different state -> not published.
        self.assertFalse(publish_state.is_published("2026-09-12", "Karnataka", "Potato"))

    def test_identity_is_case_and_whitespace_insensitive(self):
        publish_state.mark_published("2026-09-12", "Punjab", "Potato", "abc123")
        self.assertTrue(publish_state.is_published("2026-09-12", " punjab ", "POTATO"))

    def test_survives_reload_from_disk(self):
        # Simulates a fresh GitHub Actions run reading back a log file
        # committed by a previous run.
        publish_state.mark_published("2026-09-12", "Punjab", "Potato", "abc123")
        self.assertTrue(self._tmp_log_path.exists())

        reloaded = publish_state._load_log()
        self.assertIn("2026-09-12", reloaded)

    def test_corrupted_log_file_does_not_crash(self):
        self._tmp_log_path.parent.mkdir(parents=True, exist_ok=True)
        self._tmp_log_path.write_text("{not valid json", encoding="utf-8")

        self.assertFalse(publish_state.is_published("2026-09-12", "Punjab", "Potato"))
        # And a subsequent mark_published() must still work, rewriting the
        # file cleanly rather than being permanently blocked.
        publish_state.mark_published("2026-09-12", "Punjab", "Potato", "abc123")
        self.assertTrue(publish_state.is_published("2026-09-12", "Punjab", "Potato"))


if __name__ == "__main__":
    unittest.main()
