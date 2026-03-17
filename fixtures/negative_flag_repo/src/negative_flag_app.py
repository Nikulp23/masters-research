from __future__ import annotations


def resolve_negative_flag(default: bool, flag_value: bool | None) -> bool:
    if default is True:
        return False if flag_value is None else flag_value
    if flag_value is None:
        return default
    return flag_value
