from __future__ import annotations

from typing import Any


def kernel_function(func: Any) -> Any:
    func.__kernel_function__ = True
    return func


def _has_kernel_function(cls: type[Any]) -> bool:
    for name in dir(cls):
        value = getattr(cls, name)
        if getattr(value, "__kernel_function__", False):
            return True
    return False


def load_plugin(plugin_classes: list[type[Any]]) -> object:
    for cls in plugin_classes:
        return cls()
    raise ValueError("No plugin classes found")
