# -*- coding: utf-8 -*-
import datetime as dt, json, unittest
from unittest import mock
import mela_video as mv

PAGE = '''<html><head><script type="application/ld+json">{"@context":"https://schema.org","@graph":[
{"@type":"BreadcrumbList","itemListElement":[]},
{"@type":"Event","name":"Pusa Krishi Vigyan Mela","startDate":"2026-10-12","endDate":"2026-10-14",
 "eventStatus":"https://schema.org/EventScheduled",
 "location":{"@type":"Place","name":"IARI Mela Ground","address":{"@type":"PostalAddress","addressLocality":"New Delhi","addressRegion":"Delhi"}}}]}
</script></head></html>'''
EXPECTED = '<html><script type="application/ld+json">{"@type":"BreadcrumbList"}</script></html>'
SITEMAP = b'''<?xml version="1.0"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
<url><loc>https://taazabhav.com/kisan-mela</loc></url>
<url><loc>https://taazabhav.com/kisan-mela/state/delhi</loc></url>
<url><loc>https://taazabhav.com/kisan-mela/pusa-krishi-vigyan-mela</loc></url>
<url><loc>https://taazabhav.com/kisan-mela/some-expected-expo</loc></url></urlset>'''


def r(text=None, content=None):
    m = mock.Mock(); m.text = text; m.content = content; m.raise_for_status = lambda: None; return m


class MelaTest(unittest.TestCase):
    def test_fetch_only_confirmed_event_pages(self):
        s = mock.Mock(); s.get.side_effect = [r(content=SITEMAP), r(text=PAGE), r(text=EXPECTED)]
        evs = mv.fetch_events(s)
        self.assertEqual(len(evs), 1)
        e = evs[0]
        self.assertEqual((e["slug"], e["start"], e["end"], e["city"]), ("pusa-krishi-vigyan-mela", dt.date(2026, 10, 12), dt.date(2026, 10, 14), "New Delhi"))

    def test_due_stages_and_dedupe(self):
        e = mv.parse_event(PAGE, "https://taazabhav.com/kisan-mela/pusa-krishi-vigyan-mela")
        self.assertEqual(mv.due([e], dt.date(2026, 10, 5), set())[0][2], "week")
        self.assertEqual(mv.due([e], dt.date(2026, 10, 11), set())[0][1], 1)
        self.assertEqual(mv.due([e], dt.date(2026, 10, 8), set()), [])
        self.assertEqual(mv.due([e], dt.date(2026, 10, 5), {"pusa-krishi-vigyan-mela:2026-10-12:week"}), [])

    def test_dates_and_place(self):
        self.assertEqual(mv.date_range_hi(dt.date(2026, 10, 12), dt.date(2026, 10, 14)), "12–14 अक्टूबर 2026")
        self.assertEqual(mv.date_range_hi(dt.date(2026, 10, 30), dt.date(2026, 11, 2)), "30 अक्टूबर – 2 नवंबर 2026")
        self.assertEqual(mv.place({"venue": "IARI Mela Ground, New Delhi", "city": "New Delhi", "state": "Delhi"}), "IARI Mela Ground, New Delhi")
        self.assertEqual(mv.place({"venue": "PAU Campus", "city": "Ludhiana", "state": "Punjab"}), "PAU Campus, Ludhiana, Punjab")

    def test_props_and_metadata(self):
        e = mv.parse_event(PAGE, "https://taazabhav.com/kisan-mela/pusa-krishi-vigyan-mela")
        p = mv.build_props(e, 1)
        self.assertEqual(p["countdown"], "कल से शुरू!"); self.assertTrue(p["urgent"])
        t, d, tags, c = mv.metadata(e, 7)
        self.assertLessEqual(len(t), 100); self.assertIn("7 दिन बाद", t); self.assertIn("#Shorts", t)
        self.assertNotIn("utm_", d)
        self.assertIn("पुष्टि", d)

    def test_cancelled_skipped(self):
        s = mock.Mock()
        s.get.side_effect = [r(content=SITEMAP), r(text=PAGE.replace("EventScheduled", "EventCancelled")), r(text=EXPECTED)]
        self.assertEqual(mv.fetch_events(s), [])


if __name__ == "__main__":
    unittest.main()
