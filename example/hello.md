# Welcome

This is the first slide with **bold** and *italic* text.

---

## Features

- Bullet lists
- Tables
- Syntax-highlighted code blocks

---

## Inline vs block

You can drop a `pathlib.Path` snippet inline, just like **bold** or *italic*.

- First, install the package
- Then call the helper:

```python
from pathlib import Path

def first_line(p: str) -> str:
    return Path(p).read_text().splitlines()[0]
```

- Finally, you're done!

---

## Code-only slide

```python
def hello():
    print("Hello, world!")
```

---

## Comparison

A few options at a glance:

- Built-in: easy, fewer features
- Library: more powerful, extra dep

table 3x2
Approach
Notes
Built-in
Quick to start
Library
More features

- Pick what fits your project!

---

## Pure table

table 3x3
Name
Role
Tenure
Ada
Engineer
3 yrs
Grace
Manager
8 yrs

---

## Thanks

That's all!
