from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass
class CodeBlock:
    language: str
    code: str


@dataclass
class TableBlock:
    rows: int
    cols: int
    entries: list[str]


Segment = str | CodeBlock | TableBlock


@dataclass
class TextBox:
    content: str
    segments: list[Segment] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.segments:
            self.segments = _split_into_segments(self.content)


@dataclass
class ImageBox:
    src: str
    alt: str


Box = TextBox | ImageBox


@dataclass
class Slide:
    boxes: list[Box]
    title: str | None = field(default=None)


@dataclass
class Settings:
    background_color: str = "white"
    text_color: str = "black"
    text_size: int = 10


@dataclass
class Presentation:
    settings: Settings
    slides: list[Slide]


SLIDE_SEPARATOR = re.compile(r"^\s*---\s*$")
COLUMN_SEPARATOR = re.compile(r"^\s*:::\s*$")
IMAGE_ONLY = re.compile(r"^!\[([^\]]*)\]\(([^)]+)\)$")
LEADING_HEADING = re.compile(r"^\s*#{1,6}\s+(.+?)\s*$")
FENCE_OPEN = re.compile(r"^\s*(```|~~~)\s*([^\s`~]*)\s*$")
TABLE_DIRECTIVE = re.compile(r"^\s*table\s+(\d+)[xX](\d+)\s*$", re.IGNORECASE)


def parse(markdown: str) -> Presentation:
    """Parse a markdown presentation: optional frontmatter + slides."""
    settings, body = _extract_frontmatter(markdown)
    return Presentation(settings=settings, slides=parse_slides(body))


def parse_slides(markdown: str) -> list[Slide]:
    """Split markdown into slides; within each slide, support a two-column layout."""
    raw_slides = _split_on(markdown, SLIDE_SEPARATOR)
    return [_build_slide(s) for s in raw_slides]


def _extract_frontmatter(markdown: str) -> tuple[Settings, str]:
    """Detect a leading ``---``/``---`` frontmatter block; otherwise return defaults."""
    lines = markdown.split("\n")
    if not lines or not SLIDE_SEPARATOR.match(lines[0]):
        return Settings(), markdown

    for i in range(1, len(lines)):
        if SLIDE_SEPARATOR.match(lines[i]):
            settings = _parse_settings_block(lines[1:i])
            body = "\n".join(lines[i + 1 :])
            return settings, body

    # No closing fence — treat as no frontmatter at all.
    return Settings(), markdown


def _parse_settings_block(lines: list[str]) -> Settings:
    settings = Settings()
    for line in lines:
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        key = key.strip()
        value = _unquote(value.strip())

        if key == "background_color":
            settings.background_color = value
        elif key == "text_color":
            settings.text_color = value
        elif key == "text_size":
            try:
                settings.text_size = int(value)
            except ValueError:
                pass
    return settings


def _unquote(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
        return value[1:-1]
    return value


def _split_on(markdown: str, separator: re.Pattern[str]) -> list[str]:
    """Split markdown on a separator regex, ignoring matches inside code fences."""
    lines = markdown.split("\n")
    chunks: list[str] = []
    current: list[str] = []
    in_fence = False

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("```") or stripped.startswith("~~~"):
            in_fence = not in_fence

        if not in_fence and separator.match(line):
            chunks.append("\n".join(current).strip())
            current = []
        else:
            current.append(line)

    chunks.append("\n".join(current).strip())
    return chunks


def _build_slide(raw: str) -> Slide:
    title, body = _extract_title(raw)
    parts = _split_on(body, COLUMN_SEPARATOR)

    if len(parts) > 2:
        parts = [parts[0], "\n\n:::\n\n".join(parts[1:])]

    return Slide(title=title, boxes=[_box_from(p) for p in parts])


def _extract_title(raw: str) -> tuple[str | None, str]:
    lines = raw.split("\n")
    i = 0
    while i < len(lines) and not lines[i].strip():
        i += 1

    if i >= len(lines):
        return None, ""

    match = LEADING_HEADING.match(lines[i])
    if not match:
        return None, raw

    title = match.group(1).strip()
    body = "\n".join(lines[i + 1 :]).strip()
    return title, body


def _box_from(content: str) -> Box:
    stripped = content.strip()
    match = IMAGE_ONLY.match(stripped)
    if match:
        alt, src = match.group(1), match.group(2)
        return ImageBox(src=src, alt=alt)
    return TextBox(content=content)


def _split_into_segments(content: str) -> list[Segment]:
    """Walk the content line by line, peeling fenced code blocks into CodeBlocks.

    Inline backticks are left inside text segments — Markdown renders them as
    snippets the same way it renders bold/italic.
    """
    lines = content.split("\n")
    segments: list[Segment] = []
    text_buf: list[str] = []
    i = 0

    def flush_text() -> None:
        if not text_buf:
            return
        joined = "\n".join(text_buf).strip("\n")
        if joined:
            segments.append(joined)
        text_buf.clear()

    while i < len(lines):
        open_match = FENCE_OPEN.match(lines[i])
        if open_match:
            fence = open_match.group(1)
            language = open_match.group(2)
            code_lines: list[str] = []
            j = i + 1
            closed = False
            while j < len(lines):
                if lines[j].strip() == fence:
                    closed = True
                    break
                code_lines.append(lines[j])
                j += 1

            if closed:
                flush_text()
                segments.append(CodeBlock(language=language, code="\n".join(code_lines)))
                i = j + 1
                continue

        table_match = TABLE_DIRECTIVE.match(lines[i])
        if table_match:
            rows = int(table_match.group(1))
            cols = int(table_match.group(2))
            needed = rows * cols
            entries = [ln.strip() for ln in lines[i + 1 : i + 1 + needed]]
            entries.extend([""] * (needed - len(entries)))
            flush_text()
            segments.append(TableBlock(rows=rows, cols=cols, entries=entries))
            i += 1 + needed
            continue

        text_buf.append(lines[i])
        i += 1

    flush_text()
    if not segments:
        segments.append("")
    return segments
