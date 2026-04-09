from __future__ import annotations

from pathlib import Path

import pytest

from tools.benchmarks.periodic_sub_trans.no_wli.analysis.late_family_quality_v1 import (
    extract_late_family_quality_v1 as mod,
)


def _family_row(
    *,
    key_seed: int,
    family_id: str,
    stage_boundary: str,
    candidate_hash: str,
    truth: float,
    trust: float,
    archive_uplift: float,
    full_uplift: float,
    xent: float = 10.0,
    lane: str = '',
    distance_to_anchor: float = 0.0,
    persistence_count: int = 0,
    persistence_boundaries: str = '',
    reaches_archive: int = 0,
    target_panel_name: str = 'core',
    target_panel_role: str = 'benchmark',
) -> dict[str, object]:
    return {
        'artifact_path': f'output/test/{key_seed}.json',
        'run_id': f'run-{key_seed}',
        'key_seed': key_seed,
        'run_type': 'bench',
        'target_panel_name': target_panel_name,
        'target_panel_role': target_panel_role,
        'family_view_id': 'prefix_hamming_le_24',
        'family_id': family_id,
        'stage_boundary': stage_boundary,
        'candidate_hash': candidate_hash,
        'lane': lane,
        'distance_to_anchor': distance_to_anchor,
        'replay_truth_match': truth,
        'replay_word_ngram_trust_score': trust,
        'replay_word_ngram_report_xent': xent,
        'shadow_late_family_search_uplift': archive_uplift,
        'shadow_late_family_full_uplift': full_uplift,
        'shadow_late_family_persistence_count': persistence_count,
        'shadow_late_family_persistence_boundaries': persistence_boundaries,
        'shadow_late_family_reaches_archive': reaches_archive,
    }


def _run_row(seed: int, *, would_dump: int = 0, would_stop: int = 0, rule_id: str = '', panel: str = 'core') -> dict[str, object]:
    return {
        'key_seed': seed,
        'target_panel_name': panel,
        'target_panel_role': 'benchmark' if panel == 'core' else 'falsification',
        'run_type': 'bench',
        'would_dump': would_dump,
        'would_stop': would_stop,
        'shadow_rule_id': rule_id,
    }


def _case_row(seed: int, label: str, *, panel: str = 'core') -> dict[str, object]:
    return {
        'key_seed': seed,
        'target_panel_name': panel,
        'target_panel_role': 'benchmark' if panel == 'core' else 'falsification',
        'run_type': 'bench',
        'would_dump': 0,
        'would_stop': 0,
        'shadow_rule_id': '',
        'case_shape_label': label,
    }


def test_family_quality_study_seed_contract_is_fixed() -> None:
    assert mod.FAMILY_QUALITY_DISCRIMINATOR_SEEDS == (1111, 1311, 1411)
    assert mod.FAMILY_QUALITY_REFERENCE_WIN_SEEDS == (411, 611, 1011)
    assert mod.FAMILY_QUALITY_STUDY_SEEDS == (1111, 1311, 1411, 411, 611, 1011)


def test_family_quality_requires_explicit_input_bundle_files(tmp_path: Path) -> None:
    bundle_dir = tmp_path / 'bundle'
    bundle_dir.mkdir()
    with pytest.raises(FileNotFoundError):
        mod._require_input_bundle_files(bundle_dir)


def test_family_quality_keeps_partial_families_and_sets_missing_boundary_flags() -> None:
    rows = [
        _family_row(
            key_seed=1111,
            family_id='f1',
            stage_boundary='phaseC_start',
            candidate_hash='a',
            truth=0.4,
            trust=0.1,
            archive_uplift=0.0,
            full_uplift=0.0,
            persistence_count=1,
            persistence_boundaries='phaseC_start',
        ),
        _family_row(
            key_seed=1111,
            family_id='f1',
            stage_boundary='stage35_archive',
            candidate_hash='b',
            truth=0.5,
            trust=0.2,
            archive_uplift=0.1,
            full_uplift=0.2,
            persistence_count=2,
            persistence_boundaries='phaseC_start|stage35_archive',
            reaches_archive=1,
        ),
    ]
    family_rows = mod._build_family_rows(rows)
    assert len(family_rows) == 1
    row = family_rows[0]
    assert row['has_phasec_start'] == 1
    assert row['has_stage35_seed'] == 0
    assert row['has_stage35_archive'] == 1
    assert row['boundary_count'] == 2
    assert row['truth_trend_label'] == 'improves'


def test_family_role_label_anchor_like() -> None:
    assert mod._family_role_label(1, 0) == 'anchor_like'


def test_family_role_label_challenger_like() -> None:
    assert mod._family_role_label(0, 1) == 'challenger_like'


def test_family_role_label_mixed() -> None:
    assert mod._family_role_label(1, 1) == 'mixed'


