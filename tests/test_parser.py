from __future__ import annotations

from present.parser import (
    ImageBox,
    Settings,
    Slide,
    TextBox,
    parse,
    parse_slides,
)


class TestParseSlidesSeparators:
    def test_single_slide_no_separator(self) -> None:
        slides = parse_slides("# Hello\n\nSome content")
        assert len(slides) == 1
        assert slides[0].title == "Hello"
        assert isinstance(slides[0].boxes[0], TextBox)
        assert "Some content" in slides[0].boxes[0].content

    def test_two_slides(self) -> None:
        slides = parse_slides("# Slide 1\n\n---\n\n# Slide 2")
        assert len(slides) == 2

    def test_separator_inside_code_fence_ignored(self) -> None:
        md = "# Slide 1\n\n```\n---\n```\n\n---\n\n# Slide 2"
        slides = parse_slides(md)
        assert len(slides) == 2
        assert "```" in slides[0].boxes[0].content  # type: ignore[union-attr]

    def test_strips_leading_trailing_whitespace(self) -> None:
        md = "\n\n# Slide 1\n\nA\n\n---\n\n\n# Slide 2\n\nB\n"
        slides = parse_slides(md)
        assert slides[0].title == "Slide 1"
        assert slides[1].title == "Slide 2"

    def test_empty_string_returns_one_slide(self) -> None:
        slides = parse_slides("")
        assert len(slides) == 1

    def test_tilde_code_fence_not_split(self) -> None:
        md = "# Slide 1\n\n~~~\n---\n~~~\n\n---\n\n# Slide 2"
        slides = parse_slides(md)
        assert len(slides) == 2

    def test_separator_variants(self) -> None:
        slides = parse_slides("# A\n\n  ---  \n\n# B")
        assert len(slides) == 2


class TestSlideTitle:
    def test_leading_h1_extracted_as_title(self) -> None:
        slide = parse_slides("# My Title\n\nbody text")[0]
        assert slide.title == "My Title"
        assert "# My Title" not in slide.boxes[0].content  # type: ignore[union-attr]
        assert "body text" in slide.boxes[0].content  # type: ignore[union-attr]

    def test_leading_h2_extracted_as_title(self) -> None:
        slide = parse_slides("## Section\n\n- a\n- b")[0]
        assert slide.title == "Section"

    def test_no_heading_means_no_title(self) -> None:
        slide = parse_slides("just paragraphs\n\nno heading here")[0]
        assert slide.title is None
        assert "just paragraphs" in slide.boxes[0].content  # type: ignore[union-attr]

    def test_only_first_leading_heading_is_title(self) -> None:
        slide = parse_slides("# Title\n\n## Sub\n\nbody")[0]
        assert slide.title == "Title"
        assert "## Sub" in slide.boxes[0].content  # type: ignore[union-attr]

    def test_title_extracted_before_column_split(self) -> None:
        md = "# Big Title\n\nleft\n\n:::\n\nright"
        slide = parse_slides(md)[0]
        assert slide.title == "Big Title"
        assert len(slide.boxes) == 2
        assert "left" in slide.boxes[0].content  # type: ignore[union-attr]
        assert "right" in slide.boxes[1].content  # type: ignore[union-attr]

    def test_title_strips_inline_formatting_markers(self) -> None:
        # The raw string is preserved (including markdown emphasis); renderer interprets it.
        slide = parse_slides("# **Bold** Title\n\nbody")[0]
        assert slide.title == "**Bold** Title"

    def test_title_with_leading_blank_lines(self) -> None:
        slide = parse_slides("\n\n\n# Title\n\nbody")[0]
        assert slide.title == "Title"


class TestSingleBoxLayout:
    def test_slide_with_no_column_separator_is_one_box(self) -> None:
        slides = parse_slides("# Title\n\nBody text")
        assert len(slides[0].boxes) == 1
        assert isinstance(slides[0].boxes[0], TextBox)

    def test_text_box_preserves_markdown(self) -> None:
        slides = parse_slides("- one\n- two\n- three")
        box = slides[0].boxes[0]
        assert isinstance(box, TextBox)
        assert "- one" in box.content
        assert "- three" in box.content


class TestTwoColumnLayout:
    def test_column_separator_splits_slide_into_two_boxes(self) -> None:
        md = "# Title\n\nLeft side\n\n:::\n\nRight side"
        slides = parse_slides(md)
        assert len(slides) == 1
        assert len(slides[0].boxes) == 2

    def test_left_box_contains_left_content(self) -> None:
        md = "Left text\n\n:::\n\nRight text"
        slide = parse_slides(md)[0]
        left, right = slide.boxes
        assert isinstance(left, TextBox)
        assert isinstance(right, TextBox)
        assert "Left text" in left.content
        assert "Right text" in right.content

    def test_column_separator_inside_code_fence_ignored(self) -> None:
        md = "Left\n\n```\n:::\n```\n\n:::\n\nRight"
        slide = parse_slides(md)[0]
        assert len(slide.boxes) == 2
        assert "```" in slide.boxes[0].content  # type: ignore[union-attr]

    def test_only_one_column_separator_allowed_extras_kept_in_right_box(self) -> None:
        # Per spec: max two boxes. Second/subsequent ::: are part of right box content.
        md = "Left\n\n:::\n\nMiddle\n\n:::\n\nRight"
        slide = parse_slides(md)[0]
        assert len(slide.boxes) == 2

    def test_column_separator_with_whitespace(self) -> None:
        md = "Left\n\n  :::  \n\nRight"
        slide = parse_slides(md)[0]
        assert len(slide.boxes) == 2


