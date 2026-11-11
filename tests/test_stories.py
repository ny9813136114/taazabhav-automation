# -*- coding: utf-8 -*-
"""Stories (11 Nov 2026): every feed post and Reel also goes to FB + IG Story."""
import os
import sys
import tempfile
import unittest
from datetime import date, datetime
from pathlib import Path
from unittest import mock

import meta_publish as mp
import meta_stories as ms
from posts import bhav


def resp(body, code=200):
    r = mock.Mock(); r.status_code = code; r.json.return_value = body; r.text = str(body); return r


class StoryTest(unittest.TestCase):
    def setUp(self):
        self.env = mock.patch.dict(os.environ, {"META_TOKEN": "sys", "FB_PAGE_ID": "123"}); self.env.start()
        self.tmp = tempfile.mkdtemp()
        self.png = Path(self.tmp) / "s1.png"
        self.png.write_bytes(b"png")
        self.video = Path(self.tmp) / "v.mp4"
        self.video.write_bytes(b"x" * 10)

    def tearDown(self):
        self.env.stop()

    def test_photo_story_live_posts_fb_then_ig(self):
        s = mock.Mock()
        s.post.side_effect = [resp({"id": "ph1"}), resp({"success": True, "post_id": "st1"}),
                              resp({"id": "c1"}), resp({"id": "igst1"})]
        s.get.side_effect = [resp({"images": [{"width": 100, "source": "https://cdn/s"}, {"width": 1080, "source": "https://cdn/b"}]}),
                             resp({"status_code": "FINISHED"})]
        with mock.patch.dict(os.environ, {"STORIES_LIVE": "1"}), \
                mock.patch.object(ms, "story_image", return_value=self.png):
            out = ms.share_post("p1", [self.png], "pt", "ig1", s, sleep=lambda _: None)
        self.assertEqual(out, {"facebook": "st1", "instagram": "igst1", "errors": []})
        urls = [c.args[0] for c in s.post.call_args_list]
        self.assertTrue(urls[0].endswith("/123/photos"))
        self.assertTrue(urls[1].endswith("/123/photo_stories"))
        self.assertEqual(s.post.call_args_list[1].kwargs["data"]["photo_id"], "ph1")
        self.assertEqual(s.post.call_args_list[2].kwargs["data"]["media_type"], "STORIES")
        self.assertEqual(s.post.call_args_list[2].kwargs["data"]["image_url"], "https://cdn/b")

    def test_photo_story_preview_posts_nothing(self):
        s = mock.Mock()
        with mock.patch.dict(os.environ, {"STORIES_LIVE": ""}), \
                mock.patch.object(ms, "story_image", return_value=self.png), \
                mock.patch.object(ms, "_preview_photo") as prev:
            out = ms.share_post("p1", [self.png], "pt", "ig1", s)
        prev.assert_called_once()
        s.post.assert_not_called()
        self.assertEqual(out["errors"], [])

    def test_fb_story_error_still_tries_ig(self):
        s = mock.Mock()
        s.post.side_effect = [resp({"error": {"message": "no perm"}}, 400), resp({"id": "ph2"}),
                              resp({"id": "c1"}), resp({"id": "igst1"})]
        s.get.side_effect = [resp({"images": [{"width": 1080, "source": "https://cdn/b"}]}), resp({"status_code": "FINISHED"})]
        with mock.patch.dict(os.environ, {"STORIES_LIVE": "1"}), \
                mock.patch.object(ms, "story_image", return_value=self.png):
            out = ms.share_post("p1", [self.png], "pt", "ig1", s, sleep=lambda _: None)
        self.assertIsNone(out["facebook"])
        self.assertEqual(out["instagram"], "igst1")
        self.assertIn("no perm", out["errors"][0])

    def test_reel_story_live(self):
        s = mock.Mock()
        s.post.side_effect = [resp({"video_id": "v9", "upload_url": "https://up/v9"}), resp({"success": True}),
                              resp({"success": True, "post_id": "fbst"}),
                              resp({"id": "c9", "uri": "https://up/c9"}), resp({"success": True}), resp({"id": "igst"})]
        s.get.side_effect = [resp({"status_code": "FINISHED"})]
        with mock.patch.dict(os.environ, {"STORIES_LIVE": "1"}), mock.patch.object(ms, "video_seconds", return_value=40):
            out = ms.share_reel("Reel Y", self.video, "pt", "ig1", s, sleep=lambda _: None)
        self.assertEqual(out, {"facebook": "fbst", "instagram": "igst", "errors": []})
        self.assertTrue(s.post.call_args_list[0].args[0].endswith("/123/video_stories"))
        self.assertEqual(s.post.call_args_list[3].kwargs["params"]["media_type"], "STORIES")

    def test_long_reel_gets_no_story(self):
        s = mock.Mock()
        with mock.patch.dict(os.environ, {"STORIES_LIVE": "1"}), mock.patch.object(ms, "video_seconds", return_value=75):
            out = ms.share_reel("Reel B", self.video, "pt", "ig1", s)
        s.post.assert_not_called()
        self.assertEqual(out["skipped"], "75s")
        self.assertEqual(out["errors"], [])

    def test_story_failure_never_breaks_the_reel(self):
        s = mock.Mock()
        s.get.side_effect = [resp({"access_token": "pt", "instagram_business_account": {"id": "ig1"}}),
                             resp({"status_code": "FINISHED"})]
        s.post.side_effect = [resp({"video_id": "v1"}), resp({"success": True}), resp({"success": True}),
                              resp({"id": "c1"}), resp({"success": True}), resp({"id": "m1"})]
        with mock.patch.object(ms, "share_reel", side_effect=RuntimeError("boom")):
            out = mp.publish_all(str(self.video), "cap", s, sleep=lambda _: None)
        self.assertEqual((out["facebook"], out["instagram"]), ("v1", "m1"))
        self.assertIn("Story: boom", out["errors"])

    def test_story_picture_renders_9_16(self):
        try:
            from playwright.sync_api import sync_playwright  # noqa: F401
        except ImportError:
            self.skipTest("playwright not installed")
        from posts.render import render
        post = {"id": "t-story", "slides": [{"kind": "hook", "label": "योजना की बात", "big": "पीएम किसान", "sub": "21वीं किस्त"},
                                            {"kind": "cta", "big": "देखें", "url": "taazabhav.com"}]}
        try:
            slides = render(post, Path(self.tmp))
            out = ms.story_image(slides[0], Path(self.tmp) / "story.png")
        except Exception as e:  # no chromium on this machine
            self.skipTest(f"chromium not available: {e}")
        from PIL import Image
        self.assertEqual(Image.open(out).size, (1080, 1920))


