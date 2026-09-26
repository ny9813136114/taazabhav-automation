"""Covers Phase 1A requirements 1-3:
  1. Successful API response.
  2. Temporary API failure followed by a successful retry.
  3. Permanent API failure (retries exhausted -> DataFetchError).
Plus: a non-retryable 4xx error must fail immediately, without retrying.

No real network calls are made -- requests.get is patched throughout.
"""
import os
import unittest
from unittest.mock import patch, MagicMock

# fetch_prices.py reads DATA_GOV_API_KEY at import time; tests must not
# depend on a real secret being present.
os.environ.setdefault("DATA_GOV_API_KEY", "test-key-not-real")

import fetch_prices  # noqa: E402


def _response(status_code, json_body=None):
    resp = MagicMock()
    resp.status_code = status_code
    resp.reason = "error"
    resp.url = "https://api.data.gov.in/resource/fake"
    resp.json.return_value = json_body or {}
    if status_code >= 400:
        import requests
        resp.raise_for_status.side_effect = requests.exceptions.HTTPError(
            f"{status_code} error", response=resp
        )
    else:
        resp.raise_for_status.return_value = None
    return resp


class TestSuccessfulResponse(unittest.TestCase):
    @patch("fetch_prices.time.sleep", return_value=None)
    @patch("fetch_prices.requests.get")
    def test_success_on_first_attempt(self, mock_get, mock_sleep):
        mock_get.return_value = _response(200, {"records": [{"state": "Uttar Pradesh", "market": "Lucknow APMC", "modal_price": "3000"}]})

        records = fetch_prices.fetch_all_states("Onion")

        self.assertEqual(len(records), 1)
        self.assertEqual(mock_get.call_count, 1)
        mock_sleep.assert_not_called()


class TestRetryRecovery(unittest.TestCase):
    @patch("fetch_prices.time.sleep", return_value=None)
    @patch("fetch_prices.requests.get")
    def test_502_then_success_recovers(self, mock_get, mock_sleep):
        mock_get.side_effect = [
            _response(502),
            _response(200, {"records": [{"state": "Punjab", "market": "Ludhiana APMC", "modal_price": "1200"}]}),
        ]

        records = fetch_prices.fetch_all_states("Potato")

        self.assertEqual(len(records), 1)
        self.assertEqual(mock_get.call_count, 2)
        mock_sleep.assert_called_once_with(fetch_prices.BACKOFF_SECONDS[0])


class TestPermanentFailure(unittest.TestCase):
    @patch("fetch_prices.time.sleep", return_value=None)
    @patch("fetch_prices.requests.get")
    def test_all_attempts_502_raises_data_fetch_error(self, mock_get, mock_sleep):
        mock_get.return_value = _response(502)

        with self.assertRaises(fetch_prices.DataFetchError):
            fetch_prices.fetch_all_states("Onion")

        self.assertEqual(mock_get.call_count, fetch_prices.MAX_ATTEMPTS)
        self.assertEqual(mock_sleep.call_count, fetch_prices.MAX_ATTEMPTS - 1)

    @patch("fetch_prices.time.sleep", return_value=None)
    @patch("fetch_prices.requests.get")
    def test_non_retryable_4xx_fails_immediately(self, mock_get, mock_sleep):
        mock_get.return_value = _response(401)

        with self.assertRaises(fetch_prices.DataFetchError):
            fetch_prices.fetch_all_states("Onion")

        # A bad api-key/request can never succeed by retrying -- must not
        # waste the retry budget on it.
        self.assertEqual(mock_get.call_count, 1)
        mock_sleep.assert_not_called()


class TestRetryableEdgeCases(unittest.TestCase):
    """Covers two review findings from the Phase 1A branch review:
    a malformed (non-JSON) 200 response must be retried the same as a
    5xx, and 429 (Too Many Requests) must be retryable, not treated as a
    permanent client error."""

    @patch("fetch_prices.time.sleep", return_value=None)
    @patch("fetch_prices.requests.get")
    def test_malformed_json_body_is_retried(self, mock_get, mock_sleep):
        bad_json_resp = _response(200)
        bad_json_resp.json.side_effect = ValueError("Expecting value: line 1 column 1 (char 0)")
        good_resp = _response(200, {"records": [{"state": "Punjab", "market": "Ludhiana APMC", "modal_price": "1200"}]})
        mock_get.side_effect = [bad_json_resp, good_resp]

        records = fetch_prices.fetch_all_states("Potato")

        self.assertEqual(len(records), 1)
        self.assertEqual(mock_get.call_count, 2)

    @patch("fetch_prices.time.sleep", return_value=None)
    @patch("fetch_prices.requests.get")
    def test_429_is_retryable(self, mock_get, mock_sleep):
        mock_get.side_effect = [
            _response(429),
            _response(200, {"records": [{"state": "Punjab", "market": "Ludhiana APMC", "modal_price": "1200"}]}),
        ]

        records = fetch_prices.fetch_all_states("Potato")

        self.assertEqual(len(records), 1)
        self.assertEqual(mock_get.call_count, 2)
        mock_sleep.assert_called_once()


