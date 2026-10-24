# -*- coding: utf-8 -*-
import unittest
from datetime import date

from posts import group_kit


def row(t, hook, link):
    return {"time": f"2026-10-24T{t}:00+05:30", "hook": hook, "link": link}


class GroupKitTest(unittest.TestCase):
    def test_empty_day_sends_nothing(self):
        self.assertIsNone(group_kit.message(date(2026, 10, 24), []))

    def test_lists_posts_in_time_order_with_type(self):
        text = group_kit.message(date(2026, 10, 24), [
            row("14:30", "आज के मंडी भाव", "https://www.facebook.com/1/posts/2"),
            row("07:30", "भाव धमाका", "https://www.facebook.com/reel/3"),
        ])
        self.assertIn("2 पोस्ट", text)
        self.assertLess(text.index("reel/3"), text.index("posts/2"))
        self.assertIn("1. 🎬 07:30", text)
        self.assertIn("2. 🖼 14:30", text)
        self.assertNotIn("utm_", text)

    def test_stays_under_telegram_limit(self):
        rows = [row("09:%02d" % (i % 60), "क" * 200, f"https://www.facebook.com/reel/{i}") for i in range(80)]
        text = group_kit.message(date(2026, 10, 24), rows)
        self.assertLessEqual(len(text), 4096)
        self.assertIn("बाकी पोस्ट", text)


if __name__ == "__main__":
    unittest.main()
