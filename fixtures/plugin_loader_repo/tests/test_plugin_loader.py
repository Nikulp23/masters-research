from __future__ import annotations

import unittest

from src.plugin_loader import kernel_function, load_plugin


class EmptyPlugin:
    def helper(self) -> str:
        return "noop"


class ValidPlugin:
    @kernel_function
    def run(self) -> str:
        return "ok"


class PluginLoaderTests(unittest.TestCase):
    def test_skips_classes_without_kernel_function_methods(self) -> None:
        plugin = load_plugin([EmptyPlugin, ValidPlugin])
        self.assertIsInstance(plugin, ValidPlugin)


if __name__ == "__main__":
    unittest.main()