class TestStateFiltering(unittest.TestCase):
    @patch("fetch_prices.time.sleep", return_value=None)
    @patch("fetch_prices.requests.get")
    def test_fetch_prices_filters_locally_by_state(self, mock_get, mock_sleep):
        mock_get.return_value = _response(200, {"records": [
            {"state": "Uttar Pradesh", "market": "Lucknow APMC", "modal_price": "3000"},
            {"state": "Tamil Nadu", "market": "Ooty APMC", "modal_price": "5000"},
        ]})

        records = fetch_prices.fetch_prices(state="Uttar Pradesh", commodity="Onion")

        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["market"], "Lucknow APMC")

    def test_empty_result_is_not_an_error(self):
        # filter_by_state on an empty/non-matching list must return [] --
        # this is the "legitimate no data today" case, never an exception.
        result = fetch_prices.filter_by_state(
            [{"state": "Tamil Nadu", "market": "Ooty APMC", "modal_price": "5000"}],
            "Uttar Pradesh",
        )
        self.assertEqual(result, [])


class TestPaging(unittest.TestCase):
    """Batch 1 (26 Sep 2026): one limit=500 call silently dropped every
    state the API listed after row 500. fetch_all_states must page with
    offset until a short page comes back."""

    @patch("fetch_prices.time.sleep", return_value=None)
    @patch("fetch_prices.requests.get")
    def test_pages_until_short_page(self, mock_get, mock_sleep):
        full = [{"state": "Uttar Pradesh", "market": f"M{i}", "modal_price": "1000"} for i in range(fetch_prices.PAGE_SIZE)]
        tail = [{"state": "Karnataka", "market": "Kolar", "modal_price": "900"}]
        mock_get.side_effect = [_response(200, {"records": full}), _response(200, {"records": tail})]

        records = fetch_prices.fetch_all_states("Tomato")

        self.assertEqual(len(records), fetch_prices.PAGE_SIZE + 1)
        self.assertEqual(mock_get.call_count, 2)
        offsets = [c.kwargs["params"]["offset"] for c in mock_get.call_args_list]
        self.assertEqual(offsets, [0, fetch_prices.PAGE_SIZE])

    @patch("fetch_prices.time.sleep", return_value=None)
    @patch("fetch_prices.requests.get")
    def test_stops_at_api_total(self, mock_get, mock_sleep):
        full = [{"state": "Punjab", "market": f"M{i}", "modal_price": "1000"} for i in range(fetch_prices.PAGE_SIZE)]
        mock_get.return_value = _response(200, {"records": full, "total": fetch_prices.PAGE_SIZE})

        records = fetch_prices.fetch_all_states("Potato")

        self.assertEqual(len(records), fetch_prices.PAGE_SIZE)
        self.assertEqual(mock_get.call_count, 1)

    @patch("fetch_prices.time.sleep", return_value=None)
    @patch("fetch_prices.requests.get")
    def test_failed_later_page_raises(self, mock_get, mock_sleep):
        full = [{"state": "Punjab", "market": f"M{i}", "modal_price": "1000"} for i in range(fetch_prices.PAGE_SIZE)]
        mock_get.side_effect = [_response(200, {"records": full})] + [_response(502)] * fetch_prices.MAX_ATTEMPTS

        with self.assertRaises(fetch_prices.DataFetchError):
            fetch_prices.fetch_all_states("Potato")


class TestCleanRecords(unittest.TestCase):
    """Batch 1: real on-screen errors from the 25 Sep UP onion Short."""

    def test_sorted_highest_first_and_whole_rupees(self):
        rows = [
            {"market": "Najibabad APMC", "modal_price": "2311.09", "min_price": "2000", "max_price": "2500.5"},
            {"market": "Tilhar APMC", "modal_price": "5983", "min_price": "5000", "max_price": "6000"},
            {"market": "Ghaziabad APMC", "modal_price": "4042.26"},
        ]
        out = fetch_prices.clean_records(rows)
        self.assertEqual([r["market"] for r in out], ["Tilhar APMC", "Ghaziabad APMC", "Najibabad APMC"])
        self.assertEqual(out[2]["modal_price"], 2311)
        self.assertEqual(out[2]["max_price"], 2501)
        # missing min/max fall back to modal, never "N/A" on screen
        self.assertEqual(out[1]["min_price"], 4042)

    def test_one_row_per_market_uses_median_variety(self):
        rows = [
            {"market": "Tilhar APMC", "modal_price": "5983", "variety": "Big"},
            {"market": "Tilhar APMC", "modal_price": "3000", "variety": "Local"},
            {"market": "tilhar apmc ", "modal_price": "4000", "variety": "Red"},
        ]
        out = fetch_prices.clean_records(rows)
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["modal_price"], 4000)

    def test_drops_missing_or_non_positive_modal(self):
        rows = [
            {"market": "A", "modal_price": "0"},
            {"market": "B", "modal_price": "N/A"},
            {"market": "C"},
            {"market": "D", "modal_price": "1500"},
        ]
        out = fetch_prices.clean_records(rows)
        self.assertEqual([r["market"] for r in out], ["D"])

    @patch("fetch_prices.time.sleep", return_value=None)
    @patch("fetch_prices.requests.get")
    def test_fetch_prices_returns_cleaned_sorted(self, mock_get, mock_sleep):
        mock_get.return_value = _response(200, {"records": [
            {"state": "Uttar Pradesh", "market": "Low", "modal_price": "1000"},
            {"state": "Uttar Pradesh", "market": "High", "modal_price": "3000.4"},
            {"state": "Bihar", "market": "Other", "modal_price": "9999"},
        ]})
        records = fetch_prices.fetch_prices(state="Uttar Pradesh", commodity="Onion")
        self.assertEqual([r["market"] for r in records], ["High", "Low"])
        self.assertEqual(records[0]["modal_price"], 3000)


if __name__ == "__main__":
    unittest.main()