class TestImageBox:
    def test_box_with_only_image_becomes_image_box(self) -> None:
        md = "![Alt text](https://example.com/pic.png)"
        slide = parse_slides(md)[0]
        box = slide.boxes[0]
        assert isinstance(box, ImageBox)
        assert box.src == "https://example.com/pic.png"
        assert box.alt == "Alt text"

    def test_image_box_in_two_column_layout(self) -> None:
        md = "- bullet one\n- bullet two\n\n:::\n\n![Portrait](http://example.com/p.jpg)"
        slide = parse_slides(md)[0]
        left, right = slide.boxes
        assert isinstance(left, TextBox)
        assert isinstance(right, ImageBox)
        assert right.src == "http://example.com/p.jpg"

    def test_text_with_inline_image_stays_text_box(self) -> None:
        md = "Some intro\n\n![pic](x.png)\n\nMore text"
        slide = parse_slides(md)[0]
        assert isinstance(slide.boxes[0], TextBox)

    def test_image_alt_can_be_empty(self) -> None:
        md = "![](https://example.com/x.png)"
        box = parse_slides(md)[0].boxes[0]
        assert isinstance(box, ImageBox)
        assert box.alt == ""
        assert box.src == "https://example.com/x.png"

    def test_image_with_surrounding_whitespace(self) -> None:
        md = "\n\n![pic](x.png)\n\n"
        box = parse_slides(md)[0].boxes[0]
        assert isinstance(box, ImageBox)


class TestSlideDataclass:
    def test_slide_exposes_boxes_list(self) -> None:
        slide = Slide(boxes=[TextBox(content="hi")])
        assert slide.boxes[0].content == "hi"  # type: ignore[union-attr]


class TestPresentationFrontmatter:
    def test_default_settings_when_no_frontmatter(self) -> None:
        pres = parse("# Hello\n\nbody")
        assert pres.settings == Settings()
        assert pres.settings.background_color == "white"
        assert pres.settings.text_color == "black"
        assert pres.settings.text_size == 10
        assert len(pres.slides) == 1

    def test_frontmatter_parsed(self) -> None:
        md = (
            "---\n"
            "background_color: navy\n"
            "text_color: white\n"
            "text_size: 14\n"
            "---\n\n# Hello"
        )
        pres = parse(md)
        assert pres.settings.background_color == "navy"
        assert pres.settings.text_color == "white"
        assert pres.settings.text_size == 14

    def test_frontmatter_subset_uses_defaults_for_missing(self) -> None:
        md = "---\nbackground_color: red\n---\n\n# Hello"
        pres = parse(md)
        assert pres.settings.background_color == "red"
        assert pres.settings.text_color == "black"
        assert pres.settings.text_size == 10

    def test_frontmatter_stripped_from_slide_content(self) -> None:
        md = "---\nbackground_color: red\n---\n\n# Hello\n\nbody"
        pres = parse(md)
        assert len(pres.slides) == 1
        assert pres.slides[0].title == "Hello"
        body = pres.slides[0].boxes[0]
        assert isinstance(body, TextBox)
        assert "background_color" not in body.content
        assert "body" in body.content

    def test_unknown_field_ignored(self) -> None:
        md = "---\nfoo: bar\nbackground_color: red\n---\n\n# Hi"
        pres = parse(md)
        assert pres.settings.background_color == "red"

    def test_invalid_text_size_uses_default(self) -> None:
        md = "---\ntext_size: huge\n---\n\n# Hi"
        pres = parse(md)
        assert pres.settings.text_size == 10

    def test_no_closing_fence_treats_as_no_frontmatter(self) -> None:
        # Here the leading --- is just a slide separator; there's no closing.
        md = "---\nbackground_color: red\n# Hello"
        pres = parse(md)
        assert pres.settings == Settings()

    def test_hex_color_values_preserved(self) -> None:
        md = "---\nbackground_color: '#1a1a2e'\ntext_color: '#ffffff'\n---\n\n# Hi"
        pres = parse(md)
        assert pres.settings.background_color == "#1a1a2e"
        assert pres.settings.text_color == "#ffffff"

    def test_quoted_values_unquoted(self) -> None:
        md = '---\nbackground_color: "navy blue"\n---\n\n# Hi'
        pres = parse(md)
        assert pres.settings.background_color == "navy blue"

    def test_multiple_slides_after_frontmatter(self) -> None:
        md = "---\ntext_size: 12\n---\n\n# A\n\nx\n\n---\n\n# B\n\ny"
        pres = parse(md)
        assert len(pres.slides) == 2
        assert pres.slides[0].title == "A"
        assert pres.slides[1].title == "B"
