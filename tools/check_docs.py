#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Check repository Markdown links that resolve to local files."""

from __future__ import annotations

import re
import sys
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]
DOCUMENT_TREES = (
    "docs",
    "enclosure",
    "firmware",
    "configurator",
    "hardware",
    "LICENSES",
)
MARKDOWN = tuple(
    sorted(
        {
            *ROOT.glob("*.md"),
            *(
                document
                for tree in DOCUMENT_TREES
                for document in (ROOT / tree).rglob("*.md")
            ),
        }
    )
)
LINK = re.compile(r"(?<!!)\[[^]]*\]\(([^)]+)\)")


def main() -> int:
    failures: list[str] = []
    for document in MARKDOWN:
        text = document.read_text(encoding="utf-8")
        for raw in LINK.findall(text):
            target = raw.split("#", 1)[0].strip().strip("<>")
            if not target or "://" in target or target.startswith("mailto:"):
                continue
            resolved = (document.parent / unquote(target)).resolve()
            try:
                resolved.relative_to(ROOT)
            except ValueError:
                failures.append(
                    f"{document.relative_to(ROOT)}: link escapes repository: {raw}"
                )
                continue
            if not resolved.exists():
                failures.append(
                    f"{document.relative_to(ROOT)}: missing link target: {raw}"
                )
    if failures:
        print("\n".join(f"FAIL: {failure}" for failure in failures))
        return 1
    print(f"PASS: {len(MARKDOWN)} Markdown files have valid local link targets.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
