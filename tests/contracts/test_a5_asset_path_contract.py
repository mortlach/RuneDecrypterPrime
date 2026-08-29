import pytest
from rune_decrypter_prime.data import asset_paths

pytestmark = pytest.mark.tier_a


def test_source_checkout_assets_have_precedence(monkeypatch, tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "pyproject.toml").write_text("[project]\nname='x'\n", encoding="utf-8")
    (repo / "assets").mkdir()
    package_data = tmp_path / "site" / "rune_decrypter_prime" / "data"
    package_data.mkdir(parents=True)
    package_assets = package_data / "assets"
    package_assets.mkdir()
    package_manifest = package_data / "assets_manifest_ci_light_v1.json"
    package_manifest.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(asset_paths, "_PACKAGE_DATA_ROOT", package_data)
    monkeypatch.setattr(asset_paths, "_PACKAGE_ASSETS_ROOT", package_assets)
    monkeypatch.setattr(asset_paths, "_PACKAGE_CI_MANIFEST", package_manifest)
    assert (
        asset_paths.find_assets_root(repo / "src" / "anything.py")
        == (repo / "assets").resolve()
    )


def test_installed_package_uses_staged_assets_not_data_or_cwd(monkeypatch, tmp_path):
    package_data = tmp_path / "site" / "rune_decrypter_prime" / "data"
    package_data.mkdir(parents=True)
    package_assets = package_data / "assets"
    package_assets.mkdir()
    package_manifest = package_data / "assets_manifest_ci_light_v1.json"
    package_manifest.write_text("{}", encoding="utf-8")
    fake_origin = tmp_path / "isolated" / "probe.py"
    fake_origin.parent.mkdir()
    fake_origin.write_text("", encoding="utf-8")
    unrelated = tmp_path / "cwd"
    unrelated.mkdir()
    (unrelated / "assets").mkdir()
    monkeypatch.chdir(unrelated)
    monkeypatch.setattr(asset_paths, "_PACKAGE_DATA_ROOT", package_data)
    monkeypatch.setattr(asset_paths, "_PACKAGE_ASSETS_ROOT", package_assets)
    monkeypatch.setattr(asset_paths, "_PACKAGE_CI_MANIFEST", package_manifest)
    assert asset_paths.find_assets_root(fake_origin) == package_assets.resolve()


def test_empty_package_data_directory_is_not_an_asset_root(monkeypatch, tmp_path):
    package_data = tmp_path / "site" / "rune_decrypter_prime" / "data"
    package_data.mkdir(parents=True)
    fake_origin = tmp_path / "isolated" / "probe.py"
    fake_origin.parent.mkdir()
    fake_origin.write_text("", encoding="utf-8")
    monkeypatch.setattr(asset_paths, "_PACKAGE_DATA_ROOT", package_data)
    monkeypatch.setattr(asset_paths, "_PACKAGE_ASSETS_ROOT", package_data / "assets")
    monkeypatch.setattr(
        asset_paths,
        "_PACKAGE_CI_MANIFEST",
        package_data / "assets_manifest_ci_light_v1.json",
    )
    with pytest.raises(FileNotFoundError, match="No RDP asset root"):
        asset_paths.find_assets_root(fake_origin)


def test_external_display_path_does_not_leak_absolute_path(tmp_path):
    shown = asset_paths.to_repo_relative(tmp_path / "private" / "model.bin")
    assert shown == "<external:model.bin>"
    assert str(tmp_path.resolve()) not in shown
