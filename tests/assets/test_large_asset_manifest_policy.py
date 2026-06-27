from __future__ import annotations

import json
from pathlib import Path

import pytest


pytestmark = pytest.mark.tier_a

ROOT = Path(__file__).resolve().parents[2]


def test_large_asset_manifest_points_to_validated_prerelease_host() -> None:
    manifest = json.loads((ROOT / "assets_manifest_v1.json").read_text(encoding="utf-8"))
    asset_set = manifest["release_asset_sets"]["v1_lm_runtime_full"]

    assert asset_set["release_repository"] == "mortlach/rdp_assets"
    assert asset_set["release_tag"] == "rdp-v1-lm-large-test-20260626"
    assert [item["name"] for item in asset_set["release_assets"]] == [
        "rdp-v1-lm-large-part001.zip",
        "rdp-v1-lm-large-part002.zip",
    ]
    assert all("mortlach/rdp_assets/releases/download/rdp-v1-lm-large-test-20260626" in item["url"] for item in asset_set["release_assets"])


def test_large_asset_manifest_declares_129_runtime_assets_and_64_large_required() -> None:
    manifest = json.loads((ROOT / "assets_manifest_v1.json").read_text(encoding="utf-8"))
    installed = manifest["installed_assets"]

    assert len(installed) == 129
    assert sum(1 for row in installed if "v1_lm_large_required" in row["required_for"]) == 64
