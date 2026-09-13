"""Covers Phase 1A requirements 4, 8, 9, 10, and Phase 1B-B's canonical-date
architecture (see docs/RELIABILITY.md and TAAZABHAV_PHASE_1B-B_*.md):
  4. Pipeline failure status when required data cannot be retrieved.
  8. A failed upload does not incorrectly mark content as published.
  9. A multi-target run where one target permanently fails still attempts
     the remaining targets, using the SAME canonical run_date throughout.
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
from datetime import date
from unittest.mock import patch, MagicMock

os.environ.setdefault("DATA_GOV_API_KEY", "test-key-not-real")

import main  # noqa: E402
from fetch_prices import DataFetchError  # noqa: E402

SAMPLE_RECORDS = [
    {"state": "Punjab", "market": "Ludhiana APMC", "min_price": "700", "max_price": "900", "modal_price": "800"},
]

# A fixed, arbitrary canonical run_date used throughout this file wherever a
# test calls the real run_pipeline() (which now requires one explicitly --
# Phase 1B-B). Using one shared constant makes every test's intent obvious:
# "this is the date the whole pipeline run was given," never "today."
TEST_RUN_DATE = date(2026, 9, 12)

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
            result = main.run_pipeline("Punjab", "Potato", TEST_RUN_DATE)

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
            result = main.run_pipeline("Punjab", "Potato", TEST_RUN_DATE)

        self.assertEqual(result, main.RESULT_SKIPPED_NO_DATA)
        mock_alert.assert_not_called()


class TestRunPipelineAlreadyPublished(unittest.TestCase):
    def test_already_published_skips_before_any_fetch(self):
        with patch("main.publish_state.is_published", return_value=True), \
             patch("main.fetch_prices") as mock_fetch:
            result = main.run_pipeline("Punjab", "Potato", TEST_RUN_DATE)

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
            result = main.run_pipeline("Punjab", "Potato", TEST_RUN_DATE)

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
            result = main.run_pipeline("Punjab", "Potato", TEST_RUN_DATE)

        self.assertEqual(result, main.RESULT_SUCCESS)
        mock_save.assert_called_once()
        mock_mark.assert_called_once()
        # video_id from upload_video must be what gets recorded.
        self.assertEqual(mock_mark.call_args.args[-1], "video123")
        # save_today_prices must receive the SAME run_date run_pipeline was
        # given, not one it computed itself (Phase 1B-B).
        self.assertEqual(mock_save.call_args.args[-1], TEST_RUN_DATE)


class TestCanonicalDateUsage(unittest.TestCase):
    """Phase 1B-B TEST 2 (script date) and TEST 4 (date consistency):
    run_pipeline() must pass the SAME explicitly-supplied run_date to every
    business-date-dependent component (script generation, history, title),
    and must never compute its own -- run_pipeline() no longer imports or
    calls datetime.now()/date.today() at all for this purpose, so there is
    nothing left inside it capable of independently determining the date."""

    def test_run_date_flows_unchanged_to_script_history_and_title(self):
        with patch("main.publish_state.is_published", return_value=False) as mock_is_published, \
             patch("main.publish_state.mark_published"), \
             patch("main.load_yesterday_prices", return_value={}), \
             patch("main.fetch_prices", return_value=SAMPLE_RECORDS), \
             patch("main.upload_video", return_value="video123"), \
             patch("main.save_today_prices") as mock_save, \
             patch("main.build_script_and_captions", return_value=("script text", {
                 "intro": "intro", "markets": [], "trend": None, "trend_data": None,
             })) as mock_build_script, \
             patch("main.make_audio", return_value=None), \
             patch("main.make_video") as mock_make_video, \
             patch("main.generate_thumbnail", return_value=None), \
             patch("main.os.path.exists", return_value=False):
            main.run_pipeline("Punjab", "Potato", TEST_RUN_DATE)

        # 1. publish_state's identity key is derived from run_date, not a
        #    fresh clock read.
        self.assertEqual(mock_is_published.call_args.args[0], TEST_RUN_DATE.isoformat())
        # 2. generate_script.build_script_and_captions() receives run_date
        #    explicitly as its own argument (Phase 1B-B Part 2).
        self.assertIn(TEST_RUN_DATE, mock_build_script.call_args.args)
        # 3. The video title/thumbnail date_str is derived from the exact
        #    same run_date (Phase 1B-B Part 4 -- title and script must not
        #    just both be "correct", they must be provably the SAME source).
        expected_today_str = TEST_RUN_DATE.strftime("%d %b %Y")
        self.assertEqual(mock_make_video.call_args.kwargs["date_str"], expected_today_str)
        # 4. price_history.save_today_prices() receives the same run_date too.
        self.assertEqual(mock_save.call_args.args[-1], TEST_RUN_DATE)

    def test_run_pipeline_never_calls_datetime_now_or_date_today(self):
        """Belt-and-suspenders architectural check: after Phase 1B-B,
        run_pipeline() has no code path that can independently determine
        a business date, because it no longer references datetime.now()
        or date.today() anywhere for that purpose. This patches BOTH to
        raise if called at all during a full run_pipeline() execution."""
        def _fail_if_called(*args, **kwargs):
            raise AssertionError("run_pipeline() must not compute its own current date/time")

        with patch("main.publish_state.is_published", return_value=False), \
             patch("main.publish_state.mark_published"), \
             patch("main.load_yesterday_prices", return_value={}), \
             patch("main.build_script_and_captions", return_value=("script text", {
                 "intro": "intro", "markets": [], "trend": None, "trend_data": None,
             })), \
             patch("main.make_audio", return_value=None), \
             patch("main.make_video", return_value=None), \
             patch("main.generate_thumbnail", return_value=None), \
             patch("main.fetch_prices", return_value=SAMPLE_RECORDS), \
             patch("main.upload_video", return_value="video123"), \
             patch("main.save_today_prices"), \
             patch("main.os.path.exists", return_value=False), \
             patch("main.datetime") as mock_datetime_cls:
            # Replaces the `datetime` NAME as seen inside main.py only (not
            # the real, global datetime.datetime class), so this can't leak
            # into any other module -- if run_pipeline() calls
            # main.datetime.now(...) anywhere, this raises immediately.
            mock_datetime_cls.now.side_effect = _fail_if_called
            result = main.run_pipeline("Punjab", "Potato", TEST_RUN_DATE)

        self.assertEqual(result, main.RESULT_SUCCESS)


class TestMidnightSafety(unittest.TestCase):
    """Phase 1B-B TEST 5 (midnight crossing), at the main()-level: the
    canonical run_date must be computed exactly ONCE per process execution
    (inside get_canonical_run_date(), called once at the top of main()),
    so a run that takes long enough to cross IST midnight -- entirely
    realistic given fetch_prices.py's retries can now take up to ~99s per
    target, and a multi-target workflow_dispatch run can take many minutes
    -- still uses the date that was current when the run STARTED, for
    every target, not a freshly-read later date."""

    def test_run_date_computed_once_and_reused_across_all_targets(self):
        import datetime as datetime_module

        before_midnight = datetime_module.datetime(2026, 9, 12, 23, 59, 0, tzinfo=main.IST)
        after_midnight = datetime_module.datetime(2026, 9, 13, 0, 10, 0, tzinfo=main.IST)

        fake_targets = [
            {"state": "A", "commodity": "X", "lang": "hi"},
            {"state": "B", "commodity": "Y", "lang": "hi"},
            {"state": "C", "commodity": "Z", "lang": "hi"},
        ]
        captured_run_dates = []

        def fake_run_pipeline(state, commodity, run_date, lang="hi"):
            captured_run_dates.append(run_date)
            return main.RESULT_SUCCESS

        # Only the FIRST datetime.now(IST) call (get_canonical_run_date(),
        # called once at the top of main()) should ever happen; every
        # later value in this list simulates what a regression back to
        # per-target date computation would see -- all safely after
        # midnight, so the test fails loudly if anything re-reads the clock.
        with patch("main.datetime") as mock_datetime_cls, \
             patch("main.TARGETS", fake_targets), \
             patch("main.run_pipeline", side_effect=fake_run_pipeline), \
             patch.dict(os.environ, {k: v for k, v in os.environ.items() if k not in ("YT_STATE", "YT_COMMODITY")}, clear=True):
            mock_datetime_cls.now.side_effect = [before_midnight] + [after_midnight] * 10
            exit_code = main.main()

        self.assertEqual(mock_datetime_cls.now.call_count, 1)
        self.assertEqual(exit_code, 0)
        self.assertEqual(len(captured_run_dates), 3)
        # Every target -- including the third, processed "later" in this
        # simulated run -- must have received the SAME pre-midnight date.
        self.assertTrue(all(d == date(2026, 9, 12) for d in captured_run_dates))

    def test_get_canonical_run_date_uses_asia_kolkata(self):
        """Phase 1B-B TEST 1: the canonical date is computed from
        Asia/Kolkata (UTC+5:30), not the server's own local/UTC clock."""
        import datetime as datetime_module

        # A UTC instant where the UTC calendar date and the IST calendar
        # date genuinely differ, so this test is meaningful (not
        # accidentally passing regardless of which timezone was used).
        utc_instant = datetime_module.datetime(2026, 9, 12, 23, 45, 0, tzinfo=datetime_module.timezone.utc)
        ist_instant = utc_instant.astimezone(main.IST)
        self.assertEqual(main.IST.utcoffset(None), datetime_module.timedelta(hours=5, minutes=30))

        with patch("main.datetime") as mock_datetime_cls:
            mock_datetime_cls.now.return_value = ist_instant
            run_date = main.get_canonical_run_date()

        mock_datetime_cls.now.assert_called_once_with(main.IST)
        self.assertEqual(run_date, date(2026, 9, 13))  # IST has already rolled to the 13th
        self.assertNotEqual(run_date, utc_instant.date())  # while UTC is still the 12th


class TestMainMultiTargetContinuesAfterFailure(unittest.TestCase):
    """Requirement 9: one target's permanent failure must not stop the
    others in the same workflow_dispatch run, and every target still
    receives the same canonical run_date (Phase 1B-B)."""

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
        # All three calls must have been given the exact same run_date
        # (the 3rd positional arg: state, commodity, run_date, lang).
        run_dates_seen = {call.args[2] for call in run_pipeline_mock.call_args_list}
        self.assertEqual(len(run_dates_seen), 1)


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
