"""Contracts for the canonical V1 reader route and example catalogue."""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.tier_a
ROOT = Path(__file__).resolve().parents[2]
README = ROOT / "README.md"
QUICKSTART = ROOT / "docs" / "guides" / "quickstart.md"
RUN_ANATOMY = ROOT / "docs" / "guides" / "anatomy_of_a_run.md"
CATALOGUE = ROOT / "tutorials" / "v1" / "README.md"
ROADMAP = ROOT / "docs" / "project_overview.md"
EXAMPLES = ROOT / "tutorials" / "v1" / "examples"
ROUTE = ROOT / "tutorials" / "v1" / "getting_started"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_root_readme_uses_the_public_api_and_reader_route() -> None:
    text = _read(README)
    assert "from rdp import api" in text
    for path in (
        "docs/guides/quickstart.md",
        "docs/guides/anatomy_of_a_run.md",
        "docs/guides/ciphertext_input.md",
        "docs/tutorials/README.md",
    ):
        assert path in text


def test_quickstart_python_fences_execute_as_documented() -> None:
    blocks = re.findall(
        r'^```python\s*\n(.*?)^```\s*$',
        _read(QUICKSTART),
        re.MULTILINE | re.DOTALL,
    )
    assert blocks
    code = '\n\n'.join(blocks)
    completed = subprocess.run(
        [sys.executable, '-B', '-X', 'utf8', '-c', code],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding='utf-8',
        timeout=180,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr


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


def test_canonical_docs_do_not_restore_retired_taxonomy_or_prohibited_tone() -> None:
    paths = (
        README,
        ROOT / "docs" / "README.md",
        ROOT / "docs" / "setup" / "installation.md",
        ROOT / "docs" / "setup" / "building.md",
        ROOT / "docs" / "setup" / "README.md",
        ROOT / "docs" / "guides" / "using_rdp.md",
        QUICKSTART,
        RUN_ANATOMY,
        ROOT / "docs" / "guides" / "ciphertext_input.md",
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
        RUN_ANATOMY,
        ROOT / "docs" / "guides" / "ciphertext_input.md",
        ROOT / "docs" / "tutorials" / "README.md",
        CATALOGUE,
        ROUTE / "README.md",
        EXAMPLES / "README.md",
        ROOT / "docs/setup/building.md",
        ROOT / "docs/setup/README.md",
        ROOT / "docs/guides/using_rdp.md",
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


def test_using_rdp_explains_editable_and_native_boundaries() -> None:
    text = _read(ROOT / "docs/guides/using_rdp.md")
    for term in ("python -m pip install -e .", "new Python process", "Restart",
                 "rebuild", "dependency metadata", "--all", "--only 01 07 10",
                 "CicadaSolvers", "does not ship a public browser front end"):
        assert term in text
    assert "working source checkout" in text
