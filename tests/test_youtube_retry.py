# -*- coding: utf-8 -*-
"""YouTube's passing errors are retried, real errors are not, and a failed
playlist add is retried on the next video without duplicates (20 Oct 2026)."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from googleapiclient.errors import HttpError

import upload_youtube
from engine import publish


def http_error(status, reason="SERVICE_UNAVAILABLE"):
    resp = mock.Mock(status=status, reason="x")
    body = json.dumps({"error": {"errors": [{"reason": reason}], "message": "The operation was aborted."}}).encode()
    return HttpError(resp, body)


class Req:
    def __init__(self, *outcomes):
        self.outcomes, self.calls = list(outcomes), 0

    def execute(self):
        self.calls += 1
        o = self.outcomes.pop(0)
        if isinstance(o, Exception):
            raise o
        return o


class ExecuteTest(unittest.TestCase):
    def test_passing_errors_are_retried(self):
        for status in (409, 429, 500, 502, 503, 504):
            r = Req(http_error(status), http_error(status), {"ok": 1})
            self.assertEqual(upload_youtube.execute(r, sleep=lambda s: None), {"ok": 1}, status)
            self.assertEqual(r.calls, 3)

    def test_real_errors_fail_at_once(self):
        for status in (400, 401, 403, 404):
            r = Req(http_error(status, "forbidden"), {"ok": 1})
            with self.assertRaises(HttpError):
                upload_youtube.execute(r, sleep=lambda s: None)
            self.assertEqual(r.calls, 1)

    def test_gives_up_after_all_waits(self):
        waits = []
        r = Req(*[http_error(409)] * 4)
        with self.assertRaises(HttpError):
            upload_youtube.execute(r, sleep=waits.append)
        self.assertEqual(waits, list(upload_youtube.RETRY_WAITS))
        self.assertEqual(r.calls, 4)


class FakeYT:
    """playlistItems().insert fails `fail` times per video with a 409."""

    def __init__(self, fail=0, existing=()):
        self.fail, self.added, self.existing = fail, [], set(existing)
        self.tries = {}

    def playlistItems(self):
        return self

    def list(self, part, playlistId, videoId):
        return Req({"items": [1] if videoId in self.existing or videoId in self.added else []})

    def insert(self, part, body):
        vid = body["snippet"]["resourceId"]["videoId"]
        yt = self

        class Insert:
            def execute(self):
                n = yt.tries.get(vid, 0)
                yt.tries[vid] = n + 1
                if n < yt.fail:
                    raise http_error(409)
                yt.added.append(vid)
                return {"id": "x"}
        return Insert()


class PlaylistTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        d = Path(self.tmp.name)
        self.p = [mock.patch.object(publish, "PLAYLIST_PENDING", d / "pending.json"),
                  mock.patch.object(publish, "PLAYLISTS", d / "pl.json"),
                  mock.patch.object(upload_youtube, "RETRY_WAITS", (0, 0, 0))]
        for p in self.p:
            p.start()
        (d / "pl.json").write_text(json.dumps({s: f"PL{s}" for s in "ABCD"}))
        self.alerts = []

    def tearDown(self):
        for p in self.p:
            p.stop()
        self.tmp.cleanup()

    def test_one_409_is_retried_and_not_alerted(self):
        yt = FakeYT(fail=1)
        for series in "ABCD":
            self.assertEqual(publish.add_to_playlists(series, f"v{series}", self.alerts.append, yt), [])
        self.assertEqual(yt.added, ["vA", "vB", "vC", "vD"])
        self.assertEqual(self.alerts, [])

    def test_lasting_failure_is_kept_and_added_with_next_video(self):
        left = publish.add_to_playlists("B", "v1", self.alerts.append, FakeYT(fail=99))
        self.assertEqual(left, [{"series": "B", "video": "v1"}])
        self.assertEqual(len(self.alerts), 1)
        yt = FakeYT()
        self.assertEqual(publish.add_to_playlists("A", "v2", self.alerts.append, yt), [])
        self.assertEqual(yt.added, ["v1", "v2"])
        self.assertEqual(len(self.alerts), 1)

    def test_pending_video_already_in_playlist_is_not_added_twice(self):
        publish.PLAYLIST_PENDING.write_text(json.dumps([{"series": "B", "video": "HSgV2jIHyOw"}]))
        yt = FakeYT(existing={"HSgV2jIHyOw"})
        publish.add_to_playlists("A", "v3", self.alerts.append, yt)
        self.assertEqual(yt.added, ["v3"])

    def test_repo_pending_file_is_valid(self):
        items = json.loads(Path("data/engine/playlist_pending.json").read_text())
        self.assertTrue(all(set(i) == {"series", "video"} for i in items))


if __name__ == "__main__":
    unittest.main()
