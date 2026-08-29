from pathlib import Path
import tomllib
import pytest

pytestmark = pytest.mark.tier_a
ROOT = Path(__file__).resolve().parents[2]
BLOCKED = (
    "rune_decrypter_prime.ciphers.dev",
    "rune_decrypter_prime.keyops.dev",
    "rune_decrypter_prime.data.liber_primus.old",
)


def test_pyproject_declares_clean_runtime_dependency_and_package_exclusions():
    data = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    deps = data["project"]["dependencies"]
    assert any((dep.split(">=", 1)[0].strip().lower() == "lark" for dep in deps))
    excluded = tuple(data["tool"]["setuptools"]["packages"]["find"]["exclude"])
    for prefix in BLOCKED:
        assert prefix in excluded
        assert prefix + ".*" in excluded


def test_setup_uses_exact_ci_light_asset_allowlist_for_wheel_and_sdist():
    setup_text = (ROOT / "setup.py").read_text(encoding="utf-8")
    assert "exclude=_PACKAGE_EXCLUDES" in setup_text
    assert "assets_manifest_ci_light_v1.json" in setup_text
    assert "class A5BuildPy" in setup_text
    assert "class A5Sdist" in setup_text
    assert (
        "make_release_tree"
        in setup_text.split("class A5Sdist", 1)[1].split("lm_dir", 1)[0]
    )


def test_manifest_does_not_glob_local_asset_tree_and_mirrors_code_boundary():
    manifest = (ROOT / "MANIFEST.in").read_text(encoding="utf-8")
    assert "recursive-include assets" not in manifest
    assert "include assets_manifest_ci_light_v1.json" in manifest
    for fragment in ("ciphers/dev", "keyops/dev", "data/liber_primus/old"):
        assert f"prune src/rune_decrypter_prime/{fragment}" in manifest


def test_support_claims_are_limited_to_qualified_gate():
    data = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    classifiers = set(data["project"]["classifiers"])
    assert "Programming Language :: Python :: 3.11" in classifiers
    assert "Operating System :: Microsoft :: Windows" in classifiers
    assert "Operating System :: POSIX :: Linux" in classifiers
    assert "Operating System :: OS Independent" not in classifiers
