# -*- coding: utf-8 -*-
import json
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path
from unittest import mock

from posts import ledger as L
from posts import pillar

CAL = json.loads(Path("content/calendar/2026-11.json").read_text(encoding="utf-8"))
FEED = json.loads(Path("tests/fixtures/pillar_feed.json").read_text(encoding="utf-8"))
FEED_DAY = date(2026, 10, 21)
ROTATION = {6: "P2", 0: "P8", 1: "P3", 2: "P6", 3: "P5", 4: "P4", 5: "P1"}  # date.weekday() -> pillar


def check_post(t, p):
    t.assertLessEqual(len(p["caption"]), 2200, p["id"])
    t.assertTrue(2 <= len(p["slides"]) <= 10, p["id"])
    t.assertEqual(p["slides"][-1]["kind"], "cta", p["id"])
    t.assertIn("जाँच", p["trust"], p["id"])
    t.assertNotIn("utm_", json.dumps(p, ensure_ascii=False), p["id"])
    t.assertTrue(p["ask"].strip(), p["id"])
    t.assertIn("taazabhav.com/", p["link"])
    from posts.render import _slide
    for i, s in enumerate(p["slides"], 1):
        _slide(s, i, len(p["slides"]), p["trust"])  # every slide kind renders


class CalendarTest(unittest.TestCase):
    def test_every_day_of_november_in_weekday_rotation(self):
        days = CAL["days"]
        self.assertEqual([d["date"] for d in days], [(date(2026, 11, 1) + timedelta(days=i)).isoformat() for i in range(30)])
        for d in days:
            self.assertEqual(d["pillar"], ROTATION[date.fromisoformat(d["date"]).weekday()], d["date"])
            self.assertTrue(d.get("post") or d.get("dynamic"), d["date"])

    def test_static_posts_fit_meta_and_carry_a_source(self):
        for d in CAL["days"]:
            if d.get("post"):
                check_post(self, d["post"])

    def test_whole_month_passes_the_no_repeat_ledger(self):
        led = []
        for d in CAL["days"]:
            p = d.get("post")
            if not p:
                continue
            day = date.fromisoformat(d["date"])
            e = pillar.entry_for(day, d["pillar"], p["id"], p["meta"], p["caption"])
            self.assertEqual(L.problems(e, led, day), [], d["date"])
            led.append(e)

    def test_thursday_answers_wednesdays_challenge(self):
        days = {d["date"]: d for d in CAL["days"]}
        for d in CAL["days"]:
            if d["pillar"] == "P6":
                thu = days.get((date.fromisoformat(d["date"]) + timedelta(days=1)).isoformat())
                if thu:
                    self.assertTrue(any(s["kind"] == "answer" and "कल का चैलेंज" in s["label"] for s in thu["post"]["slides"]), thu["date"])

    def test_known_numbers_from_site_code(self):
        text = json.dumps(CAL, ensure_ascii=False)
        self.assertIn("₹266.50", text)      # urea bag
        self.assertIn("₹97,640", text)      # 40 qtl paddy at MSP 2,441
        self.assertIn("1.38 एकड़", text)    # 5 MP bigha
        self.assertIn("₹1,22,050", text)    # 50 qtl paddy

    def test_hold_maths_matches_site(self):
        # lib/hold-or-sell.ts for the same inputs (checked with tsx, 21 Oct 2026)
        r = pillar.hold_or_sell(20, 6775, 2, 10, 12, 1)
        self.assertEqual((r["sellNow"], r["storageCost"], r["interestCost"], r["breakEven"], r["risePerMonth"], r["costIfFlat"]),
                         (135500, 400, 2710, 7001, 113, 4465))


class DynamicTest(unittest.TestCase):
    def test_p1_main_crop_of_the_state(self):
        p = pillar.build_p1(FEED, FEED_DAY, {"state": "madhya-pradesh"}, [])
        check_post(self, p)
        self.assertEqual((p["meta"]["crop"], p["meta"]["state"]), ("soybean", "madhya-pradesh"))
        self.assertIn("₹6,500 से ₹7,300", p["slides"][0]["big"])

    def test_p1_skips_crop_the_ledger_used_and_falls_to_next_state_without_report(self):
        used = [pillar.entry_for(FEED_DAY - timedelta(days=1), "P1", "x", {"crop": "soybean", "state": "madhya-pradesh",
                                                                           "angle": f"spread-{FEED_DAY.isoformat()}"}, "a")]
        self.assertNotEqual(pillar.build_p1(FEED, FEED_DAY, {"state": "madhya-pradesh"}, used)["meta"]["crop"], "soybean")
        self.assertEqual(pillar.build_p1(FEED, FEED_DAY, {"state": "karnataka"}, [])["meta"]["state"], "madhya-pradesh")

    def test_p3_hold_uses_todays_state_price(self):
        p = pillar.build_p3_hold(FEED, FEED_DAY, {"crop": "soybean", "state": "madhya-pradesh", "qtl": 20}, CAL)
        check_post(self, p)
        self.assertIn("₹4,465", p["slides"][0]["big"])
        self.assertNotIn("भावांतर", p["caption"])  # 21 Oct: Bhavantar sale opens 22 Oct
        cal = json.loads(json.dumps(CAL)); cal["site"]["bhavantar"]["saleStart"] = "2026-10-21"
        self.assertIn("भावांतर", pillar.build_p3_hold(FEED, FEED_DAY, {"crop": "soybean", "state": "madhya-pradesh", "qtl": 20}, cal)["caption"])

    def test_p4_leads_with_a_stored_crop_and_says_no_advice(self):
        p = pillar.build_p4(FEED, FEED_DAY)
        check_post(self, p)
        self.assertIn("मक्का", p["slides"][0]["big"])
        self.assertIn("यह सलाह नहीं", p["caption"])

    def test_no_prices_today_means_no_dynamic_post(self):
        later = FEED_DAY + timedelta(days=1)
        self.assertIsNone(pillar.build_p1(FEED, later, {"state": "madhya-pradesh"}, []))
        self.assertIsNone(pillar.build_p4(FEED, later))
        self.assertIsNone(pillar.build_p3_hold(FEED, later, {"crop": "soybean", "state": "madhya-pradesh", "qtl": 20}, CAL))


