from __future__ import annotations

from unittest.mock import patch

from present.input import read_key


def _mock_os_read(data: bytes):
    """Yield the given bytes one at a time, like os.read(fd, 1) calls."""
    pos = 0

    def fake_read(fd: int, n: int) -> bytes:
        nonlocal pos
        chunk = data[pos : pos + n]
        pos += n
        return chunk

    return fake_read


class _FakeStdin:
    def fileno(self) -> int:
        return 0


def _patches(data: bytes, more_pending: bool):
    """Stack of patches needed to drive read_key with fake input."""
    return [
        patch("present.input.sys.stdin", _FakeStdin()),
        patch("present.input.os.read", side_effect=_mock_os_read(data)),
        patch("present.input.termios.tcgetattr", return_value=[]),
        patch("present.input.termios.tcsetattr"),
        patch("present.input.tty.setraw"),
        patch(
            "present.input.select.select",
            return_value=([0], [], []) if more_pending else ([], [], []),
        ),
    ]


def _run_with(data: bytes, more_pending: bool = True) -> str:
    ctxs = _patches(data, more_pending)
    for c in ctxs:
        c.start()
    try:
        return read_key()
    finally:
        for c in reversed(ctxs):
            c.stop()


class TestReadKey:
    def test_right_arrow_xterm(self) -> None:
        assert _run_with(b"\x1b[C") == "right"

    def test_left_arrow_xterm(self) -> None:
        assert _run_with(b"\x1b[D") == "left"

    def test_right_arrow_application_cursor_mode(self) -> None:
        # DECCKM mode sends ESC O C instead of ESC [ C.
        assert _run_with(b"\x1bOC") == "right"

    def test_left_arrow_application_cursor_mode(self) -> None:
        assert _run_with(b"\x1bOD") == "left"

    def test_q_key(self) -> None:
        assert _run_with(b"q", more_pending=False) == "q"

    def test_unknown_key(self) -> None:
        assert _run_with(b"x", more_pending=False) == "unknown"

    def test_lone_escape(self) -> None:
        assert _run_with(b"\x1b", more_pending=False) == "escape"
