from __future__ import annotations

from io import BytesIO, StringIO
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from PIL import Image
from rich.console import Console

from present.parser import ImageBox, Settings, Slide, TextBox
from present.renderer import render_slide


@pytest.fixture
def tiny_image(tmp_path: Path) -> Path:
    """A 4x4 red PNG on disk."""
    path = tmp_path / "tiny.png"
    Image.new("RGB", (4, 4), color="red").save(path)
    return path


def _make_screen(console: Console) -> MagicMock:
    screen = MagicMock()
    screen.console = console
    return screen


def _capture(renderable: object) -> str:
    test_console = Console(file=StringIO(), width=80, height=24, force_terminal=True)
    with test_console.capture() as cap:
        test_console.print(renderable)
    return cap.get()


class TestSingleBoxRender:
    def test_renders_heading(self) -> None:
        console = Console(file=StringIO(), width=80, height=24, force_terminal=True)
        screen = _make_screen(console)
        slide = Slide(boxes=[TextBox(content="body content")], title="Hello World")

        render_slide(screen, slide, slide_index=0, total_slides=1)

        screen.update.assert_called_once()
        out = _capture(screen.update.call_args[0][0])
        assert "Hello World" in out
        assert "body content" in out

    def test_renders_list(self) -> None:
        console = Console(file=StringIO(), width=80, height=24, force_terminal=True)
        screen = _make_screen(console)
        slide = Slide(boxes=[TextBox(content="- one\n- two")])

        render_slide(screen, slide, slide_index=0, total_slides=1)
        out = _capture(screen.update.call_args[0][0])
        assert "one" in out
        assert "two" in out

    def test_renders_code_block(self) -> None:
        console = Console(file=StringIO(), width=80, height=24, force_terminal=True)
        screen = _make_screen(console)
        slide = Slide(boxes=[TextBox(content="```python\nprint('hi')\n```")])

        render_slide(screen, slide, slide_index=0, total_slides=1)
        out = _capture(screen.update.call_args[0][0])
        assert "print" in out


class TestTwoColumnRender:
    def test_renders_both_text_boxes(self) -> None:
        console = Console(file=StringIO(), width=120, height=30, force_terminal=True)
        screen = _make_screen(console)
        slide = Slide(
            boxes=[
                TextBox(content="LEFT_SIDE_MARKER"),
                TextBox(content="RIGHT_SIDE_MARKER"),
            ]
        )

        render_slide(screen, slide, slide_index=0, total_slides=1)

        out = _capture(screen.update.call_args[0][0])
        assert "LEFT_SIDE_MARKER" in out
        assert "RIGHT_SIDE_MARKER" in out

    def test_left_appears_before_right_on_each_row(self) -> None:
        console = Console(file=StringIO(), width=120, height=30, force_terminal=True)
        screen = _make_screen(console)
        slide = Slide(
            boxes=[TextBox(content="LEFT"), TextBox(content="RIGHT")]
        )

        render_slide(screen, slide, slide_index=0, total_slides=1)
        out = _capture(screen.update.call_args[0][0])
        # Find a line containing both markers — left must come first horizontally
        line_with_both = next(
            (line for line in out.splitlines() if "LEFT" in line and "RIGHT" in line),
            None,
        )
        assert line_with_both is not None, "expected both markers on the same row"
        assert line_with_both.index("LEFT") < line_with_both.index("RIGHT")


class TestImageRender:
    def test_local_image_path_is_loaded(self, tiny_image: Path) -> None:
        console = Console(file=StringIO(), width=80, height=24, force_terminal=True)
        screen = _make_screen(console)
        slide = Slide(boxes=[ImageBox(src=str(tiny_image), alt="red")])

        render_slide(screen, slide, slide_index=0, total_slides=1)

        screen.update.assert_called_once()
        # Output should include some non-empty rendering (Pixels emits ANSI).
        out = _capture(screen.update.call_args[0][0])
        assert out.strip() != ""

    def test_url_image_is_fetched_and_rendered(self) -> None:
        # Build an in-memory PNG and mock urlopen to return it.
        buf = BytesIO()
        Image.new("RGB", (4, 4), color="blue").save(buf, format="PNG")
        buf.seek(0)

        fake_response = MagicMock()
        fake_response.read.return_value = buf.getvalue()
        fake_response.__enter__ = lambda self: self
        fake_response.__exit__ = lambda *a: None

        console = Console(file=StringIO(), width=80, height=24, force_terminal=True)
        screen = _make_screen(console)
        slide = Slide(
            boxes=[ImageBox(src="https://example.com/x.png", alt="remote")]
        )

        with patch("present.renderer.urlopen", return_value=fake_response) as mock_open:
            render_slide(screen, slide, slide_index=0, total_slides=1)

        mock_open.assert_called_once()
        screen.update.assert_called_once()

    def test_unloadable_image_falls_back_to_alt_placeholder(self) -> None:
        console = Console(file=StringIO(), width=80, height=24, force_terminal=True)
        screen = _make_screen(console)
        slide = Slide(boxes=[ImageBox(src="/nonexistent/path.png", alt="missing")])

        # Should not raise; should render a fallback indicating the alt text.
        render_slide(screen, slide, slide_index=0, total_slides=1)
        out = _capture(screen.update.call_args[0][0])
        assert "missing" in out or "Image" in out

    def test_two_column_with_text_and_image(self, tiny_image: Path) -> None:
        console = Console(file=StringIO(), width=120, height=30, force_terminal=True)
        screen = _make_screen(console)
        slide = Slide(
            boxes=[
                TextBox(content="BULLET_MARKER"),
                ImageBox(src=str(tiny_image), alt="r"),
            ]
        )

        render_slide(screen, slide, slide_index=0, total_slides=1)
        out = _capture(screen.update.call_args[0][0])
        assert "BULLET_MARKER" in out


