from __future__ import annotations

from io import BytesIO, StringIO
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from PIL import Image
from rich.console import Console

from present.parser import ImageBox, Settings, Slide, TableBlock, TextBox
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


_ANSI_RE = __import__("re").compile(r"\x1b\[[0-9;]*m")


def _plain(out: str) -> str:
    return _ANSI_RE.sub("", out)


class TestCodeBlockRender:
    def test_code_only_box_renders_with_syntax_highlighting(self) -> None:
        console = Console(file=StringIO(), width=80, height=24, force_terminal=True)
        screen = _make_screen(console)
        slide = Slide(
            boxes=[TextBox(content="```python\ndef hi():\n    return 1\n```")]
        )

        render_slide(screen, slide, slide_index=0, total_slides=1)
        out = _capture(screen.update.call_args[0][0])
        # The code itself is rendered (after stripping ANSI between tokens).
        plain = _plain(out)
        assert "def" in plain and "hi" in plain
        assert "return" in plain
        # Syntax highlighting emits truecolor foregrounds — `def` should carry one.
        assert "\x1b[38;2;" in out

    def test_code_block_after_bullets_appears_after_them(self) -> None:
        console = Console(file=StringIO(), width=100, height=30, force_terminal=True)
        screen = _make_screen(console)
        md = "- bullet ALPHA\n- bullet BETA\n\n```python\nGAMMA = 1\n```"
        slide = Slide(boxes=[TextBox(content=md)])

        render_slide(screen, slide, slide_index=0, total_slides=1)
        out = _capture(screen.update.call_args[0][0])

        import re

        ansi = re.compile(r"\x1b\[[0-9;]*m")
        plain_lines = [ansi.sub("", ln) for ln in out.splitlines()]
        alpha_row = next(i for i, ln in enumerate(plain_lines) if "ALPHA" in ln)
        beta_row = next(i for i, ln in enumerate(plain_lines) if "BETA" in ln)
        gamma_row = next(i for i, ln in enumerate(plain_lines) if "GAMMA" in ln)
        assert alpha_row < beta_row < gamma_row

    def test_code_block_between_bullets_appears_between(self) -> None:
        console = Console(file=StringIO(), width=100, height=30, force_terminal=True)
        screen = _make_screen(console)
        md = "- bullet ONE\n\n```python\nMID = 0\n```\n\n- bullet TWO"
        slide = Slide(boxes=[TextBox(content=md)])

        render_slide(screen, slide, slide_index=0, total_slides=1)
        out = _capture(screen.update.call_args[0][0])

        import re

        ansi = re.compile(r"\x1b\[[0-9;]*m")
        plain = [ansi.sub("", ln) for ln in out.splitlines()]
        one_row = next(i for i, ln in enumerate(plain) if "ONE" in ln)
        mid_row = next(i for i, ln in enumerate(plain) if "MID" in ln)
        two_row = next(i for i, ln in enumerate(plain) if "TWO" in ln)
        assert one_row < mid_row < two_row

    def test_code_block_language_drives_highlighting(self) -> None:
        # JavaScript "function" keyword should be highlighted differently
        # than the same word as plain text. We just assert that ANSI fg colors
        # appear, indicating Syntax (not plain Text) rendered the block.
        console = Console(file=StringIO(), width=80, height=24, force_terminal=True)
        screen = _make_screen(console)
        slide = Slide(
            boxes=[TextBox(content="```javascript\nfunction hi() { return 1; }\n```")]
        )
        render_slide(screen, slide, slide_index=0, total_slides=1)
        out = _capture(screen.update.call_args[0][0])
        assert "function" in out
        assert "\x1b[38;2;" in out

    def test_inline_code_snippet_rendered_inline_with_text(self) -> None:
        # Single-backtick snippets are inline; content must appear on the same
        # line as surrounding text, not on a separate code-block-style line.
        console = Console(file=StringIO(), width=80, height=24, force_terminal=True)
        screen = _make_screen(console)
        slide = Slide(boxes=[TextBox(content="Use `pathlib.Path` for files.")])

        render_slide(screen, slide, slide_index=0, total_slides=1)
        out = _capture(screen.update.call_args[0][0])

        import re

        ansi = re.compile(r"\x1b\[[0-9;]*m")
        plain = [ansi.sub("", ln) for ln in out.splitlines()]
        # The snippet text and surrounding words land on the same row.
        same_row = next(
            (ln for ln in plain if "Use" in ln and "pathlib.Path" in ln and "for files" in ln),
            None,
        )
        assert same_row is not None

    def test_code_block_in_two_column_layout(self) -> None:
        console = Console(file=StringIO(), width=140, height=30, force_terminal=True)
        screen = _make_screen(console)
        slide = Slide(
            boxes=[
                TextBox(content="LEFT_TEXT"),
                TextBox(content="```python\nRIGHT_CODE = 1\n```"),
            ]
        )
        render_slide(screen, slide, slide_index=0, total_slides=1)
        out = _capture(screen.update.call_args[0][0])
        assert "LEFT_TEXT" in out
        assert "RIGHT_CODE" in out


