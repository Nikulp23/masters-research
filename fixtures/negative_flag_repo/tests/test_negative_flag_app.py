from __future__ import annotations

import unittest

from src.negative_flag_app import resolve_negative_flag


class NegativeFlagTests(unittest.TestCase):
    def test_omitted_negative_flag_keeps_true_default(self) -> None:
        self.assertTrue(resolve_negative_flag(True, None))

    def test_explicit_negative_flag_sets_false(self) -> None:
        self.assertFalse(resolve_negative_flag(True, False))


if __name__ == "__main__":
    unittest.main()
