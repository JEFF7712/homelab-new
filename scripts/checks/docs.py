"""Fail on trailing whitespace in repository Markdown files.

Vendored dependency trees are skipped: their contents are not owned by this
repository (for example, OpenCode manages .opencode/node_modules itself and
ignores it via .opencode/.gitignore).
"""

from __future__ import annotations

import sys
from collections.abc import Iterator
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

SKIP_DIRECTORIES = frozenset({".git", ".agent-state", "node_modules"})


def iter_markdown_files(root: Path) -> Iterator[Path]:
    for path in root.rglob("*.md"):
        if SKIP_DIRECTORIES.intersection(path.parts):
            continue
        yield path


def trailing_whitespace_errors(root: Path) -> list[str]:
    errors = []
    for path in iter_markdown_files(root):
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if line.rstrip() != line:
                errors.append(f"{path.relative_to(root)}:{number}: trailing whitespace")
    return errors


def main() -> int:
    errors = trailing_whitespace_errors(ROOT)
    if errors:
        print("\n".join(errors), file=sys.stderr)
    return bool(errors)


if __name__ == "__main__":
    raise SystemExit(main())