def test_metric_trend_label_improves() -> None:
    assert mod._metric_trend_label([0.1, 0.2, 0.3]) == 'improves'


def test_metric_trend_label_degrades() -> None:
    assert mod._metric_trend_label([0.3, 0.2, 0.1]) == 'degrades'


def test_metric_trend_label_flat() -> None:
    assert mod._metric_trend_label([0.3, 0.3, 0.3]) == 'flat'


def test_metric_trend_label_mixed() -> None:
    assert mod._metric_trend_label([0.1, 0.3, 0.2]) == 'mixed'


def test_metric_trend_label_insufficient_data() -> None:
    assert mod._metric_trend_label([float('nan'), 0.3]) == 'insufficient_data'


def test_pick_family_winner_by_metric_uses_stable_tiebreaks() -> None:
    rows = [
        {'family_id': 'f2', 'best_truth': 0.9, 'boundary_count': 2, 'member_count': 3},
        {'family_id': 'f1', 'best_truth': 0.9, 'boundary_count': 2, 'member_count': 3},
    ]
    winner = mod._pick_family_winner_by_metric(rows, metric_key='best_truth')
    assert winner['family_id'] == 'f1'


def test_winner_family_agreement_label_all_agree() -> None:
    assert mod._winner_family_agreement_label('f1', 'f1', 'f1', 'f1', 'f1') == 'all_agree'


def test_winner_family_agreement_label_split() -> None:
    assert mod._winner_family_agreement_label('f1', 'f2', 'f3', 'f4', 'f5') == 'truth_only'


def test_family_quality_case_digest_carries_stop_verdict_and_case_label() -> None:
    family_rows = [
        {
            'artifact_path': 'output/test/1111.json',
            'run_id': 'run-1111',
            'key_seed': 1111,
            'target_panel_name': 'core',
            'target_panel_role': 'benchmark',
            'study_role': 'discriminator',
            'family_view_id': 'prefix_hamming_le_24',
            'family_id': 'f1',
            'member_count': 2,
            'boundary_count': 2,
            'best_truth': 0.6,
            'best_trust': 0.1,
            'best_archive_uplift': 0.0,
            'best_full_uplift': 0.1,
            'family_persistence_count': 2,
            'family_role_label': 'challenger_like',
            'truth_trend_label': 'improves',
            'trust_trend_label': 'mixed',
            'archive_uplift_trend_label': 'flat',
            'boundaries_seen': 'phaseC_start|stage35_archive',
        },
    ]
    digest_rows = mod._build_family_quality_case_digest(
        family_rows,
        [_run_row(1111, would_dump=0, would_stop=0, rule_id='')],
        [_case_row(1111, 'accepted_miss_outside_current_model')],
    )
    assert digest_rows[0]['would_dump'] == 0
    assert digest_rows[0]['case_shape_label'] == 'accepted_miss_outside_current_model'


def test_family_quality_case_digest_detects_truth_trust_split() -> None:
    family_rows = [
        {
            'artifact_path': 'output/test/1311.json',
            'run_id': 'run-1311',
            'key_seed': 1311,
            'target_panel_name': 'pressure',
            'target_panel_role': 'falsification',
            'study_role': 'discriminator',
            'family_view_id': 'prefix_hamming_le_24',
            'family_id': 'f1',
            'member_count': 2,
            'boundary_count': 2,
            'best_truth': 0.55,
            'best_trust': 0.20,
            'best_archive_uplift': 0.0,
            'best_full_uplift': 0.0,
            'family_persistence_count': 2,
            'family_role_label': 'challenger_like',
            'truth_trend_label': 'improves',
            'trust_trend_label': 'mixed',
            'archive_uplift_trend_label': 'flat',
            'boundaries_seen': 'phaseC_start|stage35_seed',
        },
        {
            'artifact_path': 'output/test/1311.json',
            'run_id': 'run-1311',
            'key_seed': 1311,
            'target_panel_name': 'pressure',
            'target_panel_role': 'falsification',
            'study_role': 'discriminator',
            'family_view_id': 'prefix_hamming_le_24',
            'family_id': 'f2',
            'member_count': 2,
            'boundary_count': 2,
            'best_truth': 0.45,
            'best_trust': 0.35,
            'best_archive_uplift': 0.02,
            'best_full_uplift': 0.01,
            'family_persistence_count': 1,
            'family_role_label': 'anchor_like',
            'truth_trend_label': 'mixed',
            'trust_trend_label': 'improves',
            'archive_uplift_trend_label': 'mixed',
            'boundaries_seen': 'phaseC_start|stage35_archive',
        },
    ]
    digest_rows = mod._build_family_quality_case_digest(
        family_rows,
        [_run_row(1311, would_dump=1, rule_id='trust0.30_xent24.0_rival0.00_family1', panel='pressure')],
        [_case_row(1311, 'trust_false_fire', panel='pressure')],
    )
    assert digest_rows[0]['truth_winner_family_id'] == 'f1'
    assert digest_rows[0]['trust_winner_family_id'] == 'f2'
    assert digest_rows[0]['family_quality_read_label'] == 'trust_false_fire_family_looks_weak'


