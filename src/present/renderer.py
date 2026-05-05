from __future__ import annotations

import re
import ssl
from io import BytesIO
from urllib.request import Request, urlopen

import certifi
import pyfiglet
from PIL import Image
from rich.align import Align
from rich.console import Console, ConsoleRenderable, Group
from rich.markdown import Markdown
from rich.padding import Padding
from rich.rule import Rule
from rich.screen import Screen
from rich.style import Style
from rich.syntax import Syntax
from rich.table import Table
from rich.text import Text
from rich_pixels import Pixels

from present.parser import (
    Box,
    CodeBlock,
    ImageBox,
    Segment,
    Settings,
    Slide,
    TableBlock,
    TextBox,
)

CODE_THEME = "monokai"

USER_AGENT = "present-cli/0.1 (https://github.com/anthropics/claude-code)"

OUTER_MARGIN_X = 6
OUTER_MARGIN_Y = 2
COLUMN_GAP = 4
TITLE_BLOCK_HEIGHT = 3  # title row + rule row + spacer row

DEFAULT_TEXT_SIZE = 10
TITLE_SIZE_OFFSET = 3  # title is rendered this many sizes larger than body
FIGLET_THRESHOLD = 14  # title size at/above this uses figlet
FIGLET_LARGE_THRESHOLD = 18  # title size at/above this uses the larger figlet font


def render_slide(
    screen: object,
    slide: Slide,
    slide_index: int,
    total_slides: int,
    settings: Settings | None = None,
) -> None:
    """Render a slide full-screen with title, margins, and theme settings applied."""
    settings = settings or Settings()
    console: Console = screen.console  # type: ignore[attr-defined]
    width, height = console.size

    inner_w = max(width - 2 * OUTER_MARGIN_X, 10)
    body_height = max(height - 2 * OUTER_MARGIN_Y, 4)

    parts: list[ConsoleRenderable] = []
    if slide.title:
        title_block = _render_title(slide.title, settings)
        parts.append(title_block)
        body_height -= _title_block_height(settings)

    parts.append(_render_body(slide.boxes, inner_w, max(body_height, 4), settings))

    content = Group(*parts)
    style = _safe_style(f"{settings.text_color} on {settings.background_color}")
    padded = Padding(content, (OUTER_MARGIN_Y, OUTER_MARGIN_X), style=style)
    screen.update(Screen(padded, style=style))  # type: ignore[attr-defined]


def _safe_style(spec: str) -> Style:
    """Parse a style; fall back to default black-on-white if a color is invalid."""
    try:
        return Style.parse(spec)
    except Exception:
        return Style.parse("black on white")


def _title_size(settings: Settings) -> int:
    return settings.text_size + TITLE_SIZE_OFFSET


def _render_title(title: str, settings: Settings) -> ConsoleRenderable:
    style = _safe_style(f"bold {settings.text_color}")
    title_size = _title_size(settings)
    if title_size >= FIGLET_THRESHOLD:
        font = "small" if title_size < FIGLET_LARGE_THRESHOLD else "standard"
        try:
            art = pyfiglet.figlet_format(title, font=font).rstrip("\n")
        except Exception:
            art = title
        body = Text(art, style=style, justify="center")
    else:
        body = Text(title, style=style, justify="center")

    rule_style = _safe_style(f"dim {settings.text_color}")
    return Group(body, Rule(style=rule_style), Text(""))


def _title_block_height(settings: Settings) -> int:
    title_size = _title_size(settings)
    if title_size >= FIGLET_THRESHOLD:
        return _figlet_row_count(title_size) + 2
    return TITLE_BLOCK_HEIGHT


def _figlet_row_count(title_size: int) -> int:
    # "small" font is ~5 rows, "standard" ~6 rows.
    return 5 if title_size < FIGLET_LARGE_THRESHOLD else 6


def _render_body(
    boxes: list[Box], inner_w: int, body_height: int, settings: Settings
) -> ConsoleRenderable:
    if len(boxes) == 1:
        return _render_box(boxes[0], inner_w, body_height, settings)
    return _render_two_columns(boxes, inner_w, body_height, settings)


