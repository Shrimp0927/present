from __future__ import annotations

import os
import select
import sys
import termios
import tty

ARROW_KEYS = {
    "A": "up",
    "B": "down",
    "C": "right",
    "D": "left",
}


def read_key() -> str:
    """Read a single keypress in raw mode and return a key name.

    Uses os.read() on the fd directly because sys.stdin is a buffered
    TextIOWrapper — its read(1) can stall waiting for the buffer to fill
    even when the terminal is in raw mode.
    """
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        b = os.read(fd, 1)

        if b == b"\x1b":
            # Arrow key escape sequence: ESC [ X (xterm) or ESC O X (DECCKM).
            if select.select([fd], [], [], 0.1)[0]:
                b2 = os.read(fd, 1)
                if b2 in (b"[", b"O"):
                    b3 = os.read(fd, 1)
                    return ARROW_KEYS.get(b3.decode("ascii", "replace"), "unknown")
            return "escape"

        if b == b"q":
            return "q"

        return "unknown"
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