class FrostTest(unittest.TestCase):
    def wx(self, tmin, code=0, gust=5, day="2026-12-20"):
        r = mock.Mock(); r.status_code = 200
        r.json.return_value = {"forecast": [{"date": day, "tmin": tmin, "code": code, "gust": gust, "tmax": 20, "rh": 80, "rain": 0}]}
        s = mock.Mock(); s.get.return_value = r
        return s

    def test_night_risk_same_as_site(self):
        self.assertEqual(pillar.night_risk({"tmin": -1}, 4, 2), "frost")
        self.assertEqual(pillar.night_risk({"tmin": 1.5}, 4, 2), "high")
        self.assertEqual(pillar.night_risk({"tmin": 3.5, "code": 0, "gust": 5}, 4, 2), "high")
        self.assertEqual(pillar.night_risk({"tmin": 3.5, "code": 3, "gust": 5}, 4, 2), "watch")
        self.assertEqual(pillar.night_risk({"tmin": 8}, 4, 2), "none")

    def test_frost_takes_over_the_slot(self):
        day = date(2026, 12, 20)
        hits = pillar.frost_hits(day, CAL, self.wx(1.0))
        self.assertEqual(len(hits), len(pillar.HUBS))
        pil, p = pillar.build(day, CAL, CAL["days"][0], lambda: FEED, weather=lambda d, c: hits)
        self.assertEqual(pil, "P7")
        check_post(self, p)
        self.assertIn("1°C", p["slides"][0]["big"])
        self.assertFalse(pillar.frost_hits(day, CAL, self.wx(9.0)))

    def test_weather_failure_does_not_stop_the_post(self):
        def boom(d, c):
            raise RuntimeError("down")
        plan = next(d for d in CAL["days"] if d.get("post"))
        self.assertEqual(pillar.build(date.fromisoformat(plan["date"]), CAL, plan, lambda: FEED, weather=boom)[1]["id"], plan["post"]["id"])


class RunTest(unittest.TestCase):
    def run_main(self, argv, env, plan_day="2026-11-05"):
        sent, legacy, published = [], [], []
        with tempfile.TemporaryDirectory() as d, \
                mock.patch.object(pillar, "STATE", Path(d) / "pillar.json"), \
                mock.patch.object(L, "DIR", Path(d) / "ledger"), \
                mock.patch.dict("os.environ", env, clear=False), \
                mock.patch("sys.argv", ["x"] + argv + [plan_day]), \
                mock.patch.object(pillar, "frost_hits", return_value=[]), \
                mock.patch("posts.render.render", return_value=["a.png", "b.png"]), \
                mock.patch.object(pillar, "send_preview", side_effect=lambda p, s: sent.append(p["id"])), \
                mock.patch.object(pillar, "publish", side_effect=lambda p, s: published.append(p["id"]) or {"facebook": "f", "instagram": "i", "errors": []}), \
                mock.patch.object(pillar, "share_kit"), mock.patch.object(pillar, "alert"), \
                mock.patch.object(pillar, "legacy", side_effect=lambda why, m: legacy.append((why, m)) or 0):
            rc = pillar.main()
            led = L.load(Path(d) / "ledger")
        return rc, sent, legacy, published, led

    def test_preview_sends_pillar_and_keeps_old_carousel(self):
        rc, sent, legacy, published, led = self.run_main(["preview"], {})
        self.assertEqual((rc, sent, published, led), (0, ["p5-urea-300"], [], []))
        self.assertEqual(legacy, [("preview mode", "preview")])

    def test_publish_posts_pillar_and_records_it(self):
        rc, sent, legacy, published, led = self.run_main(["publish"], {})
        self.assertEqual((rc, sent, legacy, published), (0, [], [], ["p5-urea-300"]))
        self.assertEqual((led[0]["pillar"], led[0]["claim"]), ("P5", "urea-300|2026-04-27"))

    def test_blocked_post_falls_back_to_carousel(self):
        with mock.patch.object(L, "problems", return_value=["hook already used: x"]):
            rc, sent, legacy, published, led = self.run_main(["publish"], {})
        self.assertEqual((sent, published), ([], []))
        self.assertEqual(legacy, [("hook already used: x", "publish")])

    def test_no_calendar_month_falls_back(self):
        rc, sent, legacy, published, led = self.run_main(["publish"], {}, plan_day="2031-01-01")
        self.assertEqual(legacy[0][0], "no calendar day")


if __name__ == "__main__":
    unittest.main()
