from __future__ import annotations

from pathlib import Path

import pytest

from tools.benchmarks.periodic_sub_trans.no_wli.analysis.late_family_quality_v3 import (
    extract_late_family_quality_v3 as mod,
)


def _family_row(
    *,
    key_seed: int,
    study_role: str,
    family_id: str,
    best_truth: float,
    best_trust: float,
    best_archive_uplift: float,
    best_full_uplift: float,
    boundary_count: int,
    boundaries_seen: str,
    persistence_count: int,
    reaches_archive: int,
    role: str = "mixed",
) -> dict[str, object]:
    return {
        "artifact_path": f"output/test/{key_seed}.json",
        "run_id": f"run-{key_seed}",
        "key_seed": key_seed,
        "study_role": study_role,
        "target_panel_name": "core" if study_role == "reference" else "pressure",
        "target_panel_role": "benchmark" if study_role == "reference" else "falsification",
        "family_view_id": "prefix_hamming_le_24",
        "family_id": family_id,
        "member_count": boundary_count,
        "boundaries_seen": boundaries_seen,
        "boundary_count": boundary_count,
        "has_phasec_start": int("phaseC_start" in boundaries_seen),
        "has_stage35_seed": int("stage35_seed" in boundaries_seen),
        "has_stage35_archive": int("stage35_archive" in boundaries_seen),
        "family_role_label": role,
        "best_truth": best_truth,
        "best_trust": best_trust,
        "best_archive_uplift": best_archive_uplift,
        "best_full_uplift": best_full_uplift,
        "best_xent": 10.0,
        "family_persistence_count": persistence_count,
        "family_persistence_boundaries": boundaries_seen,
        "family_reaches_archive": reaches_archive,
        "truth_trend_label": "improves",
        "trust_trend_label": "improves",
        "archive_uplift_trend_label": "improves",
        "full_uplift_trend_label": "improves",
    }


def _case_digest_row(
    *,
    key_seed: int,
    study_role: str,
    truth_family: str,
    trust_family: str,
    archive_family: str,
    full_family: str,
    persistence_family: str,
    case_shape_label: str = "",
    family_quality_read_label: str = "",
    would_dump: int = 0,
    rule_id: str = "",
) -> dict[str, object]:
    return {
        "key_seed": key_seed,
        "study_role": study_role,
        "target_panel_name": "core" if study_role == "reference" else "pressure",
        "target_panel_role": "benchmark" if study_role == "reference" else "falsification",
        "run_type": "bench",
        "would_dump": would_dump,
        "would_stop": 0,
        "shadow_rule_id": rule_id,
        "case_shape_label": case_shape_label,
        "family_quality_read_label": family_quality_read_label,
        "truth_winner_family_id": truth_family,
        "trust_winner_family_id": trust_family,
        "archive_uplift_winner_family_id": archive_family,
        "full_uplift_winner_family_id": full_family,
        "persistence_winner_family_id": persistence_family,
    }


def _agreement_row(
    *,
    key_seed: int,
    study_role: str,
    winner_pattern_key: str,
    pattern_bucket_label: str,
    truth_agreement_count: int,
) -> dict[str, object]:
    return {
        "key_seed": key_seed,
        "study_role": study_role,
        "target_panel_name": "core" if study_role == "reference" else "pressure",
        "target_panel_role": "benchmark" if study_role == "reference" else "falsification",
        "winner_pattern_key": winner_pattern_key,
        "pattern_bucket_label": pattern_bucket_label,
        "unique_winner_family_count": 2,
        "truth_agreement_count": truth_agreement_count,
    }


