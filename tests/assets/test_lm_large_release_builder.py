from __future__ import annotations
import json
import pathlib
import zipfile
import pytest
from tools.assets.build_lm_large_release_bundle import (
    AssetBuildError,
    build_lm_large_release_bundle,
    derive_expected_lmp_files,
)
from tools.assets.release_asset_installer import load_manifest

pytestmark = pytest.mark.tier_a


def _write_source(root: pathlib.Path) -> None:
    (root / "ecdf" / "char" / "rtl").mkdir(parents=True)
    (root / "wli" / "rtl").mkdir(parents=True)
    with zipfile.ZipFile(
        root / "ecdf" / "char" / "rtl" / "rtl_nose_char_n2_win10_logp.npz", "w"
    ) as archive:
        archive.writestr("array.npy", b"n2")
    with zipfile.ZipFile(
        root / "ecdf" / "char" / "rtl" / "rtl_nose_char_n3_win10_logp.npz", "w"
    ) as archive:
        archive.writestr("array.npy", b"n3")
    (root / "wli" / "rtl" / "wli29_joint_rtl_4_wise.bin.zst").write_bytes(b"n4")
    (root / "wli" / "rtl" / "unused_part00000.npz").write_bytes(b"extra")
    (root / "index.json").write_text(
        json.dumps(
            {
                "models": [
                    "ecdf/char/rtl/rtl_nose_char_n2_win10_logp.npz",
                    "ecdf/char/rtl/rtl_nose_char_n3_win10_logp.npz",
                    "wli/rtl/wli29_joint_rtl_4_wise.bin.zst",
                ]
            }
        ),
        encoding="utf-8",
    )


def test_derive_expected_files_expands_real_index_pattern_shape(
    tmp_path: pathlib.Path,
) -> None:
    for relpath in (
        "index.json",
        "char/ltr/char29_joint_ltr_1_nose.bin.zst",
        "ecdf/char/ltr/ltr_nose_char_n1_win10_logp.npz",
    ):
        path = tmp_path / pathlib.Path(*pathlib.PurePosixPath(relpath).parts)
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.suffix == ".npz":
            with zipfile.ZipFile(path, "w") as archive:
                archive.writestr("array.npy", b"data")
        else:
            path.write_bytes(b"data")
    (tmp_path / "index.json").write_text(
        json.dumps(
            {
                "models": {
                    "char": {
                        "n": [1],
                        "stats": ["logp"],
                        "joint_pattern": "char/%%MODE%%/char29_joint_%%MODE%%_%%N%%_%%POS%%.bin.zst",
                        "ecdf_pattern": "ecdf/char/%%MODE%%/%%MODE%%_%%POS%%_char_n%%N%%_win10_%%STAT%%.npz",
                    }
                }
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(AssetBuildError, match="missing file"):
        derive_expected_lmp_files(tmp_path)


def test_derive_expected_files_uses_root_index_and_excludes_unreferenced_extras(
    tmp_path: pathlib.Path,
) -> None:
    _write_source(tmp_path)
    assert derive_expected_lmp_files(tmp_path) == [
        "ecdf/char/rtl/rtl_nose_char_n2_win10_logp.npz",
        "ecdf/char/rtl/rtl_nose_char_n3_win10_logp.npz",
        "index.json",
        "wli/rtl/wli29_joint_rtl_4_wise.bin.zst",
    ]


def test_builder_writes_manifest_zips_and_sums_without_local_source_paths(
    tmp_path: pathlib.Path,
) -> None:
    source = tmp_path / "source"
    source.mkdir()
    _write_source(source)
    output = tmp_path / "release_build"
    manifest = build_lm_large_release_bundle(source, output, target_part_bytes=3)
    manifest_path = output / "rdp-v1-lm-large-manifest.json"
    manifest_text = manifest_path.read_text(encoding="utf-8")
    assert manifest["schema_version"] == 2
    assert str(source) not in manifest_text
    assert "C:" not in manifest_text
    assert "D:" not in manifest_text
    assert load_manifest(manifest_path)["assets_root"] == "assets"
    assert (output / "rdp-v1-lm-large-SHA256SUMS.txt").is_file()
    assert len(list(output.glob("rdp-v1-lm-large-part*.zip"))) >= 2
    with zipfile.ZipFile(
        sorted(output.glob("rdp-v1-lm-large-part*.zip"))[0]
    ) as archive:
        assert all(
            (name.startswith("language_model/lmp/") for name in archive.namelist())
        )


def test_builder_marks_source_bundled_lm1_lm2_nose_assets_as_ci_light(
    tmp_path: pathlib.Path,
) -> None:
    _write_source(tmp_path)
    manifest = build_lm_large_release_bundle(
        tmp_path, tmp_path / "release_build", target_part_bytes=1024
    )
    ci_rows = [
        row
        for row in manifest["installed_assets"]
        if "v1_lm_ci_light" in row["required_for"]
    ]
    assert (
        manifest["release_asset_sets"]["v1_lm_ci_light"]["bundled_with_source"] is True
    )
    assert {row["final_relpath"] for row in ci_rows} == {
        "language_model/lmp/ecdf/char/rtl/rtl_nose_char_n2_win10_logp.npz",
        "language_model/lmp/index.json",
    }


def test_builder_marks_n3_n4_assets_as_large_required(tmp_path: pathlib.Path) -> None:
    _write_source(tmp_path)
    manifest = build_lm_large_release_bundle(
        tmp_path, tmp_path / "release_build", target_part_bytes=1024
    )
    large_rows = [
        row
        for row in manifest["installed_assets"]
        if "v1_lm_large_required" in row["required_for"]
    ]
    assert {row["final_relpath"] for row in large_rows} == {
        "language_model/lmp/ecdf/char/rtl/rtl_nose_char_n3_win10_logp.npz",
        "language_model/lmp/wli/rtl/wli29_joint_rtl_4_wise.bin.zst",
    }


def test_builder_fails_when_index_references_missing_file(
    tmp_path: pathlib.Path,
) -> None:
    (tmp_path / "index.json").write_text(
        json.dumps({"models": ["missing/file.npz"]}), encoding="utf-8"
    )
    with pytest.raises(AssetBuildError, match="missing file"):
        derive_expected_lmp_files(tmp_path)
