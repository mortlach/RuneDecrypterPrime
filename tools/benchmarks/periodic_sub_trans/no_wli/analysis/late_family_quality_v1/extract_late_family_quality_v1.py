from __future__ import annotations

import datetime as dt
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


def _find_repo_root() -> Path:
    here = Path(__file__).resolve()
    for parent in [here] + list(here.parents):
        if (parent / 'src').exists() and (parent / 'tools').exists():
            return parent
    raise RuntimeError('Could not locate repo root from extract_late_family_quality_v1.py')


REPO_ROOT = _find_repo_root()
INPUT_SCORE_STOP_BUNDLE_DIR = REPO_ROOT / Path(
    'output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/'
    'score_stop_shadow_v2/20260408T041415Z__score_stop_shadow_v2'
)
OUTPUT_BASE_DIR = (
    REPO_ROOT
    / 'output'
    / 'tools'
    / 'benchmarks'
    / 'periodic_sub_trans'
    / 'no_wli'
    / 'analysis'
    / 'late_family_quality_v1'
)
REQUIRED_INPUT_FILES = (
    'row_scores.jsonl',
    'run_shadow_summary.jsonl',
    'case_explanations.jsonl',
)
OPTIONAL_INPUT_FILES = (
    'threshold_matrix_rows.jsonl',
)
FAMILY_QUALITY_DISCRIMINATOR_SEEDS = (1111, 1311, 1411)
FAMILY_QUALITY_REFERENCE_WIN_SEEDS = (411, 611, 1011)
FAMILY_QUALITY_STUDY_SEEDS = (
    1111, 1311, 1411,
    411, 611, 1011,
)
LATE_BOUNDARY_ORDER = {
    'phaseC_start': 1,
    'stage35_seed': 2,
    'stage35_archive': 3,
}
TREND_EPS = 1e-9


def _safe_str(value: Any) -> str:
    return str(value or '')


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return int(default)


def _safe_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return float('nan')


def _is_finite(value: Any) -> bool:
    return math.isfinite(_safe_float(value))


def _json_default(value: Any) -> Any:
    if isinstance(value, float) and not math.isfinite(value):
        return None
    raise TypeError(f'Object of type {type(value)!r} is not JSON serializable')


def _relative_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open('r', encoding='utf-8') as handle:
        for line in handle:
            text = line.strip()
            if not text:
                continue
            rows.append(dict(json.loads(text)))
    return rows


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, default=_json_default) + '\n', encoding='utf-8')


