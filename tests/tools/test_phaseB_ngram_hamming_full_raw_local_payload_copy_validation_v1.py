from __future__ import annotations

import hashlib
import json
from pathlib import Path

from tools.benchmarks.periodic_sub_trans.no_wli.analysis import (
    validate_phaseB_ngram_hamming_full_raw_local_payload_copy_v1 as validate,
)


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def write_manifest(
    root: Path,
    *,
    missing: bool = False,
    bad_hash: bool = False,
    bad_bytes: bool = False,
    bad_path: bool = False,
) -> None:
    asset_home = root / "assets/ngram_hamming/phaseB_full_raw_v1"
    asset_home.mkdir(parents=True)
    files = []
    for order in (2, 3):
        for cut in ("normal", "strict"):
            rel_path = (
                "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
                f"phaseB_ngram_hamming_full_raw_asset_shards_v1/order_{order}/{cut}_fwd/ngram{order}.csv.gz"
            )
            if bad_path and order == 2 and cut == "normal":
                rel_path = rel_path.replace("/", "\\")
            payload = f"{order}-{cut}\n".encode("utf-8")
            path = root / rel_path
            if not missing or not (order == 3 and cut == "strict"):
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(payload)
            files.append(
                {
                    "role": "shard_payload",
                    "path": rel_path,
                    "bytes": len(payload) + (1 if bad_bytes and order == 2 and cut == "strict" else 0),
                    "sha256": "0" * 64 if bad_hash and order == 3 and cut == "normal" else sha256_bytes(payload),
                    "ngram_order": order,
                    "dictionary_cut": cut,
                    "direction": "fwd",
                    "aggregate_rows": 1,
                }
            )
    manifest = {
        "asset_id": "phaseB_ngram_hamming_full_raw_v1",
        "files": files,
    }
    (asset_home / "asset_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


def test_local_payload_copy_validation_passes_complete_payload(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(validate, "REPO_ROOT", tmp_path)
    write_manifest(tmp_path)

    manifest = validate.validate_payload_copy(output_dir=tmp_path / "out")

    assert manifest["status"] == "pass"
    assert manifest["payload_files_expected"] == 4
    assert manifest["payload_files_checked"] == 4
    assert manifest["missing_files"] == 0
    assert manifest["hash_mismatches"] == 0
    assert manifest["byte_count_mismatches"] == 0


def test_local_payload_copy_validation_blocks_missing_payload(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(validate, "REPO_ROOT", tmp_path)
    write_manifest(tmp_path, missing=True)

    manifest = validate.validate_payload_copy(output_dir=tmp_path / "out")

    assert manifest["status"] == "blocked"
    assert manifest["missing_files"] == 1


def test_local_payload_copy_validation_blocks_hash_mismatch(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(validate, "REPO_ROOT", tmp_path)
    write_manifest(tmp_path, bad_hash=True)

    manifest = validate.validate_payload_copy(output_dir=tmp_path / "out")

    assert manifest["status"] == "blocked"
    assert manifest["hash_mismatches"] == 1


def test_local_payload_copy_validation_blocks_byte_mismatch(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(validate, "REPO_ROOT", tmp_path)
    write_manifest(tmp_path, bad_bytes=True)

    manifest = validate.validate_payload_copy(output_dir=tmp_path / "out")

    assert manifest["status"] == "blocked"
    assert manifest["byte_count_mismatches"] == 1


def test_local_payload_copy_validation_blocks_bad_manifest_path(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(validate, "REPO_ROOT", tmp_path)
    write_manifest(tmp_path, bad_path=True)

    manifest = validate.validate_payload_copy(output_dir=tmp_path / "out")

    assert manifest["status"] == "blocked"
    assert manifest["bad_manifest_paths"] == 1