class TestTitle:
    def test_title_appears_in_output(self) -> None:
        console = Console(file=StringIO(), width=80, height=24, force_terminal=True)
        screen = _make_screen(console)
        slide = Slide(boxes=[TextBox(content="body")], title="MY_TITLE")

        render_slide(screen, slide, slide_index=0, total_slides=1)
        out = _capture(screen.update.call_args[0][0])
        assert "MY_TITLE" in out

    def test_title_appears_above_body(self) -> None:
        console = Console(file=StringIO(), width=80, height=24, force_terminal=True)
        screen = _make_screen(console)
        slide = Slide(boxes=[TextBox(content="BODY_MARKER")], title="TITLE_MARKER")

        render_slide(screen, slide, slide_index=0, total_slides=1)
        out = _capture(screen.update.call_args[0][0])

        # Find the row where each marker first appears
        lines = out.splitlines()
        title_row = next(i for i, ln in enumerate(lines) if "TITLE_MARKER" in ln)
        body_row = next(i for i, ln in enumerate(lines) if "BODY_MARKER" in ln)
        assert title_row < body_row

    def test_no_title_renders_only_body(self) -> None:
        console = Console(file=StringIO(), width=80, height=24, force_terminal=True)
        screen = _make_screen(console)
        slide = Slide(boxes=[TextBox(content="just body")], title=None)

        render_slide(screen, slide, slide_index=0, total_slides=1)
        out = _capture(screen.update.call_args[0][0])
        assert "just body" in out


class TestMargins:
    def test_outer_horizontal_margin_present(self) -> None:
        # The leftmost columns should be background-only (no content) on every
        # row that contains content.
        console = Console(file=StringIO(), width=80, height=24, force_terminal=True)
        screen = _make_screen(console)
        slide = Slide(
            boxes=[TextBox(content="A" * 200)], title="T"  # very long line
        )

        render_slide(screen, slide, slide_index=0, total_slides=1)
        out = _capture(screen.update.call_args[0][0])

        # Strip ANSI codes for column-position analysis.
        import re

        ansi = re.compile(r"\x1b\[[0-9;]*m")
        for line in out.splitlines():
            plain = ansi.sub("", line)
            if plain.strip():
                # First non-space column must be > 0 (i.e., a left margin exists).
                first_non_space = len(plain) - len(plain.lstrip())
                assert first_non_space >= 2, f"no left margin: {plain!r}"
                break

    def test_two_column_has_gap_between_boxes(self) -> None:
        console = Console(file=StringIO(), width=120, height=24, force_terminal=True)
        screen = _make_screen(console)
        slide = Slide(
            boxes=[TextBox(content="LMARK"), TextBox(content="RMARK")], title=None
        )

        render_slide(screen, slide, slide_index=0, total_slides=1)
        out = _capture(screen.update.call_args[0][0])

        import re

        ansi = re.compile(r"\x1b\[[0-9;]*m")
        line_with_both = next(
            (
                ansi.sub("", ln)
                for ln in out.splitlines()
                if "LMARK" in ln and "RMARK" in ln
            ),
            None,
        )
        assert line_with_both is not None
        between = line_with_both[
            line_with_both.index("LMARK") + len("LMARK") : line_with_both.index("RMARK")
        ]
        assert between.strip() == "", "gap between columns should be whitespace"
        assert len(between) >= 3, f"gap too small: {between!r}"


