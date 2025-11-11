#!/usr/bin/env python3
"""
Fix Markdown file encodings under docs/ and normalise a few common symbols.

Why: some pages were saved with non-UTF8 encodings causing mojibake (e.g. 'â€“').
This tool re-saves as UTF-8 and replaces a small set of problematic characters
with plain ASCII so other tools (including apply_patch) can edit safely.

Usage:
  python tools/docs_lint/fix_docs_encoding.py            # dry-run
  python tools/docs_lint/fix_docs_encoding.py --apply    # write changes
"""

from __future__ import annotations

import argparse
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DOCS_ROOT = REPO_ROOT / "docs"


REPLACEMENTS = {
    "\u2013": "-",   # en dash
    "\u2014": "-",   # em dash
    "\u2212": "-",   # minus sign
    "\u2192": "->",  # right arrow
    "\u2026": "...", # ellipsis
    "\u2018": "'",   # left single quote
    "\u2019": "'",   # right single quote
    "\u201c": '"',   # left double quote
    "\u201d": '"',   # right double quote
}

# Handle common mojibake sequences literally as seen in files
MOJIBAKE = {
    "â€“": "-",
    "â€”": "-",
    "â€‘": "-",
    "â†’": "->",
    "â€¦": "...",
}


def normalise_text(text: str) -> str:
    for bad, good in REPLACEMENTS.items():
        text = text.replace(bad, good)
    for bad, good in MOJIBAKE.items():
        text = text.replace(bad, good)
    return text


def read_any(path: Path) -> str:
    # Try utf-8 first, then cp1252, then latin-1
    for enc in ("utf-8", "cp1252", "latin-1"):
        try:
            return path.read_text(encoding=enc)
        except UnicodeDecodeError:
            continue
    # Fall back to binary with replacement to avoid crashing
    return path.read_text(encoding="utf-8", errors="replace")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="Write changes back to files.")
    ap.add_argument("--ext", default=".md", help="File extension to scan (default: .md)")
    args = ap.parse_args()

    changed = 0
    scanned = 0
    for md in DOCS_ROOT.rglob(f"*{args.ext}"):
        scanned += 1
        orig = read_any(md)
        fixed = normalise_text(orig)
        if fixed != orig:
            changed += 1
            rel = md.relative_to(REPO_ROOT)
            if args.apply:
                md.write_text(fixed, encoding="utf-8")
                print(f"[fix-docs-encoding] Rewrote {rel} -> UTF-8")
            else:
                print(f"[fix-docs-encoding] Would rewrite {rel}")

    print(f"[fix-docs-encoding] Scanned: {scanned}, Changed: {changed}, Apply: {args.apply}")


if __name__ == "__main__":
    main()

