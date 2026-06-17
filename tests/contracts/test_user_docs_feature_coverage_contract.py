from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DOCS = ROOT / "docs"
MANIFEST = ROOT / "tutorials" / "v1" / "tutorial_manifest_v1.json"


def _manifest() -> dict:
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def _all_user_doc_text() -> str:
    parts = []
    for path in sorted(DOCS.rglob("*.md")):
        parts.append(path.read_text(encoding="utf-8", errors="replace"))
    return "\n".join(parts).lower()


def test_user_docs_cover_manifest_gate_and_asset_terms() -> None:
    manifest = _manifest()
    text = _all_user_doc_text()

    for gate in manifest.get("gate_definitions", {}).keys():
        assert gate.lower() in text, f"manifest gate missing from user docs: {gate}"

    for profile in manifest.get("asset_profiles", {}).keys():
        assert profile.lower() in text, f"manifest asset profile missing from user docs: {profile}"


def test_user_docs_cover_manifest_cipher_families() -> None:
    manifest = _manifest()
    text = _all_user_doc_text()

    for tutorial in manifest.get("tutorials", []):
        family = tutorial.get("cipher_family")
        if family:
            first_word = str(family).replace("_", " ").lower().split()[0]
            assert first_word in text, f"manifest family missing from user docs: {family}"


def test_tutorial_catalogue_mentions_active_optional_and_blocked() -> None:
    text = (DOCS / "guides" / "tutorial_catalogue.md").read_text(encoding="utf-8").lower()

    for needle in ["active", "optional", "blocked", "manifest", "gate", "asset"]:
        assert needle in text