def test_family_quality_case_digest_handles_reference_wins() -> None:
    family_rows = [
        {
            'artifact_path': 'output/test/611.json',
            'run_id': 'run-611',
            'key_seed': 611,
            'target_panel_name': 'core',
            'target_panel_role': 'benchmark',
            'study_role': 'reference',
            'family_view_id': 'prefix_hamming_le_24',
            'family_id': 'f1',
            'member_count': 3,
            'boundary_count': 3,
            'best_truth': 0.7,
            'best_trust': 0.3,
            'best_archive_uplift': 0.2,
            'best_full_uplift': 0.25,
            'family_persistence_count': 3,
            'family_role_label': 'anchor_like',
            'truth_trend_label': 'improves',
            'trust_trend_label': 'improves',
            'archive_uplift_trend_label': 'improves',
            'boundaries_seen': 'phaseC_start|stage35_seed|stage35_archive',
        },
    ]
    digest_rows = mod._build_family_quality_case_digest(
        family_rows,
        [_run_row(611, would_dump=1, rule_id='trust0.30_xent24.0_rival0.00_family1')],
        [_case_row(611, '')],
    )
    assert digest_rows[0]['study_role'] == 'reference'
    assert digest_rows[0]['truth_winner_family_id'] == 'f1'


def test_family_quality_case_digest_marks_archive_false_fire_family_as_weak_when_truth_is_low() -> None:
    family_rows = [
        {
            'artifact_path': 'output/test/1411.json',
            'run_id': 'run-1411',
            'key_seed': 1411,
            'target_panel_name': 'pressure',
            'target_panel_role': 'falsification',
            'study_role': 'discriminator',
            'family_view_id': 'prefix_hamming_le_24',
            'family_id': 'f1',
            'member_count': 2,
            'boundary_count': 2,
            'best_truth': 0.302,
            'best_trust': 0.0,
            'best_archive_uplift': 0.499,
            'best_full_uplift': 0.0,
            'family_persistence_count': 2,
            'family_role_label': 'challenger_like',
            'truth_trend_label': 'improves',
            'trust_trend_label': 'flat',
            'archive_uplift_trend_label': 'improves',
            'boundaries_seen': 'phaseC_start|stage35_seed',
        },
        {
            'artifact_path': 'output/test/1411.json',
            'run_id': 'run-1411',
            'key_seed': 1411,
            'target_panel_name': 'pressure',
            'target_panel_role': 'falsification',
            'study_role': 'discriminator',
            'family_view_id': 'prefix_hamming_le_24',
            'family_id': 'f0',
            'member_count': 3,
            'boundary_count': 3,
            'best_truth': 0.276,
            'best_trust': 0.0,
            'best_archive_uplift': 0.182,
            'best_full_uplift': 0.003,
            'family_persistence_count': 3,
            'family_role_label': 'mixed',
            'truth_trend_label': 'mixed',
            'trust_trend_label': 'flat',
            'archive_uplift_trend_label': 'improves',
            'boundaries_seen': 'phaseC_start|stage35_seed|stage35_archive',
        },
    ]
    digest_rows = mod._build_family_quality_case_digest(
        family_rows,
        [_run_row(1411, would_dump=1, rule_id='archive_search_uplift0.15', panel='pressure')],
        [_case_row(1411, 'archive_false_fire', panel='pressure')],
    )
    assert digest_rows[0]['family_quality_read_label'] == 'archive_false_fire_family_looks_weak'