class BhavExtraDayTest(unittest.TestCase):
    """bhav is off Meta (META_ON) but goes out Thu/Fri/Sat: 14 + 3 = 17 posts a week."""

    def run_main(self, day, env):
        fake_now = datetime(day.year, day.month, day.day, 14, 30, tzinfo=bhav.IST)
        dt = mock.Mock(wraps=datetime); dt.now.return_value = fake_now
        with mock.patch.object(sys, "argv", ["bhav"]), \
                mock.patch.dict(os.environ, {"BHAV_POSTS_LIVE": "1", "META_ON": "", **env}), \
                mock.patch.object(bhav, "datetime", dt), \
                mock.patch.object(bhav, "load_state", return_value={"history": [], "preview": []}), \
                mock.patch("engine.feed.load_feed", return_value={"reports": []}) as feed, \
                mock.patch.object(bhav, "build", return_value=None):
            rc = bhav.main()
        return rc, feed.called

    def test_monday_stays_off(self):
        rc, fed = self.run_main(date(2026, 11, 16), {})
        self.assertEqual(rc, 0)
        self.assertFalse(fed)

    def test_thursday_runs(self):
        for d in (date(2026, 11, 12), date(2026, 11, 13), date(2026, 11, 14)):
            rc, fed = self.run_main(d, {})
            self.assertEqual(rc, 0)
            self.assertTrue(fed, d)

    def test_thursday_preview_until_live(self):
        posted = []
        with mock.patch.object(bhav, "publish", side_effect=lambda *a: posted.append(a)), \
                mock.patch.object(bhav, "send_preview") as prev, \
                mock.patch("posts.render.render", return_value=["x.png"]), \
                mock.patch.object(bhav, "save_state"), \
                mock.patch("posts.ledger.problems", return_value=[]), \
                mock.patch.object(bhav, "build", return_value={"id": "bhav-x", "lead": "गेहूं", "slides": [], "caption": "c", "crops": []}):
            fake_now = datetime(2026, 11, 12, 14, 30, tzinfo=bhav.IST)
            dt = mock.Mock(wraps=datetime); dt.now.return_value = fake_now
            with mock.patch.object(sys, "argv", ["bhav"]), \
                    mock.patch.dict(os.environ, {"BHAV_POSTS_LIVE": "1", "META_ON": "", "BHAV_EXTRA_LIVE": ""}), \
                    mock.patch.object(bhav, "datetime", dt), \
                    mock.patch.object(bhav, "load_state", return_value={"history": [], "preview": []}), \
                    mock.patch("engine.feed.load_feed", return_value={}):
                self.assertEqual(bhav.main(), 0)
        prev.assert_called_once()
        self.assertEqual(posted, [])

    def test_extra_days_make_17(self):
        self.assertEqual(len(bhav.EXTRA_DAYS), 3)
        from posts import yojana_post
        self.assertFalse(set(bhav.EXTRA_DAYS) & set(yojana_post.BHAV_KIND))


if __name__ == "__main__":
    unittest.main()
