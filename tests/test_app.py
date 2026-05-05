from __future__ import annotations

from io import StringIO
from unittest.mock import patch

from rich.console import Console

from present.app import run


SAMPLE_MD = "# Slide 1\n\n---\n\n# Slide 2\n\n---\n\n# Slide 3"


class TestAppRun:
    def test_renders_first_slide_on_start(self) -> None:
        rendered: list[int] = []

        def fake_render(screen: object, content: object, slide_index: int, total_slides: int, **kwargs: object) -> None:
            rendered.append(slide_index)

        keys = iter(["q"])
        with patch("present.app.render_slide", side_effect=fake_render):
            with patch("present.app.read_key", side_effect=keys):
                console = Console(file=StringIO(), width=80, height=24)
                run(SAMPLE_MD, console=console)

        assert rendered[0] == 0

    def test_right_advances_slide(self) -> None:
        rendered: list[int] = []

        def fake_render(screen: object, content: object, slide_index: int, total_slides: int, **kwargs: object) -> None:
            rendered.append(slide_index)

        keys = iter(["right", "q"])
        with patch("present.app.render_slide", side_effect=fake_render):
            with patch("present.app.read_key", side_effect=keys):
                console = Console(file=StringIO(), width=80, height=24)
                run(SAMPLE_MD, console=console)

        assert rendered == [0, 1]

    def test_left_at_start_stays_at_zero(self) -> None:
        rendered: list[int] = []

        def fake_render(screen: object, content: object, slide_index: int, total_slides: int, **kwargs: object) -> None:
            rendered.append(slide_index)

        keys = iter(["left", "q"])
        with patch("present.app.render_slide", side_effect=fake_render):
            with patch("present.app.read_key", side_effect=keys):
                console = Console(file=StringIO(), width=80, height=24)
                run(SAMPLE_MD, console=console)

        assert rendered == [0, 0]

    def test_right_clamps_at_last_slide(self) -> None:
        rendered: list[int] = []

        def fake_render(screen: object, content: object, slide_index: int, total_slides: int, **kwargs: object) -> None:
            rendered.append(slide_index)

        keys = iter(["right", "right", "right", "right", "q"])
        with patch("present.app.render_slide", side_effect=fake_render):
            with patch("present.app.read_key", side_effect=keys):
                console = Console(file=StringIO(), width=80, height=24)
                run(SAMPLE_MD, console=console)

        assert rendered == [0, 1, 2, 2, 2]

    def test_q_exits(self) -> None:
        def fake_render(screen: object, content: object, slide_index: int, total_slides: int, **kwargs: object) -> None:
            pass

        keys = iter(["q"])
        with patch("present.app.render_slide", side_effect=fake_render):
            with patch("present.app.read_key", side_effect=keys):
                console = Console(file=StringIO(), width=80, height=24)
                run(SAMPLE_MD, console=console)
        # If we get here without hanging, the test passes
