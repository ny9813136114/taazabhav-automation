"""Covers Phase 1A requirements 4, 8, 9, 10:
  4. Pipeline failure status when required data cannot be retrieved.
  8. A failed upload does not incorrectly mark content as published.
  9. A multi-target run where one target permanently fails still attempts
     the remaining targets.
  10. A legitimate empty-result day does not produce a FAILURE status.

Importing main.py pulls in the full pipeline (make_audio, make_video,
render_card, upload_youtube, etc.), so every one of those is mocked here --
no real audio/video is rendered, no real network call is made, and no real
YouTube upload happens. This module needs the full requirements.txt
installed (same as running the real pipeline) purely so those imports
succeed; nothing in this file exercises their real behavior.

Each test patches every name it needs directly (rather than sharing one
big always-on patch list) so that a test asserting on a call (e.g.
send_telegram_alert.assert_called_once()) is always looking at the one
mock actually wired into that call, with nothing else silently
re-patching the same name underneath it.
"""
import os
import unittest
from unittest.mock import patch, MagicMock

os.environ.setdefault("DATA_GOV_API_KEY", "test-key-not-real")

import main  # noqa: E402
from fetch_prices import DataFetchError  # noqa: E402

SAMPLE_RECORDS = [
    {"state": "Punjab", "market": "Ludhiana APMC", "min_price": "700", "max_price": "900", "modal_price": "800"},
]

# Patches common to every test that gets past the fetch step: the
# script/audio/video/thumbnail stages, none of which are what these tests
# are exercising. Applied via multiple decorators (bottom-up call order)
# rather than a shared context list, so each test's OWN with-block is free
# to patch fetch_prices / publish_state / save_today_prices /
# send_telegram_alert / upload_video however that specific test needs,
# with no risk of a second patcher for the same name overriding it.
def _with_render_stages_mocked(test_func):
    @patch("main.os.path.exists", return_value=False)
    @patch("main.generate_thumbnail", return_value=None)
    @patch("main.make_video", return_value=None)
    @patch("main.make_audio", return_value=None)
    @patch("main.build_script_and_captions", return_value=("script text", {
        "intro": "intro", "markets": [], "trend": None, "trend_data": None,
    }))
    @patch("main.load_yesterday_prices", return_value={})
    def wrapper(self, *args, **kwargs):
        return test_func(self, *args, **kwargs)
    return wrapper


class TestRunPipelineDataFailure(unittest.TestCase):
    """Requirement 4: a genuine upstream data failure must produce
    RESULT_FAILED, not be swallowed as success."""

    @_with_render_stages_mocked
    def test_data_fetch_error_returns_failed_and_alerts(self, *_mocked_render_stages):
        with patch("main.publish_state.is_published", return_value=False), \
             patch("main.fetch_prices", side_effect=DataFetchError("502 after retries")), \
             patch("main.send_telegram_alert") as mock_alert:
            result = main.run_pipeline("Punjab", "Potato")

        self.assertEqual(result, main.RESULT_FAILED)
        mock_alert.assert_called_once()


class TestRunPipelineEmptyResult(unittest.TestCase):
    """Requirement 10: a legitimate empty result is a skip, not a failure,
    and must not alert."""

    @_with_render_stages_mocked
    def test_empty_records_returns_skipped_no_alert(self, *_mocked_render_stages):
        with patch("main.publish_state.is_published", return_value=False), \
             patch("main.fetch_prices", return_value=[]), \
             patch("main.send_telegram_alert") as mock_alert:
            result = main.run_pipeline("Punjab", "Potato")

        self.assertEqual(result, main.RESULT_SKIPPED_NO_DATA)
        mock_alert.assert_not_called()


class TestRunPipelineAlreadyPublished(unittest.TestCase):
    def test_already_published_skips_before_any_fetch(self):
        with patch("main.publish_state.is_published", return_value=True), \
             patch("main.fetch_prices") as mock_fetch:
            result = main.run_pipeline("Punjab", "Potato")

        self.assertEqual(result, main.RESULT_SKIPPED_ALREADY_PUBLISHED)
        mock_fetch.assert_not_called()


class TestRunPipelineUploadFailure(unittest.TestCase):
    """Requirement 8: a failed upload must not be recorded as published,
    and must remain eligible for a future retry."""

    @_with_render_stages_mocked
    def test_upload_failure_does_not_mark_published(self, *_mocked_render_stages):
        with patch("main.publish_state.is_published", return_value=False), \
             patch("main.publish_state.mark_published") as mock_mark, \
             patch("main.fetch_prices", return_value=SAMPLE_RECORDS), \
             patch("main.upload_video", side_effect=RuntimeError("YouTube quota exceeded")), \
             patch("main.save_today_prices") as mock_save, \
             patch("main.send_telegram_alert") as mock_alert:
            result = main.run_pipeline("Punjab", "Potato")

        self.assertEqual(result, main.RESULT_FAILED)
        mock_mark.assert_not_called()
        mock_save.assert_not_called()
        mock_alert.assert_called_once()


