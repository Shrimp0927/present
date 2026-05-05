from __future__ import annotations

import argparse
import sys
from pathlib import Path

from present.app import run


def main(argv: list[str] | None = None) -> None:
    """Entry point for the present CLI tool."""
    parser = argparse.ArgumentParser(
        prog="present",
        description="Terminal presentation tool for markdown files",
    )
    parser.add_argument("file", type=Path, help="Path to a markdown file")
    args = parser.parse_args(argv)

    filepath: Path = args.file
    if not filepath.exists():
        print(f"Error: file not found: {filepath}", file=sys.stderr)
        sys.exit(1)

    markdown = filepath.read_text()
    run(markdown)


if __name__ == "__main__":
    main()
