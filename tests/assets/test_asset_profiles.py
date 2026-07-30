from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools.assets.asset_profiles import (
    AssetProfileError,
    load_asset_profiles,
    select_asset_profile,
)
from tools.assets.release_asset_installer import load_manifest


ROOT = Path(__file__).resolve().parents[2]
PROFILE_MANIFEST = ROOT / "asset_profiles_v1.json"
RELEASE_MANIFEST = ROOT / "assets_manifest_v1.json"
CI_MANIFEST = ROOT / "assets_manifest_ci_light_v1.json"

pytestmark = pytest.mark.tier_a


def test_canonical_asset_profiles_are_exact_and_default_to_full_v1() -> None:
    default, profiles = load_asset_profiles(PROFILE_MANIFEST)

    assert default == "full_v1"
    assert tuple(profiles) == ("ci_light", "full_v1")
    assert profiles["ci_light"].language_model_orders == (1, 2)
    assert profiles["ci_light"].download_release_assets is False
    assert profiles["ci_light"].pytest_marker_expression == "not full_assets"
    assert profiles["full_v1"].language_model_orders == (1, 2, 3, 4)
    assert profiles["full_v1"].download_release_assets is True
    assert profiles["full_v1"].pytest_marker_expression is None


def test_profile_asset_sets_exist_and_full_v1_uses_github_release_assets() -> None:
    _default, profiles = load_asset_profiles(PROFILE_MANIFEST)
    release = load_manifest(RELEASE_MANIFEST)
    ci = load_manifest(CI_MANIFEST)

    assert profiles["ci_light"].verification_manifest == CI_MANIFEST.name
    assert profiles["full_v1"].verification_manifest == RELEASE_MANIFEST.name
    assert profiles["ci_light"].release_asset_set in ci["release_asset_sets"]
    assert profiles["full_v1"].release_asset_set in release["release_asset_sets"]
    assert ci["release_asset_sets"]["v1_lm_ci_light"]["bundled_with_source"] is True
    full = release["release_asset_sets"]["v1_lm_runtime_full"]
    assert full["release_repository"] == "mortlach/rdp_assets"
    assert full["release_tag"] == "rdp-v1.0.0-lm-large"
    assert full["release_assets"]
    assert all(
        item["url"].startswith(
            "https://github.com/mortlach/rdp_assets/releases/download/"
        )
        for item in full["release_assets"]
    )


def test_ci_light_manifest_rows_are_source_bundled_and_hash_exact() -> None:
    release = load_manifest(CI_MANIFEST)
    rows = [
        row
        for row in release["installed_assets"]
        if "v1_lm_ci_light" in row["required_for"]
    ]

    assert len(rows) == 33
    assert any(row["final_relpath"].endswith("index.json") for row in rows)
    assert not any("_n3_" in row["final_relpath"] or "_n4_" in row["final_relpath"] for row in rows)
    from tools.assets.release_asset_installer import verify_installed_assets

    verify_installed_assets(release, "v1_lm_ci_light", ROOT / "assets")


def test_unknown_or_malformed_profile_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(AssetProfileError, match="unknown asset profile"):
        select_asset_profile(PROFILE_MANIFEST, "not_a_profile")

    raw = json.loads(PROFILE_MANIFEST.read_text(encoding="utf-8"))
    raw["profiles"]["ci_light"]["language_model_orders"] = [2, 1]
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps(raw), encoding="utf-8")
    with pytest.raises(AssetProfileError, match="unique sorted orders"):
        load_asset_profiles(bad)

    raw = json.loads(PROFILE_MANIFEST.read_text(encoding="utf-8"))
    raw["profiles"]["ci_light"]["verification_manifest"] = "../outside.json"
    bad.write_text(json.dumps(raw), encoding="utf-8")
    with pytest.raises(AssetProfileError, match="safe repository-relative path"):
        load_asset_profiles(bad)
