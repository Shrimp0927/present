# present

A terminal presentation tool that renders Markdown files as full-screen slides, like PowerPoint but in your terminal.

## Installation

Requires Python 3.12+.

```bash
uv sync
```

## Usage

```bash
# If installed (uv sync installs the `present` command)
present slides.md

# Or run directly without installing
uv run present slides.md
```

### Navigation

- **Right arrow** — next slide
- **Left arrow** — previous slide
- **q** — quit

## Writing slides

### Presentation settings (frontmatter)

You can put a settings block at the very top of the file between two `---` lines:

```markdown
---
background_color: white
text_color: black
text_size: 11
---

# First slide
...
```

| Field              | Default | Notes                                                                  |
| ------------------ | ------- | ---------------------------------------------------------------------- |
| `background_color` | `white` | Any Rich-recognized color name (`navy_blue`, `red`, ...) or hex `#rrggbb`. |
| `text_color`       | `black` | Same color formats as above.                                           |
| `text_size`        | `11`    | At ≥14 the title is rendered as ASCII-art via figlet; larger values also widen the spacing between body bullets. Terminal cells can't truly grow, so this scales the title and inter-block spacing rather than the per-character glyph size. |

If a color is invalid, the renderer falls back to the default black-on-white. The frontmatter block is optional — omit it for the defaults.

### Slides

Slides are standard Markdown separated by `---` (horizontal rules):

```markdown
# Welcome

This is the first slide with **bold** and *italic* text.

---

## Features

- Bullet lists
- Tables
- Syntax-highlighted code blocks

---

## Code Example

\```python
def hello():
    print("Hello, world!")
\```

---

## Thanks

That's all!
```

### Supported content

- Headings (h1-h6)
- Paragraphs with **bold**, *italic*, ~~strikethrough~~
- Bullet and numbered lists
- Fenced code blocks with syntax highlighting
- Tables
- Images, rendered in the terminal via half-block pixels (local paths or `http(s)://` URLs)

Note: `---` inside fenced code blocks is not treated as a slide separator.

### Layouts

Each slide uses one of two layouts:

- **Common** (default) — one centered box. Just write markdown.
- **Two-column** — split a slide into a left and right box with a `:::` line.

A box whose only content is a single image (`![alt](src)`) renders as an image; otherwise it renders as markdown text.

### Titles

If a slide starts with a heading (`#`, `##`, ...), that heading is rendered as the slide title at the top, with a separator below it — like a Google Slides title bar. The heading is not also repeated in the body.

```markdown
# Two-column slide

- Bullet on the left
- Another bullet

:::

![Portrait](https://example.com/portrait.jpg)
```

`:::` inside a fenced code block is ignored. Only the first `:::` per slide splits; any further occurrences become literal text in the right box.

Slides have outer margins from the terminal edge, plus a gap between columns in the two-column layout — so content never butts up against the screen border.

## Development

```bash
# Run tests
uv run pytest

# Lint
uv run ruff check src/ tests/
```
