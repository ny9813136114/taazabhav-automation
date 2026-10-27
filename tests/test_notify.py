import io
import os
import unittest
from contextlib import redirect_stdout
from unittest import mock

import notify


class AnnotateTest(unittest.TestCase):
    def _out(self, env, msg):
        buf = io.StringIO()
        with mock.patch.dict(os.environ, env, clear=True), redirect_stdout(buf):
            notify.send_telegram_alert(msg)
        return buf.getvalue()

    def test_actions_alert_becomes_error_annotation(self):
        out = self._out({"GITHUB_ACTIONS": "true"}, "shaam (x):\nfacebook: 100% fail")
        self.assertIn("::error::shaam (x):%0Afacebook: 100%25 fail\n", out)

    def test_no_annotation_outside_actions(self):
        self.assertNotIn("::error::", self._out({}, "boom"))


if __name__ == "__main__":
    unittest.main()
