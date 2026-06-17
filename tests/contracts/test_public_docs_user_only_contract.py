from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DOCS = ROOT / "docs"

BANNED_PUBLIC_DOC_PATHS = [
    "archive",
    "architecture",
    "appendices",
    "howto",
    "reference",
    "release_contracts",
    "repo",
    "tests",
    "tests_docs",
    "user",
    "v1_traceability",
]

BANNED_PUBLIC_DOC_FILES = [
    "DOCS_CLEANUP_PLAN.md",
    "DOCS_INVENTORY_REVIEW.md",
    "DOCS_STAGE1_DECISIONS.md",
    "DOCS_STAGE2_FULL_REFRESH_MATRIX.md",
    "DOCS_NEXT_LOCAL_ACTIONS.md",
    "DOCS_CLEANUP_SUMMARY.md",
    "DOCS_FINAL_CROSSCHECK.md",
    "INDEX.md",
]


def test_public_docs_tree_is_user_and_expert_focused() -> None:
    assert DOCS.is_dir()

    for rel in BANNED_PUBLIC_DOC_PATHS:
        assert not (DOCS / rel).exists(), f"non-user docs path remains public: docs/{rel}"

    for rel in BANNED_PUBLIC_DOC_FILES:
        assert not (DOCS / rel).exists(), f"non-user docs file remains public: docs/{rel}"


def test_public_docs_entrypoints_exist() -> None:
    required = [
        "README.md",
        "FAQ.md",
        "glossary.md",
        "setup/installation.md",
        "guides/quickstart.md",
        "guides/first_real_solve.md",
        "guides/using_rdp.md",
        "guides/features.md",
        "guides/common_run_options.md",
        "guides/tutorial_catalogue.md",
        "guides/examples.md",
        "guides/troubleshooting.md",
        "guides/outputs.md",
        "guides/liber_primus_solved_sources.md",
        "tutorials/index.md",
        "expert/README.md",
        "expert/design_philosophy.md",
        "expert/component_model.md",
        "expert/contracts_overview.md",
        "expert/gui_frontend_interfaces.md",
        "expert/gui_interface_contract.md",
        "expert/stability_surface.md",
        "expert/plugin_design.md",
        "expert/reports_and_artifacts.md",
        "expert/source_and_tutorial_interfaces.md",
    ]

    for rel in required:
        assert (DOCS / rel).is_file(), f"missing user/expert doc: docs/{rel}"


def test_docs_readme_does_not_link_internal_lanes() -> None:
    text = (DOCS / "README.md").read_text(encoding="utf-8").lower()

    banned = [
        "release_contracts",
        "d-stage",
        "d0",
        "d1",
        "d2",
        "d3",
        "d4",
        "d5",
        "d6",
        "d7",
        "pull request",
        "implementation handoff",
        "docs cleanup",
    ]

    for needle in banned:
        assert needle not in text, f"internal wording leaked into docs/README.md: {needle!r}"


def test_public_docs_do_not_contain_local_or_review_pack_paths() -> None:
    forbidden = [
        "/mnt/" + "data",
        "review_pack__",
        "review-pack",
    ]

    for path in DOCS.rglob("*.md"):
        text = path.read_text(encoding="utf-8", errors="replace").lower()
        for needle in forbidden:
            assert needle not in text, f"{needle!r} leaked into {path.relative_to(ROOT)}"
