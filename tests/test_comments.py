# -*- coding: utf-8 -*-
"""PR 3: link in the Page's first comment + shaam ka sawal."""
import os
import tempfile
import unittest
from datetime import date
from unittest import mock

import meta_publish as mp
from posts import bhav, run, shaam
from posts.render import _slide


def resp(body, code=200):
    r = mock.Mock(); r.status_code = code; r.json.return_value = body; r.text = str(body); return r


TOOL_CAP = ("2 एकड़ गेहूं में कितनी खाद लगेगी?\n• यूरिया: 4 बोरी\n\n"
            "पूरा हिसाब अपने आंकड़ों से: taazabhav.com/khad-calculator?utm_source=fb (लिंक बायो में)\n"
            "काम का लगे तो शेयर करें।\n\n#किसान #taazabhav")
REEL_CAP = ("सोयाबीन ₹4,800\n\nसोयाबीन का आज का भाव, 900+ मंडियाँ: https://taazabhav.com/hi/soybean\n"
            "रोज़ सुबह 7:30 बजे भाव धमाका · Telegram: https://t.me/taazabhav\n#mandibhav")


class FbCaptionTest(unittest.TestCase):
    def test_links_leave_and_one_marker_before_tags(self):
        out = mp.fb_caption(TOOL_CAP)
        self.assertNotIn("taazabhav.com/", out)
        self.assertNotIn("बायो", out)
        self.assertEqual(out.count(mp.COMMENT_MARK), 1)
        self.assertLess(out.index(mp.COMMENT_MARK), out.index("#किसान"))
        self.assertIn("काम का लगे तो शेयर करें।", out)

    def test_reel_caption_keeps_text_drops_link_labels(self):
        out = mp.fb_caption(REEL_CAP)
        self.assertNotIn("http", out)
        self.assertNotIn("t.me", out)
        self.assertIn("रोज़ सुबह 7:30 बजे भाव धमाका", out)
        self.assertNotIn("900+ मंडियाँ", out)

    def test_no_link_no_change(self):
        self.assertEqual(mp.fb_caption("सिर्फ बात\n#x"), "सिर्फ बात\n#x")

    def test_default_comment_takes_site_link_https(self):
        self.assertEqual(mp.default_comment(mp.strip_utm(TOOL_CAP)),
                         "👉 पूरी जानकारी, मुफ़्त: https://taazabhav.com/khad-calculator")
        self.assertIsNone(mp.default_comment("no link"))


class ReelCommentTest(unittest.TestCase):
    def setUp(self):
        self.env = mock.patch.dict(os.environ, {"META_TOKEN": "sys", "FB_PAGE_ID": "123", "COMMENTS_LIVE": "1"}); self.env.start()
        f = tempfile.NamedTemporaryFile(suffix=".mp4", delete=False); f.write(b"x"); f.close(); self.video = f.name

    def tearDown(self):
        self.env.stop(); os.unlink(self.video)

    def _session(self, comment_resps):
        s = mock.Mock()
        s.get.side_effect = [resp({"access_token": "pt"})]
        s.post.side_effect = [resp({"video_id": "v1"}), resp({"success": True}), resp({"success": True})] + comment_resps
        return s

    def test_live_fb_caption_has_no_link_and_page_comments_it(self):
        s = self._session([resp({"id": "cm1"})])
        out = mp.publish_all(self.video, REEL_CAP, s, sleep=lambda _: None, comment="🔗 टूल: https://taazabhav.com/x?utm_medium=a")
        self.assertEqual(out["comment"], "cm1")
        desc = s.post.call_args_list[2].kwargs["params"]["description"]
        self.assertNotIn("http", desc)
        c = s.post.call_args_list[3]
        self.assertTrue(c.args[0].endswith("/v1/comments"))
        self.assertEqual(c.kwargs["data"]["message"], "🔗 टूल: https://taazabhav.com/x")

    def test_comment_fails_then_full_caption_restored(self):
        err = resp({"error": {"message": "(#200) pages_manage_engagement"}}, 403)
        s = self._session([err] * mp.COMMENT_TRIES + [resp({"success": True})])
        out = mp.publish_all(self.video, REEL_CAP, s, sleep=lambda _: None)
        self.assertIsNone(out["comment"])
        self.assertIn("caption put back", out["errors"][-1])
        restore = s.post.call_args_list[-1]
        self.assertTrue(restore.args[0].endswith("/v1"))
        self.assertIn("https://taazabhav.com/hi/soybean", restore.kwargs["data"]["description"])

    def test_off_keeps_caption_and_only_previews(self):
        with mock.patch.dict(os.environ, {"COMMENTS_LIVE": ""}), mock.patch.object(mp, "preview_comment") as pv:
            s = self._session([])
            out = mp.publish_all(self.video, REEL_CAP, s, sleep=lambda _: None)
        self.assertIn("https://taazabhav.com/hi/soybean", s.post.call_args_list[2].kwargs["params"]["description"])
        self.assertNotIn("comment", out)
        pv.assert_called_once()