def test_family_quality_cases_markdown_includes_all_study_seeds(tmp_path: Path) -> None:
    rows = []
    for seed in mod.FAMILY_QUALITY_STUDY_SEEDS:
        rows.append({
            'key_seed': seed,
            'study_role': 'discriminator' if seed in mod.FAMILY_QUALITY_DISCRIMINATOR_SEEDS else 'reference',
            'would_dump': 0,
            'would_stop': 0,
            'shadow_rule_id': '',
            'case_shape_label': '',
            'truth_winner_family_id': 'f1',
            'trust_winner_family_id': 'f1',
            'archive_uplift_winner_family_id': 'f1',
            'full_uplift_winner_family_id': 'f1',
            'persistence_winner_family_id': 'f1',
            'winner_family_agreement_label': 'all_agree',
            'truth_winner_best_truth': 0.5,
            'truth_winner_family_role_label': 'anchor_like',
            'truth_winner_family_persistence_count': 2,
            'truth_winner_truth_trend_label': 'improves',
            'truth_winner_boundaries_seen': 'phaseC_start|stage35_archive',
            'trust_winner_best_truth': 0.5,
            'trust_winner_family_role_label': 'anchor_like',
            'trust_winner_family_persistence_count': 2,
            'trust_winner_truth_trend_label': 'improves',
            'trust_winner_boundaries_seen': 'phaseC_start|stage35_archive',
            'archive_winner_best_truth': 0.5,
            'archive_winner_best_archive_uplift': 0.2,
            'archive_winner_family_role_label': 'anchor_like',
            'archive_winner_family_persistence_count': 2,
            'archive_winner_truth_trend_label': 'improves',
            'archive_winner_archive_uplift_trend_label': 'mixed',
            'archive_winner_boundaries_seen': 'phaseC_start|stage35_archive',
            'full_uplift_winner_best_truth': 0.5,
            'full_uplift_winner_best_full_uplift': 0.03,
            'full_uplift_winner_family_role_label': 'anchor_like',
            'full_uplift_winner_family_persistence_count': 2,
            'full_uplift_winner_truth_trend_label': 'improves',
            'full_uplift_winner_full_uplift_trend_label': 'flat',
            'full_uplift_winner_boundaries_seen': 'phaseC_start|stage35_archive',
            'persistence_winner_family_persistence_count': 2,
            'persistence_winner_family_role_label': 'anchor_like',
            'persistence_winner_boundaries_seen': 'phaseC_start|stage35_archive',
            'family_quality_read_label': 'family_level_signal_inconclusive',
        })
    mod._write_case_markdown(tmp_path, rows)
    text = (tmp_path / 'family_quality_cases.md').read_text(encoding='utf-8')
    for seed in mod.FAMILY_QUALITY_STUDY_SEEDS:
        assert f'Seed {seed}' in text


def test_family_quality_cases_markdown_uses_metric_specific_value_and_trend_columns(tmp_path: Path) -> None:
    rows = [{
        'key_seed': 1111,
        'study_role': 'discriminator',
        'would_dump': 0,
        'would_stop': 0,
        'shadow_rule_id': '',
        'case_shape_label': 'accepted_miss_outside_current_model',
        'truth_winner_family_id': 'f0',
        'trust_winner_family_id': 'f1',
        'archive_uplift_winner_family_id': 'f2',
        'archive_winner_family_id': 'f2',
        'full_uplift_winner_family_id': 'f3',
        'persistence_winner_family_id': 'f4',
        'winner_family_agreement_label': 'split',
        'truth_winner_best_truth': 0.528,
        'truth_winner_family_role_label': 'mixed',
        'truth_winner_family_persistence_count': 3,
        'truth_winner_truth_trend_label': 'improves',
        'truth_winner_boundaries_seen': 'phaseC_start|stage35_seed|stage35_archive',
        'trust_winner_best_trust': 0.167,
        'trust_winner_family_role_label': 'challenger_like',
        'trust_winner_family_persistence_count': 2,
        'trust_winner_trust_trend_label': 'degrades',
        'trust_winner_boundaries_seen': 'phaseC_start|stage35_seed',
        'archive_winner_best_archive_uplift': 0.225,
        'archive_winner_family_role_label': 'anchor_like',
        'archive_winner_family_persistence_count': 2,
        'archive_winner_archive_uplift_trend_label': 'flat',
        'archive_winner_boundaries_seen': 'phaseC_start|stage35_seed',
        'full_uplift_winner_best_full_uplift': 0.013,
        'full_uplift_winner_family_role_label': 'mixed',
        'full_uplift_winner_family_persistence_count': 3,
        'full_uplift_winner_full_uplift_trend_label': 'mixed',
        'full_uplift_winner_boundaries_seen': 'phaseC_start|stage35_seed|stage35_archive',
        'persistence_winner_family_persistence_count': 3,
        'persistence_winner_family_role_label': 'mixed',
        'persistence_winner_boundaries_seen': 'phaseC_start|stage35_seed|stage35_archive',
        'family_quality_read_label': 'accepted_miss_family_looks_real',
    }]
    mod._write_case_markdown(tmp_path, rows)
    text = (tmp_path / 'family_quality_cases.md').read_text(encoding='utf-8')
    assert '| metric | family id | best value | role | persistence | boundaries seen | trend |' in text
    assert '| trust | f1 | 0.167 | challenger_like | 2 | phaseC_start|stage35_seed | degrades |' in text
    assert '| archive uplift | f2 | 0.225 | anchor_like | 2 | phaseC_start|stage35_seed | flat |' in text
    assert '| full uplift | f3 | 0.013 | mixed | 3 | phaseC_start|stage35_seed|stage35_archive | mixed |' in text
    assert '| persistence | f4 | 3 | mixed | 3 | phaseC_start|stage35_seed|stage35_archive | na |' in text
