from __future__ import annotations

from pathlib import Path

import pytest

from tools.benchmarks.periodic_sub_trans.no_wli.analysis.late_family_quality_v2 import (
    extract_late_family_quality_v2 as mod,
)


def _digest_row(
    *,
    key_seed: int,
    study_role: str,
    truth_family: str,
    trust_family: str,
    archive_family: str,
    full_family: str,
    persistence_family: str,
    case_shape_label: str = '',
    family_quality_read_label: str = '',
) -> dict[str, object]:
    return {
        'key_seed': key_seed,
        'study_role': study_role,
        'target_panel_name': 'core' if study_role == 'reference' else 'pressure',
        'target_panel_role': 'benchmark' if study_role == 'reference' else 'falsification',
        'run_type': 'bench',
        'would_dump': 0,
        'would_stop': 0,
        'shadow_rule_id': '',
        'case_shape_label': case_shape_label,
        'family_quality_read_label': family_quality_read_label,
        'truth_winner_family_id': truth_family,
        'trust_winner_family_id': trust_family,
        'archive_uplift_winner_family_id': archive_family,
        'full_uplift_winner_family_id': full_family,
        'persistence_winner_family_id': persistence_family,
        'truth_winner_best_truth': 0.5,
        'trust_winner_best_trust': 0.3,
        'archive_winner_best_archive_uplift': 0.2,
        'full_uplift_winner_best_full_uplift': 0.01,
        'persistence_winner_family_persistence_count': 3,
        'truth_winner_family_role_label': 'mixed',
        'trust_winner_family_role_label': 'mixed',
        'archive_winner_family_role_label': 'mixed',
        'full_uplift_winner_family_role_label': 'mixed',
        'persistence_winner_family_role_label': 'mixed',
        'truth_winner_boundaries_seen': 'phaseC_start|stage35_seed|stage35_archive',
        'trust_winner_boundaries_seen': 'phaseC_start|stage35_seed|stage35_archive',
        'archive_winner_boundaries_seen': 'phaseC_start|stage35_seed',
        'full_uplift_winner_boundaries_seen': 'phaseC_start|stage35_seed|stage35_archive',
        'persistence_winner_boundaries_seen': 'phaseC_start|stage35_seed|stage35_archive',
        'truth_winner_truth_trend_label': 'improves',
        'trust_winner_trust_trend_label': 'improves',
        'archive_winner_archive_uplift_trend_label': 'mixed',
        'full_uplift_winner_full_uplift_trend_label': 'improves',
    }


def test_family_quality_v2_seed_contract_is_fixed() -> None:
    assert mod.FAMILY_QUALITY_V2_STUDY_SEEDS == (1111, 1311, 1411, 411, 611, 1011)


def test_family_quality_v2_requires_explicit_input_bundle_files(tmp_path: Path) -> None:
    bundle_dir = tmp_path / 'bundle'
    bundle_dir.mkdir()
    with pytest.raises(FileNotFoundError):
        mod._require_input_bundle_files(bundle_dir)


def test_normalize_winner_pattern_is_deterministic() -> None:
    pattern_key, metric_to_symbol = mod._normalize_winner_pattern(
        _digest_row(
            key_seed=1111,
            study_role='discriminator',
            truth_family='f0',
            trust_family='f0',
            archive_family='f1',
            full_family='f0',
            persistence_family='f0',
        )
    )
    assert pattern_key == 'A-A-B-A-A'
    assert metric_to_symbol['truth'] == 'A'
    assert metric_to_symbol['archive_uplift'] == 'B'


