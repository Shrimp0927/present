from __future__ import annotations

from typing import TYPE_CHECKING

from present.input import read_key
from present.parser import parse
from present.renderer import render_slide

if TYPE_CHECKING:
    from rich.console import Console


def run(markdown_content: str, console: Console | None = None) -> None:
    """Run the presentation loop."""
    from rich.console import Console as RichConsole

    if console is None:
        console = RichConsole()

    presentation = parse(markdown_content)
    slides = presentation.slides
    settings = presentation.settings
    total = len(slides)
    current = 0

    bg = settings.background_color
    with console.screen(style=f"on {bg}") as screen:
        render_slide(screen, slides[current], current, total, settings=settings)

        while True:
            key = read_key()

            if key == "q":
                break
            elif key == "right":
                current = min(current + 1, total - 1)
            elif key == "left":
                current = max(current - 1, 0)

            render_slide(screen, slides[current], current, total, settings=settings)