def _render_two_columns(
    boxes: list[Box], width: int, height: int, settings: Settings
) -> ConsoleRenderable:
    table = Table.grid(expand=True, padding=(0, COLUMN_GAP // 2))
    table.add_column(ratio=1)
    table.add_column(ratio=1)
    col_width = max((width - COLUMN_GAP) // 2, 10)
    left = _render_box(boxes[0], col_width, height, settings)
    right = _render_box(boxes[1], col_width, height, settings)
    table.add_row(left, right)
    return table


def _render_box(
    box: Box, width: int, height: int, settings: Settings
) -> ConsoleRenderable:
    if isinstance(box, TextBox):
        return _render_text_box(box, settings)
    return _render_image(box, width=width, height=height)


def _render_text_box(box: TextBox, settings: Settings) -> ConsoleRenderable:
    parts: list[ConsoleRenderable] = []
    for segment in box.segments:
        rendered = _render_segment(segment, settings)
        if rendered is not None:
            parts.append(rendered)
    if len(parts) == 1:
        return parts[0]
    return Group(*parts)


def _render_segment(
    segment: Segment, settings: Settings
) -> ConsoleRenderable | None:
    if isinstance(segment, CodeBlock):
        lexer = segment.language or "text"
        return Syntax(
            segment.code,
            lexer,
            theme=CODE_THEME,
            background_color="default",
            word_wrap=True,
            padding=(0, 1),
        )
    if isinstance(segment, TableBlock):
        return _render_table(segment, settings)
    text = segment.strip("\n")
    if not text:
        return None
    return Markdown(_scale_body(text, settings.text_size), code_theme=CODE_THEME)


def _render_table(table: TableBlock, settings: Settings) -> ConsoleRenderable:
    border_style = _safe_style(f"dim {settings.text_color}")
    header_style = _safe_style(f"bold {settings.text_color}")
    rich_table = Table(
        show_header=False,
        show_lines=True,
        border_style=border_style,
        header_style=header_style,
        pad_edge=False,
    )
    for _ in range(table.cols):
        rich_table.add_column(ratio=1, justify="left", overflow="fold")

    for r in range(table.rows):
        start = r * table.cols
        row_cells = table.entries[start : start + table.cols]
        rich_table.add_row(*row_cells)
    return rich_table


def _scale_body(content: str, text_size: int) -> str:
    """Inject blank lines between block elements when text_size > default.

    Pure terminal output can't actually scale glyph size, but extra inter-block
    spacing makes larger sizes feel airier and keeps the bullets from crowding.
    """
    extra = max(text_size - DEFAULT_TEXT_SIZE, 0) // 3
    if extra == 0:
        return content
    spacer = "\n" * extra
    return re.sub(r"\n\n+", "\n\n" + spacer, content)


def _render_image(box: ImageBox, width: int, height: int) -> ConsoleRenderable:
    image = _load_image(box.src)
    if image is None:
        label = box.alt or box.src
        return Text(f"[Image: {label}]", style="italic dim")

    target_w_cells = max(width - 2, 4)
    target_h_cells = max(height - 2, 4)
    target_w_px = target_w_cells
    target_h_px = target_h_cells * 2

    iw, ih = image.size
    scale = min(target_w_px / iw, target_h_px / ih, 1.0)
    if scale < 1.0:
        new_size = (max(int(iw * scale), 1), max(int(ih * scale), 1))
        image = image.resize(new_size)

    pixels = Pixels.from_image(image)
    if box.alt:
        return Group(
            Align.center(pixels),
            Align.center(Text(box.alt, style="dim italic")),
        )
    return Align.center(pixels)


def _load_image(src: str) -> Image.Image | None:
    try:
        if src.startswith(("http://", "https://")):
            ctx = ssl.create_default_context(cafile=certifi.where())
            req = Request(src, headers={"User-Agent": USER_AGENT})
            with urlopen(req, timeout=10, context=ctx) as resp:
                data = resp.read()
            return Image.open(BytesIO(data)).convert("RGB")
        return Image.open(src).convert("RGB")
    except Exception:
        return None
