from __future__ import annotations

import csv
import json
from pathlib import Path

import numpy as np

from tools.benchmarks.periodic_sub_trans.no_wli.analysis import (
    build_phaseB_ngram_hamming_fast_runtime_lookup_index_v1 as runtime_build,
)
from tools.benchmarks.periodic_sub_trans.no_wli.analysis import (
    build_phaseB_ngram_hamming_full_raw_compact_phrase_lookup_asset_v1 as compact_build,
)
from tools.benchmarks.periodic_sub_trans.no_wli.analysis import (
    validate_phaseB_ngram_hamming_fast_runtime_lookup_index_v1 as runtime_validate,
)
from tools.benchmarks.periodic_sub_trans.no_wli.analysis import (
    validate_phaseB_ngram_hamming_full_raw_compact_phrase_lookup_asset_v1 as compact_validate,
)

from tests.tools.test_phaseB_ngram_hamming_full_raw_compact_phrase_lookup_asset_v1 import seed_source


def seed_compact_asset(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(compact_build, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(compact_validate, "REPO_ROOT", tmp_path)
    seed_source(tmp_path)
    compact_build.build_compact_lookup_asset(output_dir=tmp_path / compact_validate.COMPACT_ASSET_DIR_REL)
    compact_validate.validate_compact_lookup_asset(output_dir=tmp_path / compact_validate.OUTPUT_DIR_REL)


def runtime_out_dir(tmp_path: Path) -> Path:
    return tmp_path / runtime_validate.RUNTIME_INDEX_DIR_REL


def runtime_validation_out_dir(tmp_path: Path) -> Path:
    return tmp_path / "runtime_validation_out"


def read_failures(path: Path) -> list[dict[str, str]]:
    with (path / "validation_failure_rows.csv").open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def test_fast_runtime_index_builder_groups_by_length_and_word_shape(tmp_path: Path, monkeypatch) -> None:
    seed_compact_asset(tmp_path, monkeypatch)
    monkeypatch.setattr(runtime_build, "REPO_ROOT", tmp_path)

    manifest = runtime_build.build_fast_runtime_lookup_index(output_dir=runtime_out_dir(tmp_path))

    assert manifest["asset_status"] == "built"
    assert manifest["runtime_format"] == runtime_build.RUNTIME_FORMAT
    assert manifest["production_scorer_change"] is False
    assert manifest["counts_are_diagnostic_only"] is True
    assert manifest["phrase_rows_indexed"] == 2
    assert manifest["group_count"] == 2
    metadata = json.loads((tmp_path / runtime_build.ASSET_META_DIR_REL / "asset_manifest.json").read_text(encoding="utf-8"))
    assert metadata["payload_storage_mode"] == "local_output_payload_due_large_size"
    assert metadata["payload_manifest"].endswith("runtime_index_manifest.json")
    assert (tmp_path / runtime_build.ASSET_META_DIR_REL / "README.md").exists()
    for file_row in manifest["files"]:
        path = tmp_path / file_row["path"]
        with np.load(path, allow_pickle=False) as data:
            assert data["rune_tokens"].shape[0] == file_row["phrase_count"]
            assert data["rune_tokens"].shape[1] == file_row["phrase_token_length"]
            assert tuple(data["word_token_lengths"].tolist()) == tuple(json.loads(file_row["word_token_lengths"]))


def test_fast_runtime_index_builder_blocks_without_compact_validation_pass(tmp_path: Path, monkeypatch) -> None:
    seed_compact_asset(tmp_path, monkeypatch)
    monkeypatch.setattr(runtime_build, "REPO_ROOT", tmp_path)
    validation_path = tmp_path / runtime_build.COMPACT_VALIDATION_MANIFEST_REL
    validation = json.loads(validation_path.read_text(encoding="utf-8"))
    validation["status"] = "blocked"
    validation_path.write_text(json.dumps(validation) + "\n", encoding="utf-8")

    manifest = runtime_build.build_fast_runtime_lookup_index(output_dir=runtime_out_dir(tmp_path))

    assert manifest["asset_status"] == "blocked"
    assert "compact validation status is not pass" in manifest["blocked_reasons"]


def test_fast_runtime_validator_passes_builder_output(tmp_path: Path, monkeypatch) -> None:
    seed_compact_asset(tmp_path, monkeypatch)
    monkeypatch.setattr(runtime_build, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(runtime_validate, "REPO_ROOT", tmp_path)
    runtime_build.build_fast_runtime_lookup_index(output_dir=runtime_out_dir(tmp_path))

    validation = runtime_validate.validate_fast_runtime_lookup_index(output_dir=runtime_validation_out_dir(tmp_path))

    assert validation["status"] == "pass"
    assert validation["failure_count"] == 0
    assert validation["phrase_rows_indexed"] == 2


def test_fast_runtime_validator_blocks_mixed_cut_in_group(tmp_path: Path, monkeypatch) -> None:
    seed_compact_asset(tmp_path, monkeypatch)
    monkeypatch.setattr(runtime_build, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(runtime_validate, "REPO_ROOT", tmp_path)
    manifest = runtime_build.build_fast_runtime_lookup_index(output_dir=runtime_out_dir(tmp_path))
    target = tmp_path / manifest["files"][0]["path"]
    with np.load(target, allow_pickle=False) as data:
        arrays = {name: data[name] for name in data.files}
    arrays["dictionary_cut"] = np.asarray(["normal", "strict"], dtype=np.str_)
    np.savez_compressed(target, **arrays)

    validation = runtime_validate.validate_fast_runtime_lookup_index(output_dir=runtime_validation_out_dir(tmp_path))
    failures = read_failures(runtime_validation_out_dir(tmp_path))

    assert validation["status"] == "blocked"
    assert any(row["reason"] == "runtime npz byte count mismatch" for row in failures)
    assert any(row["reason"] == "runtime group mixes dictionary_cut" for row in failures)


def test_fast_runtime_validator_blocks_mixed_order_and_row_count_mismatch(tmp_path: Path, monkeypatch) -> None:
    seed_compact_asset(tmp_path, monkeypatch)
    monkeypatch.setattr(runtime_build, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(runtime_validate, "REPO_ROOT", tmp_path)
    manifest = runtime_build.build_fast_runtime_lookup_index(output_dir=runtime_out_dir(tmp_path))
    target = tmp_path / manifest["files"][0]["path"]
    with np.load(target, allow_pickle=False) as data:
        arrays = {name: data[name] for name in data.files}
    arrays["ngram_order"] = np.asarray([2, 3], dtype=np.int16)
    arrays["rune_tokens"] = np.vstack([arrays["rune_tokens"], arrays["rune_tokens"][0]])
    np.savez_compressed(target, **arrays)

    validation = runtime_validate.validate_fast_runtime_lookup_index(output_dir=runtime_validation_out_dir(tmp_path))
    failures = read_failures(runtime_validation_out_dir(tmp_path))

    assert validation["status"] == "blocked"
    reasons = {row["reason"] for row in failures}
    assert "runtime group mixes ngram_order" in reasons
    assert "array row count does not match listed phrase count" in reasons
