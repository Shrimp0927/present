from __future__ import annotations

from present.parser import (
    CodeBlock,
    ImageBox,
    Settings,
    Slide,
    TableBlock,
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


class TestCodeBlockSegments:
    def test_textbox_without_code_has_one_text_segment(self) -> None:
        box = parse_slides("Just plain text\n\nmore text")[0].boxes[0]
        assert isinstance(box, TextBox)
        assert box.segments == ["Just plain text\n\nmore text"]

    def test_fenced_code_block_extracted_as_codeblock_segment(self) -> None:
        md = "intro line\n\n```python\ndef hi():\n    print('hi')\n```\n\nafter"
        box = parse_slides(md)[0].boxes[0]
        assert isinstance(box, TextBox)
        assert len(box.segments) == 3
        assert box.segments[0] == "intro line"
        assert isinstance(box.segments[1], CodeBlock)
        assert box.segments[1].language == "python"
        assert box.segments[1].code == "def hi():\n    print('hi')"
        assert box.segments[2] == "after"

    def test_code_only_box_has_single_codeblock_segment(self) -> None:
        md = "```python\nprint(1)\n```"
        box = parse_slides(md)[0].boxes[0]
        assert isinstance(box, TextBox)
        assert len(box.segments) == 1
        assert isinstance(box.segments[0], CodeBlock)
        assert box.segments[0].language == "python"
        assert box.segments[0].code == "print(1)"

    def test_inline_backticks_stay_in_text_segment(self) -> None:
        # Single backticks are inline snippets, not blocks.
        md = "Use `os.path.join` to combine paths."
        box = parse_slides(md)[0].boxes[0]
        assert isinstance(box, TextBox)
        assert box.segments == ["Use `os.path.join` to combine paths."]

    def test_tilde_fenced_block_recognized(self) -> None:
        md = "before\n\n~~~js\nconsole.log(1);\n~~~\n\nafter"
        box = parse_slides(md)[0].boxes[0]
        assert isinstance(box, TextBox)
        assert len(box.segments) == 3
        assert isinstance(box.segments[1], CodeBlock)
        assert box.segments[1].language == "js"
        assert box.segments[1].code == "console.log(1);"

    def test_code_fence_without_language_has_empty_language(self) -> None:
        md = "```\nplain code\n```"
        box = parse_slides(md)[0].boxes[0]
        assert isinstance(box, TextBox)
        assert isinstance(box.segments[0], CodeBlock)
        assert box.segments[0].language == ""
        assert box.segments[0].code == "plain code"

    def test_multiple_code_blocks_in_one_box(self) -> None:
        md = "- item one\n\n```python\na = 1\n```\n\n- item two\n\n```python\nb = 2\n```"
        box = parse_slides(md)[0].boxes[0]
        assert isinstance(box, TextBox)
        # text, code, text, code
        assert len(box.segments) == 4
        assert isinstance(box.segments[1], CodeBlock)
        assert isinstance(box.segments[3], CodeBlock)
        assert box.segments[1].code == "a = 1"
        assert box.segments[3].code == "b = 2"

    def test_textbox_content_preserved_alongside_segments(self) -> None:
        # Raw content should still be available unchanged for callers that want it.
        md = "before\n\n```py\nx=1\n```\n\nafter"
        box = parse_slides(md)[0].boxes[0]
        assert isinstance(box, TextBox)
        assert "```py" in box.content
        assert "x=1" in box.content


class TestTableBlockSegments:
    def test_table_only_box_has_single_table_segment(self) -> None:
        md = "table 2x2\nA\nB\nC\nD"
        box = parse_slides(md)[0].boxes[0]
        assert isinstance(box, TextBox)
        assert len(box.segments) == 1
        seg = box.segments[0]
        assert isinstance(seg, TableBlock)
        assert seg.rows == 2
        assert seg.cols == 2
        assert seg.entries == ["A", "B", "C", "D"]

    def test_table_entries_fill_row_major(self) -> None:
        # 2 rows x 3 cols, row-major: (r0c0, r0c1, r0c2, r1c0, r1c1, r1c2)
        md = "table 2x3\none\ntwo\nthree\nfour\nfive\nsix"
        box = parse_slides(md)[0].boxes[0]
        seg = box.segments[0]
        assert isinstance(seg, TableBlock)
        assert seg.rows == 2
        assert seg.cols == 3
        assert seg.entries == ["one", "two", "three", "four", "five", "six"]

    def test_table_with_bullets_above_and_below(self) -> None:
        md = (
            "- bullet one\n"
            "- bullet two\n"
            "\n"
            "table 2x2\n"
            "A\n"
            "B\n"
            "C\n"
            "D\n"
            "\n"
            "- bullet three\n"
        )
        box = parse_slides(md)[0].boxes[0]
        assert isinstance(box, TextBox)
        # text, table, text
        assert len(box.segments) == 3
        assert isinstance(box.segments[1], TableBlock)
        assert "bullet one" in box.segments[0]
        assert "bullet three" in box.segments[2]

    def test_table_directive_case_insensitive(self) -> None:
        md = "TABLE 1x2\nleft\nright"
        seg = parse_slides(md)[0].boxes[0].segments[0]
        assert isinstance(seg, TableBlock)
        assert seg.rows == 1
        assert seg.cols == 2

    def test_dimensions_separator_is_x_or_capital_X(self) -> None:
        md = "table 2X2\nA\nB\nC\nD"
        seg = parse_slides(md)[0].boxes[0].segments[0]
        assert isinstance(seg, TableBlock)
        assert seg.rows == 2 and seg.cols == 2

    def test_1xN_table(self) -> None:
        md = "table 1x3\na\nb\nc"
        seg = parse_slides(md)[0].boxes[0].segments[0]
        assert isinstance(seg, TableBlock)
        assert seg.entries == ["a", "b", "c"]

    def test_missing_entries_are_padded_with_empty_strings(self) -> None:
        # Only 2 entries given for a 2x2 table → pad to 4.
        md = "table 2x2\nA\nB"
        seg = parse_slides(md)[0].boxes[0].segments[0]
        assert isinstance(seg, TableBlock)
        assert seg.entries == ["A", "B", "", ""]

    def test_table_alongside_code_block(self) -> None:
        md = (
            "intro\n\n"
            "table 1x2\nleft\nright\n\n"
            "```python\nprint(1)\n```\n"
        )
        box = parse_slides(md)[0].boxes[0]
        kinds = [type(s).__name__ if not isinstance(s, str) else "str" for s in box.segments]
        assert "TableBlock" in kinds
        assert "CodeBlock" in kinds

    def test_text_that_looks_like_table_directive_without_dimensions_stays_text(self) -> None:
        # "table" alone is normal text, not a directive.
        md = "I love tables.\ntable design is fun."
        box = parse_slides(md)[0].boxes[0]
        assert isinstance(box, TextBox)
        # No TableBlock, all stays text.
        assert all(isinstance(s, str) for s in box.segments)

    def test_table_inside_code_fence_is_not_treated_as_directive(self) -> None:
        md = "```\ntable 2x2\nA\nB\nC\nD\n```"
        box = parse_slides(md)[0].boxes[0]
        # The whole thing is a code block.
        assert len(box.segments) == 1
        assert isinstance(box.segments[0], CodeBlock)


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