class TestRunPipelineSuccess(unittest.TestCase):
    """Requirement 7 (integration angle): a successful upload IS recorded,
    as a distinct write from price history."""

    @_with_render_stages_mocked
    def test_successful_upload_marks_published_and_saves_history(self, *_mocked_render_stages):
        with patch("main.publish_state.is_published", return_value=False), \
             patch("main.publish_state.mark_published") as mock_mark, \
             patch("main.fetch_prices", return_value=SAMPLE_RECORDS), \
             patch("main.upload_video", return_value="video123"), \
             patch("main.save_today_prices") as mock_save:
            result = main.run_pipeline("Punjab", "Potato")

        self.assertEqual(result, main.RESULT_SUCCESS)
        mock_save.assert_called_once()
        mock_mark.assert_called_once()
        # video_id from upload_video must be what gets recorded.
        self.assertEqual(mock_mark.call_args.args[-1], "video123")


class TestRunPipelineDateConsistency(unittest.TestCase):
    """Regression test for a review finding: today_iso (publish_state's
    identity key, checked/recorded at the start and end of run_pipeline())
    and today_str (the date burned into the video/thumbnail/title) must
    come from ONE datetime.now(IST) snapshot -- not two separate calls
    that could disagree if real time crosses an IST midnight during the
    now-up-to-~99s retried fetch in between them."""

    def test_today_str_date_matches_today_iso_across_a_midnight_boundary(self):
        import datetime as datetime_module

        # Simulates the fetch call landing just before IST midnight, and
        # any LATER datetime.now(IST) call (a regression back to two
        # separate calls, or _todays_format()'s own call) landing just
        # after it -- proving today_str is NOT derived from that later
        # call.
        before_midnight = datetime_module.datetime(2026, 9, 12, 23, 59, 59, tzinfo=main.IST)
        after_midnight = datetime_module.datetime(2026, 9, 13, 0, 1, 0, tzinfo=main.IST)

        with patch("main.datetime") as mock_datetime_cls, \
             patch("main.publish_state.is_published", return_value=False), \
             patch("main.publish_state.mark_published"), \
             patch("main.load_yesterday_prices", return_value={}), \
             patch("main.build_script_and_captions", return_value=("script", {
                 "intro": "intro", "markets": [], "trend": None, "trend_data": None,
             })), \
             patch("main.make_audio", return_value=None), \
             patch("main.make_video") as mock_make_video, \
             patch("main.generate_thumbnail", return_value=None), \
             patch("main.fetch_prices", return_value=SAMPLE_RECORDS), \
             patch("main.upload_video", return_value="video123"), \
             patch("main.save_today_prices"), \
             patch("main.os.path.exists", return_value=False):
            # First call is run_pipeline()'s own now_ist snapshot; any
            # further calls (a regression, or _todays_format()'s separate
            # one) land after midnight to prove they're not what today_str
            # is built from.
            mock_datetime_cls.now.side_effect = [before_midnight] + [after_midnight] * 10
            main.run_pipeline("Punjab", "Potato")

        today_str_used = mock_make_video.call_args.kwargs["date_str"]
        today_str_date_iso = datetime_module.datetime.strptime(today_str_used, "%d %b %Y").date().isoformat()
        self.assertEqual(today_str_date_iso, "2026-09-12")


class TestMainMultiTargetContinuesAfterFailure(unittest.TestCase):
    """Requirement 9: one target's permanent failure must not stop the
    others in the same workflow_dispatch run."""

    def test_all_targets_attempted_and_exit_code_reflects_failure(self):
        fake_targets = [
            {"state": "A", "commodity": "X", "lang": "hi"},
            {"state": "B", "commodity": "Y", "lang": "hi"},
            {"state": "C", "commodity": "Z", "lang": "hi"},
        ]
        run_pipeline_mock = MagicMock(side_effect=[
            main.RESULT_SUCCESS, main.RESULT_FAILED, main.RESULT_SUCCESS,
        ])
        env_without_single_target = {k: v for k, v in os.environ.items() if k not in ("YT_STATE", "YT_COMMODITY")}
        with patch.dict(os.environ, env_without_single_target, clear=True), \
             patch("main.TARGETS", fake_targets), \
             patch("main.run_pipeline", run_pipeline_mock):
            exit_code = main.main()

        self.assertEqual(run_pipeline_mock.call_count, 3)
        self.assertEqual(exit_code, 1)


class TestMainSingleTargetEmptyResultIsNotFailure(unittest.TestCase):
    """Requirement 10, at the main()-level exit code."""

    def test_single_target_skip_returns_exit_code_zero(self):
        with patch.dict(os.environ, {"YT_STATE": "Punjab", "YT_COMMODITY": "Potato"}), \
             patch("main.run_pipeline", return_value=main.RESULT_SKIPPED_NO_DATA):
            exit_code = main.main()
        self.assertEqual(exit_code, 0)

    def test_single_target_failure_returns_exit_code_one(self):
        with patch.dict(os.environ, {"YT_STATE": "Punjab", "YT_COMMODITY": "Potato"}), \
             patch("main.run_pipeline", return_value=main.RESULT_FAILED):
            exit_code = main.main()
        self.assertEqual(exit_code, 1)


if __name__ == "__main__":
    unittest.main()