def _build_study_inputs() -> tuple[list[dict[str, object]], list[dict[str, object]], list[dict[str, object]]]:
    family_rows = [
        _family_row(key_seed=1111, study_role="discriminator", family_id="f0", best_truth=0.53, best_trust=0.17, best_archive_uplift=0.00, best_full_uplift=0.01, boundary_count=3, boundaries_seen="phaseC_start|stage35_seed|stage35_archive", persistence_count=3, reaches_archive=1),
        _family_row(key_seed=1111, study_role="discriminator", family_id="f1", best_truth=0.49, best_trust=0.00, best_archive_uplift=0.22, best_full_uplift=0.00, boundary_count=2, boundaries_seen="phaseC_start|stage35_seed", persistence_count=2, reaches_archive=0, role="challenger_like"),
        _family_row(key_seed=1311, study_role="discriminator", family_id="f0", best_truth=0.58, best_trust=0.35, best_archive_uplift=0.00, best_full_uplift=0.01, boundary_count=3, boundaries_seen="phaseC_start|stage35_seed|stage35_archive", persistence_count=3, reaches_archive=1),
        _family_row(key_seed=1311, study_role="discriminator", family_id="f1", best_truth=0.30, best_trust=0.38, best_archive_uplift=0.22, best_full_uplift=0.00, boundary_count=1, boundaries_seen="stage35_seed", persistence_count=1, reaches_archive=0, role="challenger_like"),
        _family_row(key_seed=1411, study_role="discriminator", family_id="f1", best_truth=0.40, best_trust=0.10, best_archive_uplift=0.49, best_full_uplift=0.00, boundary_count=3, boundaries_seen="phaseC_start|stage35_seed|stage35_archive", persistence_count=3, reaches_archive=1, role="challenger_like"),
        _family_row(key_seed=1411, study_role="discriminator", family_id="f0", best_truth=0.20, best_trust=0.20, best_archive_uplift=0.10, best_full_uplift=0.03, boundary_count=1, boundaries_seen="stage35_seed", persistence_count=1, reaches_archive=0),
        _family_row(key_seed=411, study_role="reference", family_id="f0", best_truth=0.49, best_trust=0.06, best_archive_uplift=0.24, best_full_uplift=0.00, boundary_count=3, boundaries_seen="phaseC_start|stage35_seed|stage35_archive", persistence_count=3, reaches_archive=1, role="anchor_like"),
        _family_row(key_seed=411, study_role="reference", family_id="f1", best_truth=0.42, best_trust=0.08, best_archive_uplift=0.00, best_full_uplift=0.00, boundary_count=2, boundaries_seen="phaseC_start|stage35_seed", persistence_count=2, reaches_archive=0),
        _family_row(key_seed=611, study_role="reference", family_id="f0", best_truth=0.64, best_trust=0.44, best_archive_uplift=0.08, best_full_uplift=0.01, boundary_count=3, boundaries_seen="phaseC_start|stage35_seed|stage35_archive", persistence_count=3, reaches_archive=1),
        _family_row(key_seed=611, study_role="reference", family_id="f1", best_truth=0.63, best_trust=0.35, best_archive_uplift=0.15, best_full_uplift=0.00, boundary_count=2, boundaries_seen="phaseC_start|stage35_seed", persistence_count=2, reaches_archive=0, role="challenger_like"),
        _family_row(key_seed=1011, study_role="reference", family_id="f1", best_truth=0.74, best_trust=0.20, best_archive_uplift=0.00, best_full_uplift=0.00, boundary_count=1, boundaries_seen="phaseC_start", persistence_count=1, reaches_archive=0, role="challenger_like"),
        _family_row(key_seed=1011, study_role="reference", family_id="f0", best_truth=0.73, best_trust=0.32, best_archive_uplift=0.14, best_full_uplift=0.01, boundary_count=3, boundaries_seen="phaseC_start|stage35_seed|stage35_archive", persistence_count=3, reaches_archive=1),
    ]
    digest_rows = [
        _case_digest_row(key_seed=1111, study_role="discriminator", truth_family="f0", trust_family="f0", archive_family="f1", full_family="f0", persistence_family="f0", case_shape_label="accepted_miss_outside_current_model", family_quality_read_label="accepted_miss_family_looks_real"),
        _case_digest_row(key_seed=1311, study_role="discriminator", truth_family="f0", trust_family="f1", archive_family="f1", full_family="f0", persistence_family="f0", case_shape_label="trust_false_fire", family_quality_read_label="trust_false_fire_family_looks_weak", would_dump=1, rule_id="trust0.30_xent24.00_margin0.00_support1"),
        _case_digest_row(key_seed=1411, study_role="discriminator", truth_family="f1", trust_family="f0", archive_family="f0", full_family="f0", persistence_family="f0", case_shape_label="archive_false_fire", family_quality_read_label="archive_false_fire_family_looks_weak", would_dump=1, rule_id="archive_search_uplift0.15"),
        _case_digest_row(key_seed=411, study_role="reference", truth_family="f0", trust_family="f1", archive_family="f0", full_family="f0", persistence_family="f0", family_quality_read_label="truth_trust_split", would_dump=1, rule_id="archive_search_uplift0.15"),
        _case_digest_row(key_seed=611, study_role="reference", truth_family="f0", trust_family="f0", archive_family="f1", full_family="f0", persistence_family="f0", family_quality_read_label="truth_uplift_split", would_dump=1, rule_id="trust0.30_xent24.00_margin0.00_support1"),
        _case_digest_row(key_seed=1011, study_role="reference", truth_family="f1", trust_family="f0", archive_family="f0", full_family="f0", persistence_family="f0", family_quality_read_label="truth_trust_split", would_dump=1, rule_id="trust0.30_xent24.00_margin0.00_support1"),
    ]
    agreement_rows = [
        _agreement_row(key_seed=1111, study_role="discriminator", winner_pattern_key="A-A-B-A-A", pattern_bucket_label="accepted_miss_matches_reference_pattern", truth_agreement_count=4),
        _agreement_row(key_seed=1311, study_role="discriminator", winner_pattern_key="A-B-B-A-A", pattern_bucket_label="false_fire_reference_mismatch", truth_agreement_count=3),
        _agreement_row(key_seed=1411, study_role="discriminator", winner_pattern_key="A-B-A-B-B", pattern_bucket_label="false_fire_reference_mismatch", truth_agreement_count=2),
        _agreement_row(key_seed=411, study_role="reference", winner_pattern_key="A-B-A-A-A", pattern_bucket_label="reference_only_pattern", truth_agreement_count=4),
        _agreement_row(key_seed=611, study_role="reference", winner_pattern_key="A-A-B-A-A", pattern_bucket_label="reference_shared_pattern", truth_agreement_count=4),
        _agreement_row(key_seed=1011, study_role="reference", winner_pattern_key="A-B-B-B-B", pattern_bucket_label="reference_only_pattern", truth_agreement_count=1),
    ]
    return family_rows, digest_rows, agreement_rows