def test_build_seed_agreement_rows_marks_false_fire_reference_mismatch() -> None:
    rows = [
        _digest_row(
            key_seed=611,
            study_role='reference',
            truth_family='f0',
            trust_family='f0',
            archive_family='f1',
            full_family='f0',
            persistence_family='f0',
        ),
        _digest_row(
            key_seed=1311,
            study_role='discriminator',
            truth_family='f0',
            trust_family='f1',
            archive_family='f1',
            full_family='f0',
            persistence_family='f0',
            case_shape_label='trust_false_fire',
        ),
    ]
    seed_rows = mod._build_seed_agreement_rows(rows)
    by_seed = {row['key_seed']: row for row in seed_rows}
    assert by_seed[611]['winner_pattern_key'] == 'A-A-B-A-A'
    assert by_seed[1311]['winner_pattern_key'] == 'A-B-B-A-A'
    assert by_seed[1311]['pattern_bucket_label'] == 'false_fire_reference_mismatch'


def test_build_seed_agreement_rows_marks_accepted_miss_matches_reference_pattern() -> None:
    rows = [
        _digest_row(
            key_seed=611,
            study_role='reference',
            truth_family='f0',
            trust_family='f0',
            archive_family='f1',
            full_family='f0',
            persistence_family='f0',
        ),
        _digest_row(
            key_seed=1111,
            study_role='discriminator',
            truth_family='f0',
            trust_family='f0',
            archive_family='f1',
            full_family='f0',
            persistence_family='f0',
            case_shape_label='accepted_miss_outside_current_model',
        ),
    ]
    seed_rows = mod._build_seed_agreement_rows(rows)
    by_seed = {row['key_seed']: row for row in seed_rows}
    assert by_seed[1111]['pattern_bucket_label'] == 'accepted_miss_matches_reference_pattern'


def test_build_pairwise_rows_emits_all_metric_pairs_for_seed() -> None:
    digest_rows = [
        _digest_row(
            key_seed=411,
            study_role='reference',
            truth_family='f0',
            trust_family='f1',
            archive_family='f0',
            full_family='f0',
            persistence_family='f0',
        ),
    ]
    seed_rows = mod._build_seed_agreement_rows(digest_rows)
    pairwise_rows = mod._build_pairwise_rows(seed_rows, digest_rows)
    assert len(pairwise_rows) == len(mod.PAIRWISE_METRIC_PAIRS)
    assert {row['metric_pair'] for row in pairwise_rows} == {f'{a}__{b}' for a, b in mod.PAIRWISE_METRIC_PAIRS}


def test_build_agreement_summary_tracks_shared_patterns() -> None:
    digest_rows = [
        _digest_row(key_seed=611, study_role='reference', truth_family='f0', trust_family='f0', archive_family='f1', full_family='f0', persistence_family='f0'),
        _digest_row(key_seed=1111, study_role='discriminator', truth_family='f0', trust_family='f0', archive_family='f1', full_family='f0', persistence_family='f0', case_shape_label='accepted_miss_outside_current_model'),
        _digest_row(key_seed=1311, study_role='discriminator', truth_family='f0', trust_family='f1', archive_family='f1', full_family='f0', persistence_family='f0', case_shape_label='trust_false_fire'),
    ]
    seed_rows = mod._build_seed_agreement_rows(digest_rows)
    pairwise_rows = mod._build_pairwise_rows(seed_rows, digest_rows)
    summary = mod._build_agreement_summary(seed_rows, pairwise_rows)
    assert 'A-A-B-A-A' in summary['shared_patterns']
    assert 'A-B-B-A-A' in summary['discriminator_only_patterns']


def test_agreement_cases_markdown_includes_all_study_seeds_present(tmp_path: Path) -> None:
    seed_rows = mod._build_seed_agreement_rows([
        _digest_row(key_seed=1111, study_role='discriminator', truth_family='f0', trust_family='f0', archive_family='f1', full_family='f0', persistence_family='f0', case_shape_label='accepted_miss_outside_current_model'),
        _digest_row(key_seed=411, study_role='reference', truth_family='f0', trust_family='f1', archive_family='f0', full_family='f0', persistence_family='f0'),
    ])
    mod._write_case_markdown(tmp_path, seed_rows)
    text = (tmp_path / 'agreement_cases.md').read_text(encoding='utf-8')
    assert 'Seed 1111' in text
    assert 'Seed 411' in text
