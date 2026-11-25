# -*- coding: utf-8 -*-
import os
import unittest
from datetime import date
from unittest import mock

import meta_publish as mp
from posts import shaam


class MetaOnTest(unittest.TestCase):
    def test_default_reels(self):
        with mock.patch.dict(os.environ, {"META_ON": ""}):
            on = [k for k in mp.META_KINDS if mp.on_meta(k)]
        self.assertEqual(sorted(on), ["Y"])  # V is not in META_KINDS; Y+V default (24 Nov 2026)

    def test_variable_overrides(self):
        with mock.patch.dict(os.environ, {"META_ON": "all"}):
            self.assertTrue(all(mp.on_meta(k) for k in mp.META_KINDS))
        with mock.patch.dict(os.environ, {"META_ON": " bhav, C "}):
            self.assertTrue(mp.on_meta("bhav") and mp.on_meta("C"))
            self.assertFalse(mp.on_meta("A") or mp.on_meta("tool"))

    def test_off_formats_post_nothing(self):
        from posts import bhav, pillar, run
        with mock.patch.dict(os.environ, {"META_ON": "A,D,B", "BHAV_POSTS_LIVE": "1", "POSTS_LIVE": "1", "PILLAR_LIVE": "1"}), \
                mock.patch("sys.argv", ["x"]), mock.patch("posts.run.publish") as pub, mock.patch("posts.bhav.publish") as pub2, \
                mock.patch("posts.pillar.publish") as pub3:
            self.assertEqual(run.main(), 0)
            self.assertEqual(bhav.main(), 0)
            self.assertEqual(pillar.main(), 0)
        pub.assert_not_called(); pub2.assert_not_called(); pub3.assert_not_called()

    def test_engine_series_off_skips_meta(self):
        from engine import publish
        with mock.patch.dict(os.environ, {"META_ON": "A,D,B", "META_TOKEN": "t", "FB_PAGE_ID": "p"}), \
                mock.patch("meta_publish.publish_all") as pa:
            self.assertIsNone(publish.meta_reels("x.mp4", {"series": "C", "title": "t", "description": "d"}, print))
        pa.assert_not_called()

    def test_shaam_falls_back_to_reel(self):
        day = date(2026, 10, 27)
        led = [{"date": "2026-10-27", "format": "reel", "slot": "07:30", "facebook": "f1"},
               {"date": "2026-10-27", "format": "reel", "slot": "12:30", "facebook": "f2"}]
        post, slot = shaam.target(day, led)
        self.assertEqual((post["facebook"], slot), ("f2", "12:30"))
        led.append({"date": "2026-10-27", "format": "photo", "slot": "14:30", "facebook": "f3"})
        self.assertEqual(shaam.target(day, led)[1], "14:30")
        self.assertEqual(shaam.target(day, [])[0], None)


if __name__ == "__main__":
    unittest.main()


class IgSafeCopyTest(unittest.TestCase):
    def test_falls_back_to_original_when_ffmpeg_fails(self):
        with mock.patch("subprocess.run", side_effect=OSError("no ffmpeg")):
            self.assertEqual(mp.ig_safe_copy("/tmp/x.mp4"), "/tmp/x.mp4")

    def test_second_try_uses_reencoded_file(self):
        seen = []
        def fake_ig(src, *a, **k):
            seen.append(src)
            if len(seen) == 1:
                raise mp.MetaError("boom")
            return "ig1"
        with mock.patch.dict(os.environ, {"META_TOKEN": "t", "FB_PAGE_ID": "p"}), \
                mock.patch.object(mp, "page_credentials", return_value=("tok", "ig")), \
                mock.patch.object(mp, "post_facebook_reel", return_value="fb1"), \
                mock.patch.object(mp, "post_instagram_reel", side_effect=fake_ig), \
                mock.patch.object(mp, "ig_safe_copy", return_value="/tmp/x_ig.mp4"), \
                mock.patch.object(mp, "link_comment", return_value=(None, None)), \
                mock.patch.object(mp, "comments_live", return_value=False), \
                mock.patch.object(mp, "meta_stories", create=True, return_value={}):
            out = mp.publish_all("/tmp/x.mp4", "cap")
        self.assertEqual(seen, ["/tmp/x.mp4", "/tmp/x_ig.mp4"])
        self.assertEqual(out["instagram"], "ig1")
