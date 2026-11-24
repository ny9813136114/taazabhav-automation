import unittest

from brand import BRAND_LINE, add_brand_line


class BrandLineTest(unittest.TestCase):
    def test_above_hashtags(self):
        out = add_brand_line("भाव आज\n\n#kisan #taazabhav")
        self.assertEqual(out, f"भाव आज\n\n{BRAND_LINE}\n#kisan #taazabhav")

    def test_appended_without_hashtags(self):
        self.assertEqual(add_brand_line("भाव आज"), f"भाव आज\n\n{BRAND_LINE}")

    def test_idempotent(self):
        once = add_brand_line("x\n#a")
        self.assertEqual(add_brand_line(once), once)

    def test_never_exceeds_limit(self):
        long = "क" * 2190
        self.assertEqual(add_brand_line(long), long)
        self.assertLessEqual(len(add_brand_line("क" * 2150)), 2200)

    def test_empty(self):
        self.assertEqual(add_brand_line(""), BRAND_LINE)
        self.assertEqual(add_brand_line(None), BRAND_LINE)


if __name__ == "__main__":
    unittest.main()
