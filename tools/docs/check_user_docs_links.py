from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DOCS = ROOT / "docs"

LINK_RE = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
CODE_FENCE_RE = re.compile(r"```.*?```", re.DOTALL)


def _strip_code_fences(text: str) -> str:
    return CODE_FENCE_RE.sub("", text)


def _is_external(target: str) -> bool:
    return target.startswith(("http://", "https://", "mailto:"))


def _clean_target(target: str) -> str:
    return target.split("#", 1)[0].strip()


def main() -> int:
    failures: list[str] = []

    for md in sorted(DOCS.rglob("*.md")):
        text = _strip_code_fences(md.read_text(encoding="utf-8", errors="replace"))
        for raw_target in LINK_RE.findall(text):
            target = _clean_target(raw_target)
            if not target or _is_external(target):
                continue
            if target.startswith("/"):
                failures.append(f"{md.relative_to(ROOT)}: absolute local link {raw_target!r}")
                continue
            candidate = (md.parent / target).resolve()
            try:
                candidate.relative_to(ROOT.resolve())
            except ValueError:
                failures.append(f"{md.relative_to(ROOT)}: link escapes repo {raw_target!r}")
                continue
            if not candidate.exists():
                failures.append(f"{md.relative_to(ROOT)}: missing link target {raw_target!r}")

    if failures:
        print("User docs link check failed:")
        for failure in failures:
            print(f"- {failure}")
        return 1

    print("User docs link check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
