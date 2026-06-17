from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DOCS = ROOT / "docs"
EXPERT = DOCS / "expert"


def test_expert_docs_exist() -> None:
    required = [
        "README.md",
        "design_philosophy.md",
        "component_model.md",
        "contracts_overview.md",
        "gui_frontend_interfaces.md",
        "gui_interface_contract.md",
        "stability_surface.md",
        "plugin_design.md",
        "reports_and_artifacts.md",
        "source_and_tutorial_interfaces.md",
    ]

    for rel in required:
        assert (EXPERT / rel).is_file(), f"missing expert doc: docs/expert/{rel}"


def test_expert_docs_cover_gui_plugin_and_stability_surfaces() -> None:
    expected_terms = {
        "README.md": ["GUI", "front-end", "stable"],
        "design_philosophy.md": ["Repeatability", "Inspectability", "Reports"],
        "component_model.md": ["Source", "Cipher", "Solver", "Scorer", "Report"],
        "contracts_overview.md": ["Tutorial manifest", "Stop reason", "Oracle"],
        "gui_frontend_interfaces.md": ["tutorial_manifest_v1.json", "structured", "console"],
        "gui_interface_contract.md": ["tutorial_id", "asset_profile", "warnings"],
        "stability_surface.md": ["Stable user-facing concepts", "Not stable"],
        "plugin_design.md": ["Cipher", "Solver", "Scorer", "metadata"],
        "reports_and_artifacts.md": ["output/", "telemetry", "warnings"],
        "source_and_tutorial_interfaces.md": ["Source", "tutorials/v1/", "gate"],
    }

    for rel, terms in expected_terms.items():
        text = (EXPERT / rel).read_text(encoding="utf-8")
        for term in terms:
            assert term in text, f"{term!r} missing from docs/expert/{rel}"


def test_top_level_docs_link_expert_path() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    docs_readme = (DOCS / "README.md").read_text(encoding="utf-8")
    faq = (DOCS / "FAQ.md").read_text(encoding="utf-8")

    for text_name, text in [("README.md", readme), ("docs/README.md", docs_readme), ("docs/FAQ.md", faq)]:
        assert "docs/expert/README.md" in text or "expert/README.md" in text, (
            f"expert docs not linked from {text_name}"
        )
