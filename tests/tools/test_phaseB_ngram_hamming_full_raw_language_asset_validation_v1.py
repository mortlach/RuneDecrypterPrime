from __future__ import annotations

import hashlib
import json
from pathlib import Path

from tools.benchmarks.periodic_sub_trans.no_wli.analysis import (
    validate_phaseB_ngram_hamming_full_raw_language_asset_v1 as validate,
)


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def write_asset(tmp_path: Path, *, sample_limit=None, prod_change: bool = False, bad_hash: bool = False) -> Path:
    asset_home = tmp_path / "assets/ngram_hamming/phaseB_full_raw_v1"
    asset_home.mkdir(parents=True)
    (asset_home / "README.md").write_text("# asset\n", encoding="utf-8")
    payload = tmp_path / "payload.csv.gz"
    payload.write_bytes(b"payload\n")
    prov = asset_home / "provenance" / "shard_provenance_manifest.json"
    prov.parent.mkdir(parents=True)
    prov.write_text("{}\n", encoding="utf-8")
    for name in sorted(validate.REQUIRED_PROVENANCE_NAMES - {"shard_provenance_manifest.json"}):
        path = asset_home / "provenance" / name
        path.write_text("col\nvalue\n", encoding="utf-8")
    provenance_files = []
    for path in sorted((asset_home / "provenance").iterdir()):
        provenance_files.append(
            {
                "path": path.relative_to(tmp_path).as_posix(),
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            }
        )
    manifest = {
        "asset_mode": "full",
        "sample_line_limit_per_order": sample_limit,
        "required_orders": [2, 3],
        "required_cuts": ["normal", "strict"],
        "required_directions": ["fwd"],
        "completed_shards": 2,
        "total_shards": 2,
        "missing_shards": 0,
        "failed_shards": 0,
        "missing_output_files": 0,
        "missing_required_output_combos": 0,
        "phrase_length_distribution_rows": 1,
        "word_length_distribution_rows": 1,
        "files": [
            {
                "path": "payload.csv.gz",
                "sha256": "0" * 64 if bad_hash else sha256_text("payload\n"),
            }
        ],
        "provenance_files": provenance_files,
        "no_production_scorer_change": not prod_change,
        "lane2_launch_authority": "not_granted_by_this_asset",
    }
    (asset_home / "asset_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return asset_home


def test_asset_validator_passes_minimal_valid_asset(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(validate, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(validate, "EXPECTED_TOTAL_SHARDS", 2)
    asset_home = write_asset(tmp_path)

    manifest = validate.validate_language_asset(asset_home=asset_home, output_dir=tmp_path / "out")

    assert manifest["status"] == "pass"
    assert manifest["hash_failures"] == 0
    assert manifest["missing_files"] == 0


def test_asset_validator_blocks_hash_mismatch(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(validate, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(validate, "EXPECTED_TOTAL_SHARDS", 2)
    asset_home = write_asset(tmp_path, bad_hash=True)

    manifest = validate.validate_language_asset(asset_home=asset_home, output_dir=tmp_path / "out")

    assert manifest["status"] == "blocked"
    assert manifest["hash_failures"] == 1


def test_asset_validator_blocks_missing_listed_file(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(validate, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(validate, "EXPECTED_TOTAL_SHARDS", 2)
    asset_home = write_asset(tmp_path)
    (tmp_path / "payload.csv.gz").unlink()

    manifest = validate.validate_language_asset(asset_home=asset_home, output_dir=tmp_path / "out")

    assert manifest["status"] == "blocked"
    assert manifest["missing_files"] == 1


def test_asset_validator_blocks_sample_mode_and_production_change(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(validate, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(validate, "EXPECTED_TOTAL_SHARDS", 2)
    asset_home = write_asset(tmp_path, sample_limit=10, prod_change=True)

    manifest = validate.validate_language_asset(asset_home=asset_home, output_dir=tmp_path / "out")

    assert manifest["status"] == "blocked"
    assert "sample_line_limit_per_order is not null" in manifest["blocked_reasons"]
    assert "no_production_scorer_change is not true" in manifest["blocked_reasons"]