class TestTableRender:
    def test_table_only_box_renders_all_entries(self) -> None:
        console = Console(file=StringIO(), width=80, height=24, force_terminal=True)
        screen = _make_screen(console)
        slide = Slide(
            boxes=[TextBox(content="table 2x2\nALPHA\nBETA\nGAMMA\nDELTA")]
        )
        render_slide(screen, slide, slide_index=0, total_slides=1)
        plain = _plain(_capture(screen.update.call_args[0][0]))
        for entry in ("ALPHA", "BETA", "GAMMA", "DELTA"):
            assert entry in plain, f"missing entry {entry!r} in output"

    def test_table_entries_rendered_row_major(self) -> None:
        # Row 0: TOPLEFT TOPRIGHT
        # Row 1: BOTLEFT BOTRIGHT
        # First, top row must come above bottom row vertically.
        # Second, on each row, left column must precede right column horizontally.
        console = Console(file=StringIO(), width=100, height=30, force_terminal=True)
        screen = _make_screen(console)
        slide = Slide(
            boxes=[
                TextBox(
                    content="table 2x2\nTOPLEFT\nTOPRIGHT\nBOTLEFT\nBOTRIGHT"
                )
            ]
        )
        render_slide(screen, slide, slide_index=0, total_slides=1)
        out_lines = [_plain(ln) for ln in _capture(screen.update.call_args[0][0]).splitlines()]

        topleft_row = next(i for i, ln in enumerate(out_lines) if "TOPLEFT" in ln)
        botleft_row = next(i for i, ln in enumerate(out_lines) if "BOTLEFT" in ln)
        assert topleft_row < botleft_row

        top_row_text = out_lines[topleft_row]
        assert "TOPRIGHT" in top_row_text
        assert top_row_text.index("TOPLEFT") < top_row_text.index("TOPRIGHT")

        bot_row_text = out_lines[botleft_row]
        assert "BOTRIGHT" in bot_row_text
        assert bot_row_text.index("BOTLEFT") < bot_row_text.index("BOTRIGHT")

    def test_table_between_bullets(self) -> None:
        md = (
            "- bullet ABOVE\n\n"
            "table 1x2\nLCELL\nRCELL\n\n"
            "- bullet BELOW\n"
        )
        console = Console(file=StringIO(), width=100, height=30, force_terminal=True)
        screen = _make_screen(console)
        slide = Slide(boxes=[TextBox(content=md)])
        render_slide(screen, slide, slide_index=0, total_slides=1)
        out_lines = [_plain(ln) for ln in _capture(screen.update.call_args[0][0]).splitlines()]
        above = next(i for i, ln in enumerate(out_lines) if "ABOVE" in ln)
        cell = next(i for i, ln in enumerate(out_lines) if "LCELL" in ln)
        below = next(i for i, ln in enumerate(out_lines) if "BELOW" in ln)
        assert above < cell < below

    def test_table_with_three_columns(self) -> None:
        md = "table 1x3\nA1\nB1\nC1"
        console = Console(file=StringIO(), width=100, height=30, force_terminal=True)
        screen = _make_screen(console)
        slide = Slide(boxes=[TextBox(content=md)])
        render_slide(screen, slide, slide_index=0, total_slides=1)
        out_lines = [_plain(ln) for ln in _capture(screen.update.call_args[0][0]).splitlines()]
        row = next(ln for ln in out_lines if "A1" in ln and "B1" in ln and "C1" in ln)
        assert row.index("A1") < row.index("B1") < row.index("C1")

    def test_table_in_two_column_layout(self) -> None:
        console = Console(file=StringIO(), width=140, height=30, force_terminal=True)
        screen = _make_screen(console)
        slide = Slide(
            boxes=[
                TextBox(content="LEFT_TEXT_MARKER"),
                TextBox(content="table 1x2\nXCELL\nYCELL"),
            ]
        )
        render_slide(screen, slide, slide_index=0, total_slides=1)
        plain = _plain(_capture(screen.update.call_args[0][0]))
        assert "LEFT_TEXT_MARKER" in plain
        assert "XCELL" in plain and "YCELL" in plain

    def test_directly_constructed_tableblock_renders(self) -> None:
        # A box built with explicit segments (skipping content parsing) still works.
        console = Console(file=StringIO(), width=80, height=24, force_terminal=True)
        screen = _make_screen(console)
        box = TextBox(
            content="",
            segments=[TableBlock(rows=1, cols=2, entries=["XX", "YY"])],
        )
        slide = Slide(boxes=[box])
        render_slide(screen, slide, slide_index=0, total_slides=1)
        plain = _plain(_capture(screen.update.call_args[0][0]))
        assert "XX" in plain and "YY" in plain


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