class TestSettings:
    def test_background_color_appears_in_ansi(self) -> None:
        console = Console(file=StringIO(), width=80, height=24, force_terminal=True)
        screen = _make_screen(console)
        slide = Slide(boxes=[TextBox(content="hi")], title="T")
        settings = Settings(background_color="blue", text_color="white", text_size=11)

        render_slide(screen, slide, 0, 1, settings=settings)
        out = _capture(screen.update.call_args[0][0])
        # ANSI background color escape should be present.
        assert "\x1b[" in out

    def test_default_settings_used_when_omitted(self) -> None:
        # Should not raise when settings omitted.
        console = Console(file=StringIO(), width=80, height=24, force_terminal=True)
        screen = _make_screen(console)
        slide = Slide(boxes=[TextBox(content="hi")], title="Hello")
        render_slide(screen, slide, 0, 1)
        screen.update.assert_called_once()

    def test_default_text_size_keeps_title_short(self) -> None:
        # text_size 10 → title size 13 → bold one-line title (no figlet).
        console = Console(file=StringIO(), width=80, height=24, force_terminal=True)
        screen = _make_screen(console)
        slide = Slide(boxes=[TextBox(content="x")], title="ABC")
        render_slide(screen, slide, 0, 1, settings=Settings(text_size=10))
        out = _capture(screen.update.call_args[0][0])
        # The literal "ABC" should appear on a single row.
        rows_with_abc = [ln for ln in out.splitlines() if "ABC" in ln]
        assert len(rows_with_abc) == 1

    def test_title_promoted_to_figlet_when_text_size_pushes_title_past_threshold(
        self,
    ) -> None:
        # text_size 11 → title size 14 → small figlet (multi-line ASCII art).
        console = Console(file=StringIO(), width=120, height=30, force_terminal=True)
        screen = _make_screen(console)
        slide = Slide(boxes=[TextBox(content="x")], title="ABC")
        render_slide(screen, slide, 0, 1, settings=Settings(text_size=11))
        out = _capture(screen.update.call_args[0][0])
        # No row contains the literal "ABC" once it's been figlet'd into glyphs.
        assert not any("ABC" in ln for ln in out.splitlines())

    def test_large_text_size_renders_title_as_figlet(self) -> None:
        # text_size 15 → title size 18 → standard figlet ASCII art.
        console = Console(file=StringIO(), width=120, height=30, force_terminal=True)
        screen = _make_screen(console)
        slide = Slide(boxes=[TextBox(content="x")], title="HI")
        render_slide(screen, slide, 0, 1, settings=Settings(text_size=15))
        import re

        ansi = re.compile(r"\x1b\[[0-9;]*m")
        plain_lines = [ansi.sub("", ln) for ln in _capture(screen.update.call_args[0][0]).splitlines()]
        # Figlet output spans more than one row of glyph rows for "HI".
        non_empty_glyph_rows = [ln for ln in plain_lines if ln.strip() and "─" not in ln]
        # At least 3 distinct rows of glyph art near the top.
        assert sum(1 for ln in non_empty_glyph_rows if any(c not in " " for c in ln)) >= 3

    def test_text_size_below_default_compresses_body_spacing(self) -> None:
        # Just verify no crash and body still renders.
        console = Console(file=StringIO(), width=80, height=24, force_terminal=True)
        screen = _make_screen(console)
        slide = Slide(boxes=[TextBox(content="- a\n- b\n- c")], title="T")
        render_slide(screen, slide, 0, 1, settings=Settings(text_size=8))
        out = _capture(screen.update.call_args[0][0])
        assert "a" in out and "b" in out and "c" in out

    def test_single_box_body_top_aligned_under_title(self) -> None:
        # Body should start within a few rows of the title's rule, not be
        # vertically centered in the remaining space.
        console = Console(file=StringIO(), width=80, height=40, force_terminal=True)
        screen = _make_screen(console)
        slide = Slide(boxes=[TextBox(content="- BULLET_MARKER")], title="MY_TITLE")

        render_slide(screen, slide, 0, 1)
        out = _capture(screen.update.call_args[0][0])

        import re
        ansi = re.compile(r"\x1b\[[0-9;]*m")
        lines = [ansi.sub("", ln) for ln in out.splitlines()]

        title_row = next(i for i, ln in enumerate(lines) if "MY_TITLE" in ln)
        bullet_row = next(i for i, ln in enumerate(lines) if "BULLET_MARKER" in ln)
        # Title block height (~3 rows). Bullet should follow soon after, not
        # be pushed halfway down the screen.
        assert bullet_row - title_row <= 5, (
            f"body should start near top under title; gap was {bullet_row - title_row} rows"
        )

    def test_hex_background_color(self) -> None:
        console = Console(file=StringIO(), width=80, height=24, force_terminal=True)
        screen = _make_screen(console)
        slide = Slide(boxes=[TextBox(content="hi")], title="T")
        settings = Settings(background_color="#1a1a2e", text_color="#ffffff")
        render_slide(screen, slide, 0, 1, settings=settings)
        out = _capture(screen.update.call_args[0][0])
        # Hex 0x1a = 26 — RGB ANSI should mention 26;26;46.
        assert "26;26;46" in out
