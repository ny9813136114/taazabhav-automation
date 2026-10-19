# -*- coding: utf-8 -*-
import json
import unittest
from datetime import date
from pathlib import Path
from unittest import mock

from posts import run

POSTS = json.loads(Path("content/tool_posts.json").read_text(encoding="utf-8"))["posts"]


class QueueTest(unittest.TestCase):
    def test_posts_fit_meta_limits(self):
        ids = set()
        for p in POSTS:
            self.assertNotIn(p["id"], ids)
            ids.add(p["id"])
            self.assertLessEqual(len(p["caption"]), 2200, p["id"])
            self.assertTrue(2 <= len(p["slides"]) <= 10, p["id"])
            self.assertEqual(p["slides"][-1]["kind"], "cta")
            self.assertIn("taazabhav.com/", p["group"])

    def test_known_fixed_prices(self):
        text = json.dumps(POSTS, ensure_ascii=False)
        self.assertIn("₹1,350", text)
        self.assertIn("₹266.50", text)
        self.assertIn("यूरिया ₹266.50", text)


class PickTest(unittest.TestCase):
    Q = [{"id": "a", "tool": "khad"}, {"id": "b", "tool": "bigha"}, {"id": "c", "tool": "msp"},
         {"id": "old", "tool": "bhavantar", "validUntil": "2026-01-01"}]

    def test_walks_queue_after_last(self):
        with mock.patch.object(run, "d_tool", return_value="none"):
            self.assertEqual(run.pick(self.Q, [{"id": "a"}], date(2026, 10, 20))["id"], "b")
            self.assertEqual(run.pick(self.Q, [{"id": "a"}, {"id": "b"}], date(2026, 10, 20))["id"], "c")

    def test_skips_expired_and_wraps(self):
        with mock.patch.object(run, "d_tool", return_value="none"):
            self.assertEqual(run.pick(self.Q, [{"id": "b"}, {"id": "c"}], date(2026, 10, 20))["id"], "a")

    def test_avoids_series_d_tool(self):
        with mock.patch.object(run, "d_tool", return_value="khad"):
            self.assertEqual(run.pick(self.Q, [], date(2026, 10, 20))["id"], "b")

    def test_d_tool_matches_engine_rotation(self):
        from engine.tools import TOOLS
        day = date(2026, 10, 21)
        self.assertEqual(run.d_tool(day), TOOLS[day.toordinal() % len(TOOLS)]["id"])


class Resp:
    def __init__(self, body):
        self.status_code, self._b, self.text = 200, body, json.dumps(body)

    def json(self):
        return self._b


class MetaTest(unittest.TestCase):
    def test_facebook_then_instagram(self):
        calls = []

        class S:
            def post(self, url, data=None, files=None, timeout=None, params=None):
                calls.append(("POST", url.rsplit("/", 2)[-1], dict(data or {})))
                if url.endswith("/photos"):
                    return Resp({"id": f"ph{len(calls)}"})
                if url.endswith("/feed"):
                    return Resp({"id": "page_post"})
                if url.endswith("/media"):
                    return Resp({"id": "box" if data.get("media_type") == "CAROUSEL" else f"it{len(calls)}"})
                return Resp({"id": "ig_post"})

            def get(self, url, params=None, timeout=None):
                if params.get("fields") == "images":
                    return Resp({"images": [{"width": 720, "source": "https://cdn/s.jpg"}, {"width": 1080, "source": "https://cdn/b.jpg"}]})
                return Resp({"status_code": "FINISHED"})

        import tempfile
        with tempfile.TemporaryDirectory() as d, mock.patch.dict("os.environ", {"FB_PAGE_ID": "1"}):
            slides = []
            for i in range(2):
                p = Path(d) / f"{i}.png"
                p.write_bytes(b"x")
                slides.append(p)
            fb, photos = run.post_facebook(slides, "cap", "tok", S())
            ig = run.post_instagram(photos, "cap", "9", "tok", S(), sleep=lambda s: None)
        self.assertEqual(fb, "page_post")
        self.assertEqual(ig, "ig_post")
        feed = [c for c in calls if c[1] == "feed"][0][2]
        self.assertIn("attached_media[1]", feed)
        items = [c[2] for c in calls if c[1] == "media" and c[2].get("is_carousel_item")]
        self.assertEqual(items[0]["image_url"], "https://cdn/b.jpg")


if __name__ == "__main__":
    unittest.main()
