from __future__ import annotations

import csv
import json
from pathlib import Path

from rune_decrypter_prime.scoring.ngram_hamming.reference import PhraseEntry
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
        diag.CLUSTER_SCOPE_SCORE,
    }
    assert all(row["profile_id"] != "BR_O2_soft" for row in summary_rows if row["cluster_scope"] == diag.CLUSTER_SCOPE_SCORE)
    assert any(row["matched_null_case_count"] != "0" for row in null_rows)
    assert any("order2_support_diagnostic_only" in row["warning_flags"] for row in concentration_rows)
    assert all(row["cut"] in {"normal", "strict"} for row in summary_rows)


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
