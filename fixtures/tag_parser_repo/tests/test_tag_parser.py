from __future__ import annotations

import unittest

from src.tag_parser import parse_tags


class TagParserTests(unittest.TestCase):
    def test_none_returns_empty_list(self) -> None:
        self.assertEqual(parse_tags(None), [])

    def test_parser_strips_whitespace_and_ignores_empty_values(self) -> None:
        self.assertEqual(parse_tags(" build, test , ,deploy ,  "), ["build", "test", "deploy"])


if __name__ == "__main__":
    unittest.main()
