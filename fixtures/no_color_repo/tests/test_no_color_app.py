from __future__ import annotations

import os
import unittest

from src.no_color_app import render_message


class NoColorTests(unittest.TestCase):
    def test_colors_render_when_no_env_var_is_set(self) -> None:
        os.environ.pop("NO_COLOR", None)
        rendered = render_message("hello")
        self.assertIn("\033[32m", rendered)

    def test_no_color_disables_ansi_codes(self) -> None:
        os.environ["NO_COLOR"] = "1"
        try:
            rendered = render_message("hello")
        finally:
            os.environ.pop("NO_COLOR", None)
        self.assertEqual(rendered, "hello")


if __name__ == "__main__":
    unittest.main()
