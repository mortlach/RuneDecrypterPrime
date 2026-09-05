"""Contracts for the canonical V1 reader route and example catalogue."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.tier_a
ROOT = Path(__file__).resolve().parents[2]
README = ROOT / "README.md"
QUICKSTART = ROOT / "docs" / "guides" / "quickstart.md"
CATALOGUE = ROOT / "tutorials" / "v1" / "README.md"
ROADMAP = ROOT / "docs" / "ROADMAP.md"
EXAMPLES = ROOT / "tutorials" / "v1" / "examples"
ROUTE = ROOT / "tutorials" / "v1" / "getting_started"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_root_readme_uses_the_exact_public_identity_and_route() -> None:
    text = _read(README)
    assert "independent project by `mortlach`" in text
    assert "Mortlach" not in text
    assert "from rdp import api" in text
    assert "technically capable" in text
    for path in (
        "docs/setup/installation.md",
        "docs/guides/quickstart.md",
        "docs/guides/runes_and_text.md",
        "tutorials/v1/README.md",
    ):
        assert path in text


def test_quickstart_names_every_route_stop_in_order() -> None:
    text = _read(QUICKSTART)
    names = [
        path.name for path in sorted(ROUTE.glob("[0-9][0-9]_*.py"))
    ]
    offsets = [text.index(name) for name in names]
    assert offsets == sorted(offsets)
    assert "completed run is not relabelled as an exact solve" in text


def test_catalogue_covers_every_example_without_fixing_a_total() -> None:
    text = _read(CATALOGUE)
    examples = sorted(
        path.name for path in EXAMPLES.glob("*.py") if path.name != "__init__.py"
    )
    assert examples
    for filename in examples:
        assert f"examples/{filename}" in text
    for field in (
        "Purpose",
        "Cipher / solver",
        "Surface",
        "Assets",
        "Runtime",
        "Result",
        "Truth / oracle",
    ):
        assert field in text


def test_active_roadmap_retains_but_does_not_launch_p7_c7_work() -> None:
    text = _read(ROADMAP)
    assert "cipher_development/periodic_columnar_staged/" in text
    assert "select the next scientific question" in text
    assert "No new cipher development or long campaign is authorised" in text
    assert "never part of an ordinary install or release run" not in text
    assert "not part of these checks" in text


def test_canonical_docs_do_not_restore_retired_taxonomy_or_prohibited_tone() -> None:
    paths = (
        README,
        ROOT / "docs" / "README.md",
        ROOT / "docs" / "setup" / "installation.md",
        QUICKSTART,
        ROOT / "docs" / "guides" / "runes_and_text.md",
        CATALOGUE,
        ROADMAP,
    )
    joined = "\n".join(_read(path) for path in paths)
    assert "tutorial_manifest_v1" not in joined
    assert "ALL_WORKING" not in joined
    assert "CI_LIGHT" not in joined
    assert "high-school" not in joined.lower()
    assert ("show" + "case") not in joined.lower()


@pytest.mark.parametrize(
    "document",
    [
        README,
        ROOT / "docs" / "README.md",
        ROOT / "docs" / "setup" / "installation.md",
        QUICKSTART,
        ROOT / "docs" / "guides" / "runes_and_text.md",
        ROOT / "docs" / "tutorials" / "index.md",
        CATALOGUE,
    ],
)
def test_canonical_local_markdown_links_resolve(document: Path) -> None:
    for href in re.findall(r"\[[^\]]+\]\(([^)]+)\)", _read(document)):
        if "://" in href or href.startswith("#"):
            continue
        target = href.split("#", 1)[0]
        if target:
            assert (document.parent / target).resolve().exists(), (
                document.relative_to(ROOT),
                href,
            )
