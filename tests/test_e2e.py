from __future__ import annotations

from io import StringIO
from pathlib import Path
from unittest.mock import patch

from rich.console import Console

from present.app import run


FIXTURES = Path(__file__).parent / "fixtures"


def test_full_presentation_navigates_all_slides() -> None:
    """E2E: load a 4-slide markdown file, navigate right through all slides, then quit."""
    markdown = (FIXTURES / "sample.md").read_text()

    rendered_slides: list[int] = []

    def fake_render(
        screen: object,
        content: object,
        slide_index: int,
        total_slides: int,
        **kwargs: object,
    ) -> None:
        rendered_slides.append(slide_index)

    # Simulate: right, right, right, q
    keys = iter(["right", "right", "right", "q"])

    with patch("present.app.render_slide", side_effect=fake_render):
        with patch("present.app.read_key", side_effect=keys):
            console = Console(file=StringIO(), width=80, height=24)
            run(markdown, console=console)

    # Should have rendered slide 0 initially, then 1, 2, 3 on each right press
    assert rendered_slides == [0, 1, 2, 3]


def test_presentation_clamps_navigation() -> None:
    """E2E: left at start stays at 0, right past end stays at last slide."""
    markdown = (FIXTURES / "sample.md").read_text()

    rendered_slides: list[int] = []

    def fake_render(
        screen: object,
        content: object,
        slide_index: int,
        total_slides: int,
        **kwargs: object,
    ) -> None:
        rendered_slides.append(slide_index)

    # left at start (stay 0), right, right, right, right (clamp at 3), left, q
    keys = iter(["left", "right", "right", "right", "right", "left", "q"])

    with patch("present.app.render_slide", side_effect=fake_render):
        with patch("present.app.read_key", side_effect=keys):
            console = Console(file=StringIO(), width=80, height=24)
            run(markdown, console=console)

    assert rendered_slides == [0, 0, 1, 2, 3, 3, 2]
