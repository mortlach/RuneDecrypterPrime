from __future__ import annotations

from pathlib import Path


def test_active_tutorial_labels_do_not_use_deprecated_demo_language() -> None:
    root = Path(__file__).resolve().parents[2]
    checked_roots = [
        root / "src",
        root / "tutorials" / "v1",
        root / "tests",
        root / "docs",
        root / "v1_docs",
        root / "solving",
    ]
    deprecated_labels = (
        "show" + "case",
        "near" + "-solve",
        "near" + "_solve",
        "near" + " solve",
    )
    offenders: list[str] = []

    for base in checked_roots:
        for path in base.rglob("*"):
            if not path.is_file() or path.suffix.lower() not in {".py", ".json", ".md", ".txt"}:
                continue
            text = path.read_text(encoding="utf-8").lower()
            matches = [label for label in deprecated_labels if label in text]
            if matches:
                relpath = path.relative_to(root).as_posix()
                offenders.append(f"{relpath}: {', '.join(matches)}")

    assert offenders == []