class PhotoCommentTest(unittest.TestCase):
    def test_photo_post_live(self):
        post = {"id": "khad", "caption": TOOL_CAP, "link": "https://taazabhav.com/khad-calculator"}
        with mock.patch.dict(os.environ, {"META_TOKEN": "t", "FB_PAGE_ID": "1", "COMMENTS_LIVE": "1"}), \
                mock.patch.object(mp, "page_credentials", return_value=("pt", None)), \
                mock.patch.object(run, "post_facebook", return_value=("1_9", ["p1"])) as fb, \
                mock.patch.object(mp, "post_comment", return_value="cm") as pc:
            out = run.publish(post, ["a.png"])
        self.assertNotIn("taazabhav.com", fb.call_args.args[1])
        self.assertEqual(pc.call_args.args[:2], ("1_9", "👉 पूरा हिसाब, मुफ़्त टूल: https://taazabhav.com/khad-calculator"))
        self.assertEqual(out["comment"], "cm")

    def test_bhav_live_caption_asks_p1_question(self):
        post = {"id": "bhav-x", "caption": "आज के भाव\n\nभाव मंडी रिपोर्ट से हैं।", "caption_live": "आज के भाव\n\n💬 सवाल?\n\nभाव मंडी रिपोर्ट से हैं।",
                "link": "https://taazabhav.com", "link_label": "अपनी मंडी का आज का भाव"}
        with mock.patch.dict(os.environ, {"META_TOKEN": "t", "FB_PAGE_ID": "1", "COMMENTS_LIVE": "1"}), \
                mock.patch.object(mp, "page_credentials", return_value=("pt", "ig")), \
                mock.patch.object(run, "post_facebook", return_value=("1_9", ["p1"])) as fb, \
                mock.patch.object(run, "post_instagram", return_value="m1") as ig, \
                mock.patch.object(mp, "post_comment", return_value="cm"):
            run.publish(post, ["a.png"])
        self.assertIn("💬 सवाल?", fb.call_args.args[1])
        self.assertIn("💬 सवाल?", ig.call_args.args[1])

    def test_cta_slide_text(self):
        s = {"kind": "cta", "big": "b", "url": "taazabhav.com", "ask": ["आज भाव?", "कमेंट में लिखें"]}
        self.assertIn("लिंक बायो में", _slide(s, 1, 1))
        on = _slide(s, 1, 1, comment=True)
        self.assertIn("FB पर पहला कमेंट", on)
        self.assertIn("आज भाव?", on)


class ShaamTest(unittest.TestCase):
    LED = [{"date": "2026-10-27", "slot": "09:30", "format": "photo", "pillar": "P3", "id": "p3", "facebook": "1_a", "instagram": "ia"},
           {"date": "2026-10-27", "slot": "14:30", "format": "photo", "pillar": "bhav", "id": "bhav", "facebook": "1_b", "instagram": "ib"},
           {"date": "2026-10-27", "slot": "07:30", "format": "reel", "pillar": "A", "id": "r", "facebook": "v"}]

    def test_bhav_post_gets_price_question(self):
        day = date(2026, 10, 27)  # Tuesday
        post, slot = shaam.target(day, self.LED)
        self.assertEqual(post["id"], "bhav")
        q = shaam.question(day, "सोयाबीन", False)
        self.assertIn("सोयाबीन", q)
        self.assertNotIn("YES", q)

    def test_wednesday_challenge_goes_under_morning_post(self):
        led = [dict(x, date="2026-10-28") for x in self.LED]
        led[0]["pillar"] = "P6"
        day = date(2026, 10, 28)
        self.assertEqual(shaam.target(day, led)[0]["id"], "p3")
        self.assertTrue(shaam.challenge_today(day, led, {}))
        self.assertIn("चैलेंज", shaam.question(day, "सोयाबीन", True))

    def test_every_weekday_has_a_real_question(self):
        qs = {shaam.question(date(2026, 11, 2 + i), "धान", False) for i in range(7)}
        self.assertGreaterEqual(len(qs), 6)
        self.assertTrue(all(q.endswith(("?", "।")) for q in qs))

    def test_no_post_today(self):
        self.assertIsNone(shaam.target(date(2026, 10, 29), self.LED)[0])

    def test_lead_crop_from_bhav_state(self):
        st = {"history": [{"date": "2026-10-27", "id": "bhav", "lead": "धान"}]}
        self.assertEqual(shaam.lead_crop(date(2026, 10, 27), st), "धान")
        self.assertEqual(shaam.lead_crop(date(2026, 10, 28), st), shaam.DEFAULT_CROP)


class ShaamLateRun(unittest.TestCase):
    def test_late_run_after_midnight_uses_previous_day(self):
        from datetime import datetime
        self.assertEqual(shaam.scheduled_day(datetime(2026, 10, 27, 0, 59, tzinfo=run.IST)), date(2026, 10, 26))
        self.assertEqual(shaam.scheduled_day(datetime(2026, 10, 27, 19, 0, tzinfo=run.IST)), date(2026, 10, 27))


if __name__ == "__main__":
    unittest.main()