def test_late_family_quality_v3_seed_contract_is_fixed() -> None:
    assert mod.LATE_FAMILY_QUALITY_V3_DISCRIMINATOR_SEEDS == (1111, 1311, 1411)
    assert mod.LATE_FAMILY_QUALITY_V3_REFERENCE_WIN_SEEDS == (411, 611, 1011)
    assert mod.LATE_FAMILY_QUALITY_V3_STUDY_SEEDS == (1111, 1311, 1411, 411, 611, 1011)


def test_late_family_quality_v3_requires_explicit_input_bundle_files(tmp_path: Path) -> None:
    bundle_dir = tmp_path / "bundle"
    bundle_dir.mkdir()
    with pytest.raises(FileNotFoundError):
        mod._require_bundle_files(bundle_dir, mod.REQUIRED_V1_INPUT_FILES, label="v1")


def test_label_family_strength_strong() -> None:
    assert mod._label_family_strength({"family_persistence_count": 2, "family_reaches_archive": 1}) == "strong"


def test_label_family_strength_partial() -> None:
    assert mod._label_family_strength({"family_persistence_count": 2, "family_reaches_archive": 0}) == "partial"


def test_label_family_strength_weak() -> None:
    assert mod._label_family_strength({"family_persistence_count": 1, "family_reaches_archive": 0}) == "weak"


def test_boundary_overlap_label_identical() -> None:
    count, label = mod._boundary_overlap_label(
        {"boundaries_seen": "phaseC_start|stage35_seed", "boundary_count": 2},
        {"boundaries_seen": "phaseC_start|stage35_seed", "boundary_count": 2},
    )
    assert (count, label) == (2, "identical")


def test_boundary_overlap_label_partial() -> None:
    count, label = mod._boundary_overlap_label(
        {"boundaries_seen": "phaseC_start|stage35_seed", "boundary_count": 2},
        {"boundaries_seen": "stage35_seed|stage35_archive", "boundary_count": 2},
    )
    assert (count, label) == (1, "partial")


def test_boundary_overlap_label_none() -> None:
    count, label = mod._boundary_overlap_label(
        {"boundaries_seen": "phaseC_start", "boundary_count": 1},
        {"boundaries_seen": "stage35_archive", "boundary_count": 1},
    )
    assert (count, label) == (0, "none")


def test_label_pair_read_truth_advantaged() -> None:
    label = mod._label_pair_read({
        "same_family": 0,
        "truth_minus_alt_best_truth": 0.20,
        "truth_minus_alt_persistence_count": 1,
        "boundary_overlap_label": "partial",
        "alt_winner_strength_label": "partial",
    })
    assert label == "truth_advantaged"


def test_label_pair_read_same_family() -> None:
    assert mod._label_pair_read({"same_family": 1}) == "same_family"


def test_label_pair_read_inconclusive() -> None:
    assert mod._label_pair_read({"same_family": 0, "truth_minus_alt_best_truth": float("nan")}) == "inconclusive"


def test_pattern_strength_read_marks_1111_style_case_as_accepted_miss_reference_like() -> None:
    label = mod._label_pattern_strength_read(
        {
            "key_seed": 1111,
            "winner_pattern_key": "A-A-B-A-A",
            "truth_winner_strength_label": "strong",
            "truth_minus_trust_winner_best_truth": 0.00,
            "truth_minus_archive_winner_best_truth": 0.04,
        },
        reference_patterns={"A-A-B-A-A"},
    )
    assert label == "accepted_miss_reference_like"


