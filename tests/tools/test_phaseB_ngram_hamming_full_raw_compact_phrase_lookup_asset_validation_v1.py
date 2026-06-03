from __future__ import annotations

import csv
import gzip
import json
from pathlib import Path

from tools.benchmarks.periodic_sub_trans.no_wli.analysis import (
    build_phaseB_ngram_hamming_full_raw_compact_phrase_lookup_asset_v1 as build,
)
from tools.benchmarks.periodic_sub_trans.no_wli.analysis import (
    validate_phaseB_ngram_hamming_full_raw_compact_phrase_lookup_asset_v1 as validate,
)

from tests.tools.test_phaseB_ngram_hamming_full_raw_compact_phrase_lookup_asset_v1 import seed_source


COMPACT_FIELDS = (
    "phrase_id",
    "direction",
    "dictionary_cut",
    "ngram_order",
    "word_token_tuple",
    "rune_token_tuple",
    "phrase_token_length",
    "word_token_lengths",
    "word_count",
    "source_row_count",
    "duplicate_row_count",
    "sum_count",
    "max_count",
    "sum_log_count",
    "max_log_count",
    "source_file_count",
    "identity_sha256",
)


def compact_manifest_dir(tmp_path: Path) -> Path:
    return tmp_path / validate.COMPACT_ASSET_DIR_REL


def validation_out_dir(tmp_path: Path) -> Path:
    return tmp_path / "validation_out"


def read_failures(path: Path) -> list[dict[str, str]]:
    with (path / "validation_failure_rows.csv").open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def compact_row(
    *,
    phrase_id: str,
    word_token_tuple: str,
    rune_token_tuple: str,
    identity_sha256: str,
    phrase_token_length: int = 2,
) -> dict[str, object]:
    return {
        "phrase_id": phrase_id,
        "direction": "fwd",
        "dictionary_cut": "normal",
        "ngram_order": 2,
        "word_token_tuple": word_token_tuple,
        "rune_token_tuple": rune_token_tuple,
        "phrase_token_length": phrase_token_length,
        "word_token_lengths": "[1,1]",
        "word_count": 2,
        "source_row_count": 1,
        "duplicate_row_count": 0,
        "sum_count": 1.0,
        "max_count": 1.0,
        "sum_log_count": 0.5,
        "max_log_count": 0.5,
        "source_file_count": 1,
        "identity_sha256": identity_sha256,
    }


def write_compact_fixture(tmp_path: Path, rows: list[dict[str, object]], manifest_updates: dict[str, object] | None = None) -> Path:
    compact_rel = (
        f"{validate.COMPACT_ASSET_DIR_REL}/compact_rows/direction=fwd/order=2/cut=normal/"
        "phrase_lookup_rows.csv.gz"
    )
    compact_path = tmp_path / compact_rel
    compact_path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(compact_path, "wt", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(COMPACT_FIELDS))
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in COMPACT_FIELDS})
    manifest = {
        "asset_id": validate.EXPECTED_ASSET_ID,
        "source_asset_id": validate.EXPECTED_SOURCE_ASSET_ID,
        "source_asset_mode": "full",
        "source_payload_validation_status": "pass",
        "orders": validate.EXPECTED_ORDERS,
        "cuts": validate.EXPECTED_CUTS,
        "directions": validate.EXPECTED_DIRECTIONS,
        "normal_strict_separate": True,
        "counts_are_diagnostic_only": True,
        "log_counts_are_diagnostic_only": True,
        "sample_asset_used": False,
        "old_phrase_index_v1_used": False,
        "files": [
            {
                "path": compact_rel,
                "role": "compact_phrase_lookup_rows",
                "direction": "fwd",
                "ngram_order": 2,
                "dictionary_cut": "normal",
                "bytes": compact_path.stat().st_size,
                "sha256": validate.sha256_file(compact_path),
            }
        ],
    }
    manifest.update(manifest_updates or {})
    manifest_path = tmp_path / validate.COMPACT_MANIFEST_REL
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return compact_path


def test_compact_validator_passes_builder_synthetic_output(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(build, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(validate, "REPO_ROOT", tmp_path)
    seed_source(tmp_path)
    build.build_compact_lookup_asset(output_dir=compact_manifest_dir(tmp_path))

    validation = validate.validate_compact_lookup_asset(output_dir=validation_out_dir(tmp_path))

    assert validation["status"] == "pass"
    assert validation["failure_count"] == 0
    assert validation["compact_rows_checked"] == 2


def test_compact_validator_blocks_duplicate_phrase_id(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(validate, "REPO_ROOT", tmp_path)
    write_compact_fixture(
        tmp_path,
        [
            compact_row(phrase_id="phrase_a", word_token_tuple="[[1],[2]]", rune_token_tuple="[1,2]", identity_sha256="a"),
            compact_row(phrase_id="phrase_a", word_token_tuple="[[1],[3]]", rune_token_tuple="[1,3]", identity_sha256="b"),
        ],
    )

    validation = validate.validate_compact_lookup_asset(output_dir=validation_out_dir(tmp_path))
    failures = read_failures(validation_out_dir(tmp_path))

    assert validation["status"] == "blocked"
    assert any(row["reason"] == "duplicate phrase_id" for row in failures)


def test_compact_validator_blocks_duplicate_canonical_identity(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(validate, "REPO_ROOT", tmp_path)
    write_compact_fixture(
        tmp_path,
        [
            compact_row(phrase_id="phrase_a", word_token_tuple="[[1],[2]]", rune_token_tuple="[1,2]", identity_sha256="a"),
            compact_row(phrase_id="phrase_b", word_token_tuple="[[1],[2]]", rune_token_tuple="[1,2]", identity_sha256="b"),
        ],
    )

    validation = validate.validate_compact_lookup_asset(output_dir=validation_out_dir(tmp_path))
    failures = read_failures(validation_out_dir(tmp_path))

    assert validation["status"] == "blocked"
    assert any(row["reason"] == "duplicate canonical identity" for row in failures)


def test_compact_validator_blocks_unsorted_rows(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(validate, "REPO_ROOT", tmp_path)
    write_compact_fixture(
        tmp_path,
        [
            compact_row(phrase_id="phrase_b", word_token_tuple="[[2],[3]]", rune_token_tuple="[2,3]", identity_sha256="b", phrase_token_length=3),
            compact_row(phrase_id="phrase_a", word_token_tuple="[[1],[2]]", rune_token_tuple="[1,2]", identity_sha256="a", phrase_token_length=2),
        ],
    )

    validation = validate.validate_compact_lookup_asset(output_dir=validation_out_dir(tmp_path))
    failures = read_failures(validation_out_dir(tmp_path))

    assert validation["status"] == "blocked"
    assert any(row["reason"] == "rows are not deterministically sorted" for row in failures)


def test_compact_validator_blocks_sample_and_old_phrase_index_flags(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(validate, "REPO_ROOT", tmp_path)
    write_compact_fixture(
        tmp_path,
        [
            compact_row(phrase_id="phrase_a", word_token_tuple="[[1],[2]]", rune_token_tuple="[1,2]", identity_sha256="a"),
        ],
        manifest_updates={"sample_asset_used": True, "old_phrase_index_v1_used": True},
    )

    validation = validate.validate_compact_lookup_asset(output_dir=validation_out_dir(tmp_path))
    failures = read_failures(validation_out_dir(tmp_path))

    assert validation["status"] == "blocked"
    reasons = {row["reason"] for row in failures}
    assert "sample asset was used" in reasons
    assert "old phrase_index_v1 was used" in reasons
