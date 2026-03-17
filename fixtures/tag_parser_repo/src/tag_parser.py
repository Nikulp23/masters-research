from __future__ import annotations


def parse_tags(raw: str | None) -> list[str]:
    if raw is None:
        return []
    return [part for part in raw.split(",") if part]