def test_pattern_strength_read_marks_1311_style_case_as_trust_false_fire_suspicious() -> None:
    label = mod._label_pattern_strength_read(
        {
            "key_seed": 1311,
            "winner_pattern_key": "A-B-B-A-A",
            "truth_winner_strength_label": "strong",
            "truth_winner_family_id": "f0",
            "trust_winner_family_id": "f1",
            "truth_minus_trust_winner_best_truth": 0.20,
            "truth_minus_trust_winner_persistence_count": 1,
            "truth_vs_trust_boundary_overlap_label": "partial",
            "trust_winner_strength_label": "partial",
        },
        reference_patterns={"A-A-B-A-A", "A-B-A-A-A", "A-B-B-B-B"},
    )
    assert label == "trust_false_fire_suspicious"


def test_pattern_strength_read_marks_1411_style_case_as_archive_false_fire_suspicious() -> None:
    label = mod._label_pattern_strength_read(
        {
            "key_seed": 1411,
            "winner_pattern_key": "A-B-A-B-B",
            "truth_winner_strength_label": "strong",
            "truth_winner_family_id": "f1",
            "archive_uplift_winner_family_id": "f0",
            "truth_minus_archive_winner_best_truth": 0.15,
            "truth_minus_archive_winner_persistence_count": 1,
            "truth_vs_archive_boundary_overlap_label": "partial",
            "archive_winner_strength_label": "partial",
        },
        reference_patterns={"A-A-B-A-A", "A-B-A-A-A", "A-B-B-B-B"},
    )
    assert label == "archive_false_fire_suspicious"


def test_pattern_strength_read_handles_reference_like_strong_case() -> None:
    label = mod._label_pattern_strength_read(
        {
            "key_seed": 611,
            "winner_pattern_key": "A-A-B-A-A",
            "truth_winner_strength_label": "strong",
        },
        reference_patterns={"A-A-B-A-A", "A-B-A-A-A", "A-B-B-B-B"},
    )
    assert label == "reference_like_strong"


def test_pattern_strength_read_handles_pattern_only_but_weak_case() -> None:
    label = mod._label_pattern_strength_read(
        {
            "key_seed": 611,
            "winner_pattern_key": "A-A-B-A-A",
            "truth_winner_strength_label": "weak",
        },
        reference_patterns={"A-A-B-A-A", "A-B-A-A-A", "A-B-B-B-B"},
    )
    assert label == "pattern_only_reference_like_but_strength_weak"


def test_build_pattern_strength_rows_carries_v1_and_v2_reads() -> None:
    family_rows, digest_rows, agreement_rows = _build_study_inputs()
    rows = mod._build_pattern_strength_rows(
        family_rows=family_rows,
        case_digest_rows=digest_rows,
        seed_agreement_rows=agreement_rows,
    )
    by_seed = {row["key_seed"]: row for row in rows}
    assert by_seed[1111]["family_quality_read_label"] == "accepted_miss_family_looks_real"
    assert by_seed[1111]["winner_pattern_key"] == "A-A-B-A-A"
    assert by_seed[1111]["truth_winner_strength_label"] == "strong"


def test_build_truth_relative_pair_rows_writes_expected_pairs() -> None:
    family_rows, digest_rows, agreement_rows = _build_study_inputs()
    rows = mod._build_pattern_strength_rows(
        family_rows=family_rows,
        case_digest_rows=digest_rows,
        seed_agreement_rows=agreement_rows,
    )
    pair_rows = mod._build_truth_relative_pair_rows(rows)
    assert len(pair_rows) == len(mod.LATE_FAMILY_QUALITY_V3_STUDY_SEEDS) * 4
    assert {row["pair_name"] for row in pair_rows} == {
        "truth_vs_trust",
        "truth_vs_archive",
        "truth_vs_full_uplift",
        "truth_vs_persistence",
    }


def test_pattern_strength_rows_are_deterministic_under_input_reordering() -> None:
    family_rows, digest_rows, agreement_rows = _build_study_inputs()
    rows_a = mod._build_pattern_strength_rows(
        family_rows=family_rows,
        case_digest_rows=digest_rows,
        seed_agreement_rows=agreement_rows,
    )
    rows_b = mod._build_pattern_strength_rows(
        family_rows=list(reversed(family_rows)),
        case_digest_rows=list(reversed(digest_rows)),
        seed_agreement_rows=list(reversed(agreement_rows)),
    )
    assert rows_a == rows_b


def test_pattern_strength_cases_markdown_includes_all_study_seeds(tmp_path: Path) -> None:
    family_rows, digest_rows, agreement_rows = _build_study_inputs()
    pattern_rows = mod._build_pattern_strength_rows(
        family_rows=family_rows,
        case_digest_rows=digest_rows,
        seed_agreement_rows=agreement_rows,
    )
    pair_rows = mod._build_truth_relative_pair_rows(pattern_rows)
    mod._write_cases_markdown(tmp_path, pattern_rows, pair_rows)
    text = (tmp_path / "pattern_strength_cases.md").read_text(encoding="utf-8")
    for seed in mod.LATE_FAMILY_QUALITY_V3_STUDY_SEEDS:
        assert f"Seed {seed}" in text
