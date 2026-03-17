from __future__ import annotations

ANSI_COLORS = {
    "green": "\033[32m",
    "red": "\033[31m",
}
ANSI_RESET = "\033[0m"


def color_enabled() -> bool:
    return True


def render_message(message: str, color: str = "green") -> str:
    if not color_enabled():
        return message
    prefix = ANSI_COLORS.get(color, "")
    if not prefix:
        return message
    return f"{prefix}{message}{ANSI_RESET}"
