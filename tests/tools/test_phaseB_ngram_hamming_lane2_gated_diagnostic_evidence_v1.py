from __future__ import annotations

import csv
import json
from pathlib import Path

import numpy as np

from rune_decrypter_prime.scoring.ngram_hamming.reference import PhraseEntry, PhraseHit
from tools.benchmarks.periodic_sub_trans.no_wli.analysis import (
    run_phaseB_ngram_hamming_lane2_gated_diagnostic_evidence_v1 as diag,
)


def fixture_entries() -> tuple[PhraseEntry, ...]:
    return (
        PhraseEntry(
            phrase_id="normal-o2",
            direction="fwd",
            dictionary_cut="normal",
            ngram_order=2,
            word_token_ids=((1, 2, 3, 4), (5, 6, 7, 8)),
            rune_token_ids=(1, 2, 3, 4, 5, 6, 7, 8),
        ),
        PhraseEntry(
            phrase_id="strict-o2",
            direction="fwd",
            dictionary_cut="strict",
            ngram_order=2,
            word_token_ids=((2, 3, 4, 5), (6, 7, 8, 9)),
            rune_token_ids=(2, 3, 4, 5, 6, 7, 8, 9),
        ),
        PhraseEntry(
            phrase_id="normal-o3",
            direction="fwd",
            dictionary_cut="normal",
            ngram_order=3,
            word_token_ids=((3, 4, 5), (6, 7, 8), (9, 10, 11)),
            rune_token_ids=(3, 4, 5, 6, 7, 8, 9, 10, 11),
        ),
        PhraseEntry(
            phrase_id="strict-o3",
            direction="fwd",
            dictionary_cut="strict",
            ngram_order=3,
            word_token_ids=((4, 5, 6), (7, 8, 9), (10, 11, 12)),
            rune_token_ids=(4, 5, 6, 7, 8, 9, 10, 11, 12),
        ),
    )


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def test_deterministic_damage_same_seed_repeats_positions_and_tokens() -> None:
    tokens = tuple(range(20))

    left_tokens, left_manifest = diag.deterministic_damage(tokens, damage_rate=0.35, seed=123)
    right_tokens, right_manifest = diag.deterministic_damage(tokens, damage_rate=0.35, seed=123)

    assert left_tokens == right_tokens
    assert left_manifest == right_manifest
    assert left_manifest["damaged_token_count"] == 7
    assert left_manifest["damage_positions_sha256"]


def test_deterministic_damage_different_seed_changes_damage() -> None:
    tokens = tuple(range(20))

    left_tokens, left_manifest = diag.deterministic_damage(tokens, damage_rate=0.35, seed=123)
    right_tokens, right_manifest = diag.deterministic_damage(tokens, damage_rate=0.35, seed=124)

    assert left_tokens != right_tokens
    assert left_manifest["damage_positions_sha256"] != right_manifest["damage_positions_sha256"]


def test_profile_validation_rejects_s3w_strict_bridge_label() -> None:
    specs = tuple(
        spec if spec.profile_id != "BR_O3_conservative" else spec.__class__(
            **{**spec.__dict__, "canonical_profile_id": "S3W"}
        )
        for spec in diag.selected_profile_specs()
    )

    try:
        diag.validate_profile_specs_for_lane2(specs)
    except ValueError as exc:
        assert "S3W" in str(exc)
    else:
        raise AssertionError("expected profile validation failure")