def _write_jsonl(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    with path.open('w', encoding='utf-8') as handle:
        for row in rows:
            handle.write(json.dumps(dict(row), sort_keys=True, default=_json_default))
            handle.write('\n')


def _require_input_bundle_files(bundle_dir: Path) -> dict[str, Path]:
    resolved: dict[str, Path] = {}
    missing = [name for name in REQUIRED_INPUT_FILES if not (bundle_dir / name).exists()]
    if missing:
        missing_list = ', '.join(sorted(missing))
        raise FileNotFoundError(f'Missing required late_family_quality_v1 input files: {missing_list}')
    for name in REQUIRED_INPUT_FILES + OPTIONAL_INPUT_FILES:
        path = bundle_dir / name
        if path.exists():
            resolved[name] = path
    return resolved


def _read_row_scores(bundle_dir: Path) -> list[dict[str, Any]]:
    return _read_jsonl(bundle_dir / 'row_scores.jsonl')


def _read_run_shadow_summary(bundle_dir: Path) -> list[dict[str, Any]]:
    return _read_jsonl(bundle_dir / 'run_shadow_summary.jsonl')


def _read_case_explanations(bundle_dir: Path) -> list[dict[str, Any]]:
    return _read_jsonl(bundle_dir / 'case_explanations.jsonl')


def _read_threshold_matrix_rows(bundle_dir: Path) -> list[dict[str, Any]]:
    path = bundle_dir / 'threshold_matrix_rows.jsonl'
    if not path.exists():
        return []
    return _read_jsonl(path)


def _study_role_for_seed(key_seed: int) -> str:
    if key_seed in FAMILY_QUALITY_DISCRIMINATOR_SEEDS:
        return 'discriminator'
    if key_seed in FAMILY_QUALITY_REFERENCE_WIN_SEEDS:
        return 'reference'
    raise KeyError(f'Unexpected study seed: {key_seed}')


def _select_study_rows(rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    selected = [dict(row) for row in rows if _safe_int(row.get('key_seed')) in FAMILY_QUALITY_STUDY_SEEDS]
    present = {_safe_int(row.get('key_seed')) for row in selected}
    missing = [seed for seed in FAMILY_QUALITY_STUDY_SEEDS if seed not in present]
    if missing:
        raise ValueError(f'Missing study seeds from frozen input bundle: {missing}')
    return selected


def _select_case_rows(rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    selected = [dict(row) for row in rows if _safe_int(row.get('key_seed')) in FAMILY_QUALITY_STUDY_SEEDS]
    present = {_safe_int(row.get('key_seed')) for row in selected}
    missing = [seed for seed in FAMILY_QUALITY_DISCRIMINATOR_SEEDS if seed not in present]
    if missing:
        raise ValueError(f'Missing case explanation rows for discriminator seeds: {missing}')
    return selected


def _boundary_rank(boundary: Any) -> int:
    return int(LATE_BOUNDARY_ORDER.get(_safe_str(boundary), 0))


def _lane_counts(rows: Sequence[Mapping[str, Any]]) -> tuple[int, int, int]:
    anchor_count = 0
    challenger_count = 0
    blank_count = 0
    for row in rows:
        lane = _safe_str(row.get('lane')).strip()
        if lane == 'anchor':
            anchor_count += 1
        elif lane:
            challenger_count += 1
        else:
            blank_count += 1
    return anchor_count, challenger_count, blank_count


def _family_role_label(anchor_row_count: int, challenger_row_count: int) -> str:
    if anchor_row_count > 0 and challenger_row_count == 0:
        return 'anchor_like'
    if challenger_row_count > 0 and anchor_row_count == 0:
        return 'challenger_like'
    if anchor_row_count > 0 and challenger_row_count > 0:
        return 'mixed'
    return 'unknown'


def _join_boundaries(boundaries: Iterable[str]) -> str:
    ordered = sorted({_safe_str(boundary) for boundary in boundaries if _safe_str(boundary)}, key=_boundary_rank)
    return '|'.join(ordered)


def _pick_best_row(
    rows: Sequence[Mapping[str, Any]],
    *,
    metric_key: str,
    higher_is_better: bool = True,
) -> dict[str, Any]:
    best_row: dict[str, Any] | None = None
    best_sort_key: tuple[Any, ...] | None = None
    for row in rows:
        metric = _safe_float(row.get(metric_key))
        if not _is_finite(metric):
            continue
        sort_metric = metric if higher_is_better else -metric
        sort_key = (
            sort_metric,
            _boundary_rank(row.get('stage_boundary')),
            _safe_str(row.get('candidate_hash')),
        )
        if best_sort_key is None or sort_key > best_sort_key:
            best_sort_key = sort_key
            best_row = dict(row)
    return best_row or {}


def _boundary_best_row(
    rows: Sequence[Mapping[str, Any]],
    *,
    metric_key: str,
    higher_is_better: bool = True,
) -> dict[str, Any]:
    return _pick_best_row(rows, metric_key=metric_key, higher_is_better=higher_is_better)


def _metric_trend_label(values: Sequence[float]) -> str:
    finite_values = [float(value) for value in values if _is_finite(value)]
    if len(finite_values) < 2:
        return 'insufficient_data'
    deltas = [finite_values[idx + 1] - finite_values[idx] for idx in range(len(finite_values) - 1)]
    if all(delta > TREND_EPS for delta in deltas):
        return 'improves'
    if all(delta < -TREND_EPS for delta in deltas):
        return 'degrades'
    if all(abs(delta) <= TREND_EPS for delta in deltas):
        return 'flat'
    return 'mixed'


def _trend_values_for_metric(family_row: Mapping[str, Any], metric_stem: str) -> list[float]:
    values: list[float] = []
    for boundary in ('phasec_start', 'stage35_seed', 'stage35_archive'):
        values.append(_safe_float(family_row.get(f'{boundary}_{metric_stem}')))
    return values


def _first_nonempty_string(values: Sequence[Any]) -> str:
    for value in values:
        text = _safe_str(value)
        if text:
            return text
    return ''


def _max_finite(values: Sequence[Any]) -> float:
    finite = [_safe_float(value) for value in values if _is_finite(value)]
    if not finite:
        return float('nan')
    return max(finite)


def _min_finite(values: Sequence[Any]) -> float:
    finite = [_safe_float(value) for value in values if _is_finite(value)]
    if not finite:
        return float('nan')
    return min(finite)


def _build_family_rows(row_rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str, int, str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in row_rows:
        boundary = _safe_str(row.get('stage_boundary'))
        if boundary not in LATE_BOUNDARY_ORDER:
            continue
        family_id = _safe_str(row.get('family_id'))
        family_view_id = _safe_str(row.get('family_view_id'))
        if not family_id:
            continue
        key = (
            _safe_str(row.get('artifact_path')),
            _safe_str(row.get('run_id')),
            _safe_int(row.get('key_seed')),
            family_view_id,
            family_id,
        )
        grouped[key].append(dict(row))
    family_rows: list[dict[str, Any]] = []
    for key, rows in sorted(grouped.items(), key=lambda item: (item[0][2], item[0][4], item[0][0])):
        artifact_path, run_id, key_seed, family_view_id, family_id = key
        anchor_row_count, challenger_row_count, blank_lane_row_count = _lane_counts(rows)
        boundaries_seen = sorted({_safe_str(row.get('stage_boundary')) for row in rows}, key=_boundary_rank)
        best_truth_row = _pick_best_row(rows, metric_key='replay_truth_match')
        best_trust_row = _pick_best_row(rows, metric_key='replay_word_ngram_trust_score')
        best_archive_uplift_row = _pick_best_row(rows, metric_key='shadow_late_family_search_uplift')
        best_full_uplift_row = _pick_best_row(rows, metric_key='shadow_late_family_full_uplift')
        best_xent_row = _pick_best_row(rows, metric_key='replay_word_ngram_report_xent', higher_is_better=False)
        persistence_rows = sorted(
            rows,
            key=lambda row: (
                _safe_int(row.get('shadow_late_family_persistence_count')),
                len(_safe_str(row.get('shadow_late_family_persistence_boundaries'))),
                _boundary_rank(row.get('stage_boundary')),
                _safe_str(row.get('candidate_hash')),
            ),
            reverse=True,
        )
        persistence_row = dict(persistence_rows[0]) if persistence_rows else {}
        family_row: dict[str, Any] = {
            'artifact_path': artifact_path,
            'run_id': run_id,
            'key_seed': key_seed,
            'target_panel_name': _first_nonempty_string([row.get('target_panel_name') for row in rows]),
            'target_panel_role': _first_nonempty_string([row.get('target_panel_role') for row in rows]),
            'study_role': _study_role_for_seed(key_seed),
            'run_type': _first_nonempty_string([row.get('run_type') for row in rows]),
            'family_view_id': family_view_id,
            'family_id': family_id,
            'member_count': len(rows),
            'boundaries_seen': _join_boundaries(boundaries_seen),
            'boundary_count': len(boundaries_seen),
            'has_phasec_start': int('phaseC_start' in boundaries_seen),
            'has_stage35_seed': int('stage35_seed' in boundaries_seen),
            'has_stage35_archive': int('stage35_archive' in boundaries_seen),
            'anchor_row_count': anchor_row_count,
            'challenger_row_count': challenger_row_count,
            'blank_lane_row_count': blank_lane_row_count,
            'min_distance_to_anchor': _min_finite([row.get('distance_to_anchor') for row in rows]),
            'max_distance_to_anchor': _max_finite([row.get('distance_to_anchor') for row in rows]),
            'family_role_label': _family_role_label(anchor_row_count, challenger_row_count),
            'family_persistence_count': _safe_int(persistence_row.get('shadow_late_family_persistence_count')),
            'family_persistence_boundaries': _safe_str(
                persistence_row.get('shadow_late_family_persistence_boundaries')
            ),
            'family_reaches_archive': int(_safe_int(persistence_row.get('shadow_late_family_reaches_archive')) > 0),
        }
        peak_specs = (
            ('truth', best_truth_row, 'replay_truth_match'),
            ('trust', best_trust_row, 'replay_word_ngram_trust_score'),
            ('archive_uplift', best_archive_uplift_row, 'shadow_late_family_search_uplift'),
            ('full_uplift', best_full_uplift_row, 'shadow_late_family_full_uplift'),
            ('xent', best_xent_row, 'replay_word_ngram_report_xent'),
        )
        for stem, best_row, metric_key in peak_specs:
            family_row[f'best_{stem}'] = _safe_float(best_row.get(metric_key))
            family_row[f'best_{stem}_candidate_hash'] = _safe_str(best_row.get('candidate_hash'))
            family_row[f'best_{stem}_stage_boundary'] = _safe_str(best_row.get('stage_boundary'))
            if stem != 'xent':
                family_row[f'best_{stem}_boundary_rank'] = _boundary_rank(best_row.get('stage_boundary'))
        for boundary_name, boundary_label in (
            ('phaseC_start', 'phasec_start'),
            ('stage35_seed', 'stage35_seed'),
            ('stage35_archive', 'stage35_archive'),
        ):
            boundary_rows = [row for row in rows if _safe_str(row.get('stage_boundary')) == boundary_name]
            family_row[f'{boundary_label}_member_count'] = len(boundary_rows)
            boundary_truth_row = _boundary_best_row(boundary_rows, metric_key='replay_truth_match')
            boundary_trust_row = _boundary_best_row(boundary_rows, metric_key='replay_word_ngram_trust_score')
            boundary_archive_row = _boundary_best_row(boundary_rows, metric_key='shadow_late_family_search_uplift')
            boundary_full_row = _boundary_best_row(boundary_rows, metric_key='shadow_late_family_full_uplift')
            family_row[f'{boundary_label}_best_truth'] = _safe_float(boundary_truth_row.get('replay_truth_match'))
            family_row[f'{boundary_label}_best_trust'] = _safe_float(boundary_trust_row.get('replay_word_ngram_trust_score'))
            family_row[f'{boundary_label}_best_archive_uplift'] = _safe_float(boundary_archive_row.get('shadow_late_family_search_uplift'))
            family_row[f'{boundary_label}_best_full_uplift'] = _safe_float(boundary_full_row.get('shadow_late_family_full_uplift'))
        family_row['truth_trend_label'] = _metric_trend_label(_trend_values_for_metric(family_row, 'best_truth'))
        family_row['trust_trend_label'] = _metric_trend_label(_trend_values_for_metric(family_row, 'best_trust'))
        family_row['archive_uplift_trend_label'] = _metric_trend_label(_trend_values_for_metric(family_row, 'best_archive_uplift'))
        family_row['full_uplift_trend_label'] = _metric_trend_label(_trend_values_for_metric(family_row, 'best_full_uplift'))
        family_rows.append(family_row)
    return family_rows


def _pick_family_winner_by_metric(
    family_rows: Sequence[Mapping[str, Any]],
    *,
    metric_key: str,
) -> dict[str, Any]:
    best_row: dict[str, Any] | None = None
    best_sort_key: tuple[Any, ...] | None = None
    for row in family_rows:
        metric = _safe_float(row.get(metric_key))
        if not _is_finite(metric):
            continue
        family_id = _safe_str(row.get('family_id'))
        family_id_tiebreak = tuple(-ord(ch) for ch in family_id)
        sort_key = (
            metric,
            _safe_int(row.get('boundary_count')),
            _safe_int(row.get('member_count')),
            family_id_tiebreak,
        )
        if best_sort_key is None or sort_key > best_sort_key:
            best_sort_key = sort_key
            best_row = dict(row)
    return best_row or {}


def _winner_family_agreement_label(
    truth_family_id: str,
    trust_family_id: str,
    archive_family_id: str,
    full_uplift_family_id: str,
    persistence_family_id: str,
) -> str:
    truth = _safe_str(truth_family_id)
    trust = _safe_str(trust_family_id)
    archive = _safe_str(archive_family_id)
    full_uplift = _safe_str(full_uplift_family_id)
    persistence = _safe_str(persistence_family_id)
    if not truth:
        return 'insufficient_data'
    available = [value for value in (truth, trust, archive, full_uplift, persistence) if value]
    if len(available) < 2:
        return 'insufficient_data'
    if all(value == truth for value in available):
        return 'all_agree'
    if truth == trust and truth != archive and truth != full_uplift and truth != persistence:
        return 'truth_trust_agree_only'
    if truth == archive and truth != trust and truth != full_uplift and truth != persistence:
        return 'truth_archive_agree_only'
    if truth != trust and truth != archive and truth != full_uplift and truth != persistence:
        return 'truth_only'
    return 'split'


def _copy_family_trait_fields(prefix: str, family_row: Mapping[str, Any], target: dict[str, Any]) -> None:
    target[f'{prefix}_family_id'] = _safe_str(family_row.get('family_id'))
    target[f'{prefix}_best_truth'] = _safe_float(family_row.get('best_truth'))
    target[f'{prefix}_best_trust'] = _safe_float(family_row.get('best_trust'))
    target[f'{prefix}_best_archive_uplift'] = _safe_float(family_row.get('best_archive_uplift'))
    target[f'{prefix}_best_full_uplift'] = _safe_float(family_row.get('best_full_uplift'))
    target[f'{prefix}_family_persistence_count'] = _safe_int(family_row.get('family_persistence_count'))
    target[f'{prefix}_family_role_label'] = _safe_str(family_row.get('family_role_label'))
    target[f'{prefix}_truth_trend_label'] = _safe_str(family_row.get('truth_trend_label'))
    target[f'{prefix}_trust_trend_label'] = _safe_str(family_row.get('trust_trend_label'))
    target[f'{prefix}_archive_uplift_trend_label'] = _safe_str(family_row.get('archive_uplift_trend_label'))
    target[f'{prefix}_full_uplift_trend_label'] = _safe_str(family_row.get('full_uplift_trend_label'))
    target[f'{prefix}_boundaries_seen'] = _safe_str(family_row.get('boundaries_seen'))


def _label_family_quality_read(case_row: Mapping[str, Any]) -> str:
    case_shape = _safe_str(case_row.get('case_shape_label'))
    truth_winner = _safe_str(case_row.get('truth_winner_family_id'))
    trust_winner = _safe_str(case_row.get('trust_winner_family_id'))
    archive_winner = _safe_str(case_row.get('archive_uplift_winner_family_id'))
    truth_best_truth = _safe_float(case_row.get('truth_winner_best_truth'))
    truth_persistence = _safe_int(case_row.get('truth_winner_family_persistence_count'))
    truth_role = _safe_str(case_row.get('truth_winner_family_role_label'))
    trust_best_truth = _safe_float(case_row.get('trust_winner_best_truth'))
    archive_best_truth = _safe_float(case_row.get('archive_winner_best_truth'))
    if case_shape == 'accepted_miss_outside_current_model':
        if _is_finite(truth_best_truth) and truth_best_truth >= 0.45 and truth_persistence >= 2:
            return 'accepted_miss_family_looks_real'
        return 'family_level_signal_inconclusive'
    if case_shape == 'trust_false_fire':
        if truth_winner and trust_winner and truth_winner != trust_winner:
            return 'trust_false_fire_family_looks_weak'
        if truth_role == 'challenger_like' and truth_persistence >= 2 and _is_finite(truth_best_truth):
            return 'trust_false_fire_family_looks_weak'
        if _is_finite(trust_best_truth) and _is_finite(truth_best_truth) and trust_best_truth + TREND_EPS < truth_best_truth:
            return 'trust_false_fire_family_looks_weak'
        return 'truth_trust_split'
    if case_shape == 'archive_false_fire':
        if truth_winner and archive_winner and truth_winner != archive_winner:
            return 'archive_false_fire_family_looks_weak'
        if _is_finite(truth_best_truth) and truth_best_truth <= 0.35:
            return 'archive_false_fire_family_looks_weak'
        if _is_finite(archive_best_truth) and _is_finite(truth_best_truth) and archive_best_truth + TREND_EPS < truth_best_truth:
            return 'archive_false_fire_family_looks_weak'
        return 'truth_uplift_split'
    if truth_winner and trust_winner and truth_winner != trust_winner:
        return 'truth_trust_split'
    if truth_winner and archive_winner and truth_winner != archive_winner:
        return 'truth_uplift_split'
    return 'family_level_signal_inconclusive'


def _select_family_rows_for_seed(
    family_rows: Sequence[Mapping[str, Any]],
    *,
    key_seed: int,
) -> list[dict[str, Any]]:
    rows = [dict(row) for row in family_rows if _safe_int(row.get('key_seed')) == key_seed]
    if not rows:
        raise ValueError(f'Missing family rows for study seed {key_seed}')
    return rows


def _build_family_quality_case_digest(
    family_rows: Sequence[Mapping[str, Any]],
    run_rows: Sequence[Mapping[str, Any]],
    case_rows: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    run_by_seed = {_safe_int(row.get('key_seed')): dict(row) for row in run_rows}
    case_by_seed = {_safe_int(row.get('key_seed')): dict(row) for row in case_rows}
    seed_order = [
        seed
        for seed in FAMILY_QUALITY_STUDY_SEEDS
        if seed in {_safe_int(row.get('key_seed')) for row in family_rows}
    ]
    digest_rows: list[dict[str, Any]] = []
    for key_seed in seed_order:
        seed_family_rows = _select_family_rows_for_seed(family_rows, key_seed=key_seed)
        run_row = run_by_seed.get(key_seed)
        if run_row is None:
            raise ValueError(f'Missing run summary for study seed {key_seed}')
        case_row = case_by_seed.get(key_seed, {})
        truth_winner = _pick_family_winner_by_metric(seed_family_rows, metric_key='best_truth')
        trust_winner = _pick_family_winner_by_metric(seed_family_rows, metric_key='best_trust')
        archive_winner = _pick_family_winner_by_metric(seed_family_rows, metric_key='best_archive_uplift')
        full_uplift_winner = _pick_family_winner_by_metric(seed_family_rows, metric_key='best_full_uplift')
        persistence_winner = _pick_family_winner_by_metric(seed_family_rows, metric_key='family_persistence_count')
        digest_row: dict[str, Any] = {
            'key_seed': key_seed,
            'study_role': _study_role_for_seed(key_seed),
            'target_panel_name': _safe_str(run_row.get('target_panel_name')),
            'target_panel_role': _safe_str(run_row.get('target_panel_role')),
            'run_type': _safe_str(run_row.get('run_type')),
            'would_dump': _safe_int(run_row.get('would_dump')),
            'would_stop': _safe_int(run_row.get('would_stop')),
            'shadow_rule_id': _safe_str(run_row.get('shadow_rule_id')),
            'case_shape_label': _safe_str(case_row.get('case_shape_label')),
            'truth_winner_family_id': _safe_str(truth_winner.get('family_id')),
            'trust_winner_family_id': _safe_str(trust_winner.get('family_id')),
            'archive_uplift_winner_family_id': _safe_str(archive_winner.get('family_id')),
            'full_uplift_winner_family_id': _safe_str(full_uplift_winner.get('family_id')),
            'persistence_winner_family_id': _safe_str(persistence_winner.get('family_id')),
        }
        digest_row['truth_equals_trust_family'] = int(
            _safe_str(digest_row['truth_winner_family_id'])
            and digest_row['truth_winner_family_id'] == digest_row['trust_winner_family_id']
        )
        digest_row['truth_equals_archive_uplift_family'] = int(
            _safe_str(digest_row['truth_winner_family_id'])
            and digest_row['truth_winner_family_id'] == digest_row['archive_uplift_winner_family_id']
        )
        digest_row['truth_equals_full_uplift_family'] = int(
            _safe_str(digest_row['truth_winner_family_id'])
            and digest_row['truth_winner_family_id'] == digest_row['full_uplift_winner_family_id']
        )
        digest_row['truth_equals_persistence_family'] = int(
            _safe_str(digest_row['truth_winner_family_id'])
            and digest_row['truth_winner_family_id'] == digest_row['persistence_winner_family_id']
        )
        digest_row['trust_equals_archive_uplift_family'] = int(
            _safe_str(digest_row['trust_winner_family_id'])
            and digest_row['trust_winner_family_id'] == digest_row['archive_uplift_winner_family_id']
        )
        digest_row['winner_family_agreement_label'] = _winner_family_agreement_label(
            _safe_str(digest_row['truth_winner_family_id']),
            _safe_str(digest_row['trust_winner_family_id']),
            _safe_str(digest_row['archive_uplift_winner_family_id']),
            _safe_str(digest_row['full_uplift_winner_family_id']),
            _safe_str(digest_row['persistence_winner_family_id']),
        )
        _copy_family_trait_fields('truth_winner', truth_winner, digest_row)
        if trust_winner:
            _copy_family_trait_fields('trust_winner', trust_winner, digest_row)
        if archive_winner:
            _copy_family_trait_fields('archive_winner', archive_winner, digest_row)
        if full_uplift_winner:
            _copy_family_trait_fields('full_uplift_winner', full_uplift_winner, digest_row)
        if persistence_winner:
            _copy_family_trait_fields('persistence_winner', persistence_winner, digest_row)
        digest_row['family_quality_read_label'] = _label_family_quality_read(digest_row)
        digest_rows.append(digest_row)
    return digest_rows


def _build_family_quality_summary(
    family_rows: Sequence[Mapping[str, Any]],
    digest_rows: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    read_counts = Counter(_safe_str(row.get('family_quality_read_label')) for row in digest_rows)
    agreement_counts = Counter(_safe_str(row.get('winner_family_agreement_label')) for row in digest_rows)
    role_counts = Counter(_safe_str(row.get('study_role')) for row in digest_rows)
    seeds_by_read: dict[str, list[int]] = defaultdict(list)
    for row in digest_rows:
        seeds_by_read[_safe_str(row.get('family_quality_read_label'))].append(_safe_int(row.get('key_seed')))
    return {
        'input_bundle_dir': _relative_path(INPUT_SCORE_STOP_BUNDLE_DIR),
        'study_seed_count': len(FAMILY_QUALITY_STUDY_SEEDS),
        'family_row_count': len(family_rows),
        'study_role_counts': dict(sorted(role_counts.items())),
        'winner_family_agreement_counts': dict(sorted(agreement_counts.items())),
        'family_quality_read_counts': dict(sorted(read_counts.items())),
        'seeds_by_read_label': {key: sorted(values) for key, values in sorted(seeds_by_read.items())},
    }


def _metric_display(value: Any) -> str:
    number = _safe_float(value)
    if not _is_finite(number):
        return 'na'
    return f'{number:.3f}'


def _winner_table_row_fields(metric_label: str, prefix: str) -> tuple[str, str | None]:
    if metric_label == 'truth':
        return f'{prefix}_best_truth', f'{prefix}_truth_trend_label'
    if metric_label == 'trust':
        return f'{prefix}_best_trust', f'{prefix}_trust_trend_label'
    if metric_label == 'archive uplift':
        return f'{prefix}_best_archive_uplift', f'{prefix}_archive_uplift_trend_label'
    if metric_label == 'full uplift':
        return f'{prefix}_best_full_uplift', f'{prefix}_full_uplift_trend_label'
    if metric_label == 'persistence':
        return f'{prefix}_family_persistence_count', None
    raise KeyError(f'Unsupported winner-table metric label: {metric_label}')


def _winner_metric_value_text(metric_label: str, value: Any) -> str:
    if metric_label == 'persistence':
        return str(_safe_int(value))
    return _metric_display(value)


def _winner_table_row(metric_label: str, prefix: str, digest_row: Mapping[str, Any]) -> str:
    family_id = _safe_str(digest_row.get(f'{prefix}_family_id'))
    if not family_id:
        return f'| {metric_label} | na | na | na | na | na | na |'
    value_key, trend_key = _winner_table_row_fields(metric_label, prefix)
    trend_text = 'na' if trend_key is None else (_safe_str(digest_row.get(trend_key)) or 'na')
    return (
        f"| {metric_label} | {family_id} | {_winner_metric_value_text(metric_label, digest_row.get(value_key))} | "
        f"{_safe_str(digest_row.get(f'{prefix}_family_role_label'))} | "
        f"{_safe_int(digest_row.get(f'{prefix}_family_persistence_count'))} | "
        f"{_safe_str(digest_row.get(f'{prefix}_boundaries_seen')) or 'na'} | "
        f"{trend_text} |"
    )


def _digest_bullets(row: Mapping[str, Any]) -> list[str]:
    truth_family = _safe_str(row.get('truth_winner_family_id')) or 'na'
    trust_family = _safe_str(row.get('trust_winner_family_id')) or 'na'
    archive_family = _safe_str(row.get('archive_uplift_winner_family_id')) or 'na'
    agreement = _safe_str(row.get('winner_family_agreement_label')) or 'na'
    truth_label = _safe_str(row.get('truth_winner_family_role_label')) or 'na'
    read_label = _safe_str(row.get('family_quality_read_label')) or 'na'
    return [
        f'truth/trust/archive agreement: `{agreement}` (`{truth_family}` / `{trust_family}` / `{archive_family}`)',
        f'truth-winning family: role `{truth_label}`, persistence `{_safe_int(row.get("truth_winner_family_persistence_count"))}`, truth trend `{_safe_str(row.get("truth_winner_truth_trend_label")) or "na"}`',
        f'family-level read: `{read_label}`',
    ]


def _write_case_markdown(output_dir: Path, digest_rows: Sequence[Mapping[str, Any]]) -> None:
    lines: list[str] = ['# Late Family Quality v1 Cases', '']
    for digest_row in digest_rows:
        key_seed = _safe_int(digest_row.get('key_seed'))
        lines.append(f'## Seed {key_seed}')
        lines.append('')
        lines.append(f'- Study role: `{_safe_str(digest_row.get("study_role"))}`')
        lines.append(
            f'- Current stop verdict: dump=`{_safe_int(digest_row.get("would_dump"))}` '
            f'stop=`{_safe_int(digest_row.get("would_stop"))}` '
            f'rule=`{_safe_str(digest_row.get("shadow_rule_id")) or "na"}`'
        )
        lines.append(f'- Stop case label: `{_safe_str(digest_row.get("case_shape_label")) or "na"}`')
        lines.append('')
        lines.append('| metric | family id | best value | role | persistence | boundaries seen | trend |')
        lines.append('| --- | --- | ---: | --- | ---: | --- | --- |')
        lines.append(_winner_table_row('truth', 'truth_winner', digest_row))
        lines.append(_winner_table_row('trust', 'trust_winner', digest_row))
        lines.append(_winner_table_row('archive uplift', 'archive_winner', digest_row))
        lines.append(_winner_table_row('full uplift', 'full_uplift_winner', digest_row))
        lines.append(_winner_table_row('persistence', 'persistence_winner', digest_row))
        lines.append('')
        for bullet in _digest_bullets(digest_row):
            lines.append(f'- {bullet}')
        lines.append('')
    (output_dir / 'family_quality_cases.md').write_text('\n'.join(lines).rstrip() + '\n', encoding='utf-8')


def main() -> None:
    _require_input_bundle_files(INPUT_SCORE_STOP_BUNDLE_DIR)
    row_rows = _select_study_rows(_read_row_scores(INPUT_SCORE_STOP_BUNDLE_DIR))
    run_rows = _select_study_rows(_read_run_shadow_summary(INPUT_SCORE_STOP_BUNDLE_DIR))
    case_rows = _select_case_rows(_read_case_explanations(INPUT_SCORE_STOP_BUNDLE_DIR))
    # Loaded only to validate frozen optional-file availability for future
    # follow-up studies. v1 does not consume the threshold matrix directly.
    _optional_threshold_rows = _read_threshold_matrix_rows(INPUT_SCORE_STOP_BUNDLE_DIR)

    family_rows = _build_family_rows(row_rows)
    digest_rows = _build_family_quality_case_digest(family_rows, run_rows, case_rows)
    summary = _build_family_quality_summary(family_rows, digest_rows)

    output_dir = OUTPUT_BASE_DIR / f'{dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")}__late_family_quality_v1'
    output_dir.mkdir(parents=True, exist_ok=False)
    _write_jsonl(output_dir / 'family_quality_rows.jsonl', family_rows)
    _write_jsonl(output_dir / 'family_quality_case_digest.jsonl', digest_rows)
    _write_json(output_dir / 'family_quality_summary.json', summary)
    _write_case_markdown(output_dir, digest_rows)
    print(
        '[late_family_quality_v1] '
        f'seeds={len(FAMILY_QUALITY_STUDY_SEEDS)} '
        f'families={len(family_rows)} '
        f'output={_relative_path(output_dir)}'
    )


if __name__ == '__main__':
    main()
