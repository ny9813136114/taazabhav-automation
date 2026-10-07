# -*- coding: utf-8 -*-
import os, tempfile, unittest
from unittest import mock
import meta_publish as mp


def resp(body, code=200):
    r = mock.Mock(); r.status_code = code; r.json.return_value = body; r.text = str(body); return r


class MetaTest(unittest.TestCase):
    def setUp(self):
        self.env = mock.patch.dict(os.environ, {"META_TOKEN": "sys", "FB_PAGE_ID": "123"}); self.env.start()
        f = tempfile.NamedTemporaryFile(suffix=".mp4", delete=False); f.write(b"x" * 10); f.close(); self.video = f.name

    def tearDown(self):
        self.env.stop(); os.unlink(self.video)

    def test_happy_path_posts_both(self):
        s = mock.Mock()
        s.get.side_effect = [resp({"access_token": "pt", "instagram_business_account": {"id": "ig1"}}),
                             resp({"status_code": "IN_PROGRESS"}), resp({"status_code": "FINISHED"})]
        s.post.side_effect = [resp({"video_id": "v1", "upload_url": "https://up/v1"}), resp({"success": True}),
                              resp({"success": True}),
                              resp({"id": "c1", "uri": "https://up/c1"}), resp({"success": True}), resp({"id": "m1"})]
        out = mp.publish_all(self.video, "cap", s, sleep=lambda _: None)
        self.assertEqual(out, {"facebook": "v1", "instagram": "m1", "errors": []})
        up = s.post.call_args_list[1]
        self.assertEqual(up.kwargs["headers"]["Authorization"], "OAuth pt")
        self.assertEqual(up.kwargs["headers"]["file_size"], "10")

    def test_facebook_error_does_not_stop_instagram(self):
        s = mock.Mock()
        s.get.side_effect = [resp({"access_token": "pt", "instagram_business_account": {"id": "ig1"}}),
                             resp({"status_code": "FINISHED"})]
        s.post.side_effect = [resp({"error": {"message": "no perm"}}, 400),
                              resp({"id": "c1"}), resp({"success": True}), resp({"id": "m1"})]
        out = mp.publish_all(self.video, "cap", s, sleep=lambda _: None)
        self.assertIsNone(out["facebook"]); self.assertEqual(out["instagram"], "m1")
        self.assertIn("no perm", out["errors"][0])

    def test_no_instagram_linked(self):
        s = mock.Mock()
        s.get.side_effect = [resp({"access_token": "pt"})]
        s.post.side_effect = [resp({"video_id": "v1"}), resp({"success": True}), resp({"success": True})]
        out = mp.publish_all(self.video, "cap", s)
        self.assertEqual(out["facebook"], "v1"); self.assertIn("no Instagram", out["errors"][0])

    def test_ig_error_status(self):
        s = mock.Mock()
        s.get.side_effect = [resp({"status_code": "ERROR"})]
        s.post.side_effect = [resp({"id": "c1"}), resp({"success": True})]
        with self.assertRaises(mp.MetaError):
            mp.post_instagram_reel(self.video, "c", "ig1", "pt", s, sleep=lambda _: None)

    def test_caption(self):
        c = mp.build_caption("प्याज ₹17 किलो! सबसे सस्ता · Konch मंडी | Onion Rate Today Uttar Pradesh #Shorts",
                             "25 सितंबर: fact line\nलिंक", "Onion", "Uttar Pradesh")
        self.assertTrue(c.startswith("प्याज ₹17 किलो! सबसे सस्ता · Konch मंडी\n\n25 सितंबर: fact line"))
        self.assertIn("#onionratetoday", c); self.assertLessEqual(len(c), 2200)

    def test_caption_leads_with_search_phrase(self):
        c = mp.build_caption("प्याज का भाव आज 8 अक्टूबर 2026 | Neemuch मंडी | ₹24 किलो सबसे सस्ता #Shorts",
                             "प्याज का भाव आज 8 अक्टूबर 2026 | Neemuch मंडी\nfact line\nलिंक",
                             "Onion", "Madhya Pradesh")
        self.assertTrue(c.startswith("प्याज का भाव आज 8 अक्टूबर 2026 | Neemuch मंडी\n\nfact line\n\n"))
        self.assertIn("taazabhav.com/hi/mandi-bhav/onion/madhya-pradesh (लिंक बायो में)", c)

    def test_disabled_without_secrets(self):
        with mock.patch.dict(os.environ, {"META_TOKEN": ""}):
            self.assertFalse(mp.enabled())


if __name__ == "__main__":
    unittest.main()