def test_lane2_diagnostic_evidence_writes_required_outputs_and_safe_manifest(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(diag, "REPO_ROOT", tmp_path)
    output_dir = tmp_path / "out"

    manifest = diag.run_lane2_gated_diagnostic_evidence(output_dir=output_dir, phrase_entries=fixture_entries())

    assert manifest["production_scorer_change"] is False
    assert manifest["real_candidate_scan_started"] is False
    assert manifest["broad_candidate_scan_started"] is False
    assert manifest["controlled_eval_corpus_scan_started"] is True
    assert manifest["run_authority"] == "diagnostic_only"
    assert manifest["asset_source_mode"] == diag.ASSET_SOURCE_MODE
    assert manifest["runtime_index_asset_id"] == diag.RUNTIME_INDEX_ASSET_ID
    assert manifest["compact_asset_id"] == diag.COMPACT_ASSET_ID
    assert manifest["old_phrase_index_v1_used"] is False
    assert manifest["sample_asset_used"] is False
    assert manifest["full_raw_shards_used_directly_as_runtime"] is False
    assert manifest["phrase_entry_source"] == "fast_runtime_index_bounded_diagnostic_selection"
    assert manifest["positive_clean_case_count"] == len(fixture_entries())
    assert manifest["matched_null_families"] == list(diag.MATCHED_NULL_FAMILIES)
    for name in (
        "run_manifest.json",
        "corpus_manifest.json",
        "profile_manifest_rows.csv",
        "candidate_profile_summary_rows.csv",
        "candidate_cluster_summary_rows.csv",
        "sampled_hit_rows.csv",
        "null_comparison_rows.csv",
        "concentration_rows.csv",
        "damage_tier_summary_rows.csv",
        "review_readout.md",
    ):
        assert (output_dir / name).exists()


def test_lane2_diagnostic_outputs_keep_scopes_and_nulls_separate(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(diag, "REPO_ROOT", tmp_path)
    output_dir = tmp_path / "out"

    diag.run_lane2_gated_diagnostic_evidence(output_dir=output_dir, phrase_entries=fixture_entries())
    summary_rows = read_csv_rows(output_dir / "candidate_profile_summary_rows.csv")
    null_rows = read_csv_rows(output_dir / "null_comparison_rows.csv")
    concentration_rows = read_csv_rows(output_dir / "concentration_rows.csv")

    assert {row["cluster_scope"] for row in summary_rows} == {
        diag.CLUSTER_SCOPE_ALL,
        diag.CLUSTER_SCOPE_BLOCKED,
        diag.CLUSTER_SCOPE_CANONICAL,
    }
    assert all(row["profile_id"] != "BR_O2_soft" for row in summary_rows if row["cluster_scope"] == diag.CLUSTER_SCOPE_BLOCKED)
    assert {
        (row["profile_id"], row["cut"], row["ngram_order"])
        for row in summary_rows
        if row["cluster_scope"] == diag.CLUSTER_SCOPE_CANONICAL
    } == {("BR_O3_conservative", "normal", "3")}
    assert any(row["matched_null_case_count"] != "0" for row in null_rows)
    assert any("order2_support_diagnostic_only" in row["warning_flags"] for row in concentration_rows)
    assert all(row["cut"] in {"normal", "strict"} for row in summary_rows)


def test_lane2_corpus_has_matched_nulls_for_each_positive(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(diag, "REPO_ROOT", tmp_path)
    output_dir = tmp_path / "out"

    diag.run_lane2_gated_diagnostic_evidence(output_dir=output_dir, phrase_entries=fixture_entries())
    manifest = json.loads((output_dir / "corpus_manifest.json").read_text(encoding="utf-8"))
    positive_rows = [
        json.loads(line)
        for line in (output_dir / "positive_passages.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    null_rows = [
        json.loads(line)
        for line in (output_dir / "null_passages.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    nulls_by_source: dict[str, list[dict[str, object]]] = {}
    for row in null_rows:
        nulls_by_source.setdefault(str(row["source_case_id"]), []).append(row)

    assert manifest["positive_clean_case_count"] == len(fixture_entries())
    assert manifest["minimum_matched_nulls_per_positive"] == len(diag.MATCHED_NULL_FAMILIES)
    for row in positive_rows:
        matched = nulls_by_source[str(row["candidate_id"])]
        assert {item["case_family"] for item in matched} == set(diag.MATCHED_NULL_FAMILIES)
        assert all(item["input_token_count"] == row["input_token_count"] for item in matched)
        assert all(item["damage_rate"] == row["damage_rate"] for item in matched)


def test_lane2_asset_loader_reports_missing_payload_paths(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(diag, "REPO_ROOT", tmp_path)
    manifest_dir = tmp_path / diag.ASSET_HOME_REL
    manifest_dir.mkdir(parents=True)
    missing_path = (
        "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
        "phaseB_ngram_hamming_full_raw_asset_shards_v1/missing.csv.gz"
    )
    (manifest_dir / "asset_manifest.json").write_text(
        json.dumps(
            {
                "files": [
                    {
                        "ngram_order": 2,
                        "dictionary_cut": "normal",
                        "direction": "fwd",
                        "aggregate_rows": 100,
                        "bytes": 100,
                        "path": missing_path,
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    try:
        diag.load_lane1_asset_entries()
    except FileNotFoundError as exc:
        assert "missing Lane 1 payload files" in str(exc)
        assert missing_path in str(exc)
    else:
        raise AssertionError("expected missing Lane 1 payload failure")


def test_lane2_default_loader_requires_valid_fast_runtime_index(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(diag, "REPO_ROOT", tmp_path)
    npz_rel = (
        "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
        "phaseB_ngram_hamming_fast_runtime_lookup_index_v1/runtime_index/direction=fwd/order=2/cut=normal/"
        "phrase_len=8__word_lens=4-4.npz"
    )
    npz_path = tmp_path / npz_rel
    npz_path.parent.mkdir(parents=True)
    np.savez_compressed(
        npz_path,
        rune_tokens=np.asarray([[1, 2, 3, 4, 5, 6, 7, 8]], dtype=np.uint8),
        phrase_id=np.asarray(["runtime-a"], dtype=np.str_),
        direction=np.asarray(["fwd"], dtype=np.str_),
        dictionary_cut=np.asarray(["normal"], dtype=np.str_),
        ngram_order=np.asarray([2], dtype=np.int16),
        phrase_token_length=np.asarray([8], dtype=np.int16),
        word_token_lengths=np.asarray([4, 4], dtype=np.int16),
        sum_count=np.asarray([1.0], dtype=np.float64),
        max_count=np.asarray([1.0], dtype=np.float64),
        sum_log_count=np.asarray([0.0], dtype=np.float64),
        max_log_count=np.asarray([0.0], dtype=np.float64),
        source_row_count=np.asarray([1], dtype=np.int64),
    )
    manifest_path = tmp_path / diag.RUNTIME_INDEX_MANIFEST_REL
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps(
            {
                "asset_id": diag.RUNTIME_INDEX_ASSET_ID,
                "asset_status": "built",
                "source_compact_asset_id": diag.COMPACT_ASSET_ID,
                "production_scorer_change": False,
                "sample_asset_used": False,
                "old_phrase_index_v1_used": False,
                "full_raw_shards_used_directly_as_runtime": False,
                "files": [
                    {
                        "path": npz_rel,
                        "direction": "fwd",
                        "dictionary_cut": "normal",
                        "ngram_order": 2,
                        "phrase_token_length": 8,
                        "word_token_lengths": "[4,4]",
                    }
                ],
            }
        )
        + "\n",
        encoding="utf-8",
    )
    validation_path = tmp_path / diag.RUNTIME_INDEX_VALIDATION_MANIFEST_REL
    validation_path.parent.mkdir(parents=True, exist_ok=True)
    validation_path.write_text(json.dumps({"status": "pass"}) + "\n", encoding="utf-8")

    entries = diag.load_fast_runtime_index_entries()

    assert len(entries) == 1
    assert entries[0].phrase_id == "runtime-a"
    assert entries[0].count == 0.0
    assert entries[0].log_count == 0.0


def test_per_profile_cluster_fractions_ignore_other_profiles_in_same_cluster() -> None:
    case = diag.EvalCase(
        candidate_id="candidate-a",
        case_family="positive_clean",
        damage_rate=0.0,
        damage_mode="none",
        seed=1,
        tokens=(1, 2, 3, 4, 5, 6, 7, 8, 9),
        source_case_id="source-a",
        expected_role="positive",
        source_kind="fixture",
    )
    target_spec = next(spec for spec in diag.selected_profile_specs() if spec.profile_id == "BR_O3_conservative")
    target_hit = PhraseHit(
        candidate_id=case.candidate_id,
        chunk_id="chunk-a",
        damage_level="positive_clean:0.0",
        profile_id="BR_O3_conservative",
        ngram_order=3,
        dictionary_cut="normal",
        phrase_id="target",
        phrase_count=1,
        phrase_log_count=1.0,
        phrase_token_length=9,
        word_lengths=(3, 3, 3),
        word_hds=(0, 0, 0),
        total_phrase_hd=0,
        max_word_hd=0,
        mean_word_hd=0.0,
        normalised_phrase_hd=0.0,
        hit_start=0,
        hit_end=9,
    )
    other_profile_hit = PhraseHit(
        **{
            **target_hit.__dict__,
            "profile_id": "BR_O3_soft",
            "phrase_id": "other-profile",
            "total_phrase_hd": 1,
            "max_word_hd": 1,
            "mean_word_hd": 1 / 3,
            "normalised_phrase_hd": 1 / 9,
        }
    )
    clusters = diag.cluster_hits_overlap_touch(
        (target_hit, other_profile_hit),
        cluster_scope=diag.CLUSTER_SCOPE_ALL,
    )

    row = diag.candidate_profile_summary_row(
        case,
        target_spec,
        "normal",
        3,
        (target_hit,),
        clusters,
        diag.CLUSTER_SCOPE_ALL,
    )

    assert row["hit_count"] == 1
    assert row["cluster_count"] == 1
    assert row["dominant_cluster_hit_fraction"] == 1.0
    assert row["top_5_cluster_hit_fraction"] == 1.0
    assert row["exact_cluster_count"] == 1


def test_lane2_concentration_fraction_outputs_are_bounded(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(diag, "REPO_ROOT", tmp_path)
    output_dir = tmp_path / "out"

    diag.run_lane2_gated_diagnostic_evidence(output_dir=output_dir, phrase_entries=fixture_entries())
    concentration_rows = read_csv_rows(output_dir / "concentration_rows.csv")

    fraction_fields = (
        "dominant_phrase_hit_fraction",
        "dominant_cluster_hit_fraction",
        "dominant_start_hit_fraction",
        "top_5_phrase_hit_fraction",
        "top_5_cluster_hit_fraction",
    )
    assert concentration_rows
    for row in concentration_rows:
        for field in fraction_fields:
            assert 0.0 <= float(row[field]) <= 1.0


def test_lane2_corpus_records_damage_manifest_fields(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(diag, "REPO_ROOT", tmp_path)
    output_dir = tmp_path / "out"

    diag.run_lane2_gated_diagnostic_evidence(output_dir=output_dir, phrase_entries=fixture_entries())
    damaged = [
        json.loads(line)
        for line in (output_dir / "damaged_cases.jsonl").read_text(encoding="utf-8").splitlines()
    ]

    assert damaged
    for row in damaged:
        assert row["damage_mode"] == "substitute"
        assert row["damage_rate"] in {0.2, 0.35, 0.5}
        assert row["seed"]
        assert row["alphabet_size"] == 29
        assert row["input_token_count"] > 0
        assert row["damaged_token_count"] > 0
        assert row["damage_positions_sha256"]
        assert row["source_case_id"]
