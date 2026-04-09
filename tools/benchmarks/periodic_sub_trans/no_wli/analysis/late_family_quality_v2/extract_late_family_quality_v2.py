from __future__ import annotations

import datetime as dt
import json
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path
from typing import Any, Mapping, Sequence


def _find_repo_root() -> Path:
    here = Path(__file__).resolve()
    for parent in [here] + list(here.parents):
        if (parent / 'src').exists() and (parent / 'tools').exists():
            return parent
    raise RuntimeError('Could not locate repo root from extract_late_family_quality_v2.py')


REPO_ROOT = _find_repo_root()
INPUT_LATE_FAMILY_QUALITY_V1_BUNDLE_DIR = REPO_ROOT / Path(
    'output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/'
    'late_family_quality_v1/20260408T152322Z__late_family_quality_v1'
)
OUTPUT_BASE_DIR = (
    REPO_ROOT
    / 'output'
    / 'tools'
    / 'benchmarks'
    / 'periodic_sub_trans'
    / 'no_wli'
    / 'analysis'
    / 'late_family_quality_v2'
)
REQUIRED_INPUT_FILES = (
    'family_quality_case_digest.jsonl',
    'family_quality_summary.json',
)
FAMILY_QUALITY_V2_DISCRIMINATOR_SEEDS = (1111, 1311, 1411)
FAMILY_QUALITY_V2_REFERENCE_WIN_SEEDS = (411, 611, 1011)
FAMILY_QUALITY_V2_STUDY_SEEDS = (
    1111, 1311, 1411,
    411, 611, 1011,
)
WINNER_METRICS = (
    'truth',
    'trust',
    'archive_uplift',
    'full_uplift',
    'persistence',
)
PAIRWISE_METRIC_PAIRS = tuple(combinations(WINNER_METRICS, 2))


def _safe_str(value: Any) -> str:
    return str(value or '')


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return int(default)


def _relative_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def _read_json(path: Path) -> dict[str, Any]:
    return dict(json.loads(path.read_text(encoding='utf-8')))


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
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + '\n', encoding='utf-8')


def _write_jsonl(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    with path.open('w', encoding='utf-8') as handle:
        for row in rows:
            handle.write(json.dumps(dict(row), sort_keys=True))
            handle.write('\n')


def _require_input_bundle_files(bundle_dir: Path) -> dict[str, Path]:
    resolved: dict[str, Path] = {}
    missing = [name for name in REQUIRED_INPUT_FILES if not (bundle_dir / name).exists()]
    if missing:
        raise FileNotFoundError(f'Missing required late_family_quality_v2 input files: {", ".join(sorted(missing))}')
    for name in REQUIRED_INPUT_FILES:
        resolved[name] = bundle_dir / name
    return resolved


def _read_case_digest_rows(bundle_dir: Path) -> list[dict[str, Any]]:
    return _read_jsonl(bundle_dir / 'family_quality_case_digest.jsonl')


def _study_role_for_seed(key_seed: int) -> str:
    if key_seed in FAMILY_QUALITY_V2_DISCRIMINATOR_SEEDS:
        return 'discriminator'
    if key_seed in FAMILY_QUALITY_V2_REFERENCE_WIN_SEEDS:
        return 'reference'
    raise KeyError(f'Unexpected v2 study seed: {key_seed}')


def _select_case_digest_rows(rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    selected = [dict(row) for row in rows if _safe_int(row.get('key_seed')) in FAMILY_QUALITY_V2_STUDY_SEEDS]
    present = {_safe_int(row.get('key_seed')) for row in selected}
    missing = [seed for seed in FAMILY_QUALITY_V2_STUDY_SEEDS if seed not in present]
    if missing:
        raise ValueError(f'Missing v2 study seeds from frozen late_family_quality_v1 bundle: {missing}')
    return selected


def _winner_family_id(row: Mapping[str, Any], metric_name: str) -> str:
    return _safe_str(row.get(f'{metric_name}_winner_family_id'))


def _normalize_winner_pattern(row: Mapping[str, Any]) -> tuple[str, dict[str, str]]:
    family_to_symbol: dict[str, str] = {}
    metric_to_symbol: dict[str, str] = {}
    next_symbol_code = ord('A')
    for metric_name in WINNER_METRICS:
        family_id = _winner_family_id(row, metric_name)
        if family_id not in family_to_symbol:
            family_to_symbol[family_id] = chr(next_symbol_code)
            next_symbol_code += 1
        metric_to_symbol[metric_name] = family_to_symbol[family_id]
    pattern_key = '-'.join(metric_to_symbol[metric_name] for metric_name in WINNER_METRICS)
    return pattern_key, metric_to_symbol


def _truth_agreement_count(row: Mapping[str, Any]) -> int:
    truth_family_id = _winner_family_id(row, 'truth')
    return sum(1 for metric_name in WINNER_METRICS if _winner_family_id(row, metric_name) == truth_family_id)


def _pattern_bucket_label(
    row: Mapping[str, Any],
    *,
    pattern_reference_count: int,
    pattern_discriminator_count: int,
) -> str:
    study_role = _safe_str(row.get('study_role'))
    case_shape_label = _safe_str(row.get('case_shape_label'))
    if study_role == 'reference':
        return 'reference_shared_pattern' if pattern_discriminator_count > 0 else 'reference_only_pattern'
    if case_shape_label == 'accepted_miss_outside_current_model':
        return 'accepted_miss_matches_reference_pattern' if pattern_reference_count > 0 else 'accepted_miss_unique_pattern'
    if case_shape_label.endswith('false_fire'):
        return 'false_fire_matches_reference_pattern' if pattern_reference_count > 0 else 'false_fire_reference_mismatch'
    return 'mixed_role_pattern'


def _pair_label(same_family: int) -> str:
    return 'agree' if int(same_family) else 'split'


def _pair_value_key(metric_name: str) -> str:
    if metric_name == 'truth':
        return 'truth_winner_best_truth'
    if metric_name == 'trust':
        return 'trust_winner_best_trust'
    if metric_name == 'archive_uplift':
        return 'archive_winner_best_archive_uplift'
    if metric_name == 'full_uplift':
        return 'full_uplift_winner_best_full_uplift'
    if metric_name == 'persistence':
        return 'persistence_winner_family_persistence_count'
    raise KeyError(metric_name)


def _pair_role_key(metric_name: str) -> str:
    if metric_name == 'archive_uplift':
        return 'archive_winner_family_role_label'
    return f'{metric_name}_winner_family_role_label'


def _pair_boundaries_key(metric_name: str) -> str:
    if metric_name == 'archive_uplift':
        return 'archive_winner_boundaries_seen'
    return f'{metric_name}_winner_boundaries_seen'


def _pair_trend_key(metric_name: str) -> str | None:
    if metric_name == 'truth':
        return 'truth_winner_truth_trend_label'
    if metric_name == 'trust':
        return 'trust_winner_trust_trend_label'
    if metric_name == 'archive_uplift':
        return 'archive_winner_archive_uplift_trend_label'
    if metric_name == 'full_uplift':
        return 'full_uplift_winner_full_uplift_trend_label'
    if metric_name == 'persistence':
        return None
    raise KeyError(metric_name)


def _build_seed_agreement_rows(digest_rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    pattern_counts = Counter()
    pattern_reference_seeds: dict[str, list[int]] = defaultdict(list)
    pattern_discriminator_seeds: dict[str, list[int]] = defaultdict(list)
    normalized_rows: list[dict[str, Any]] = []
    for row in digest_rows:
        pattern_key, metric_to_symbol = _normalize_winner_pattern(row)
        key_seed = _safe_int(row.get('key_seed'))
        study_role = _safe_str(row.get('study_role')) or _study_role_for_seed(key_seed)
        pattern_counts[pattern_key] += 1
        if study_role == 'reference':
            pattern_reference_seeds[pattern_key].append(key_seed)
        else:
            pattern_discriminator_seeds[pattern_key].append(key_seed)
        normalized_rows.append({
            'row': dict(row),
            'pattern_key': pattern_key,
            'metric_to_symbol': metric_to_symbol,
            'study_role': study_role,
            'key_seed': key_seed,
        })
    seed_rows: list[dict[str, Any]] = []
    for item in normalized_rows:
        row = item['row']
        pattern_key = item['pattern_key']
        metric_to_symbol = item['metric_to_symbol']
        key_seed = item['key_seed']
        unique_winner_family_count = len({_winner_family_id(row, metric_name) for metric_name in WINNER_METRICS})
        pair_agreement_count = 0
        pair_split_count = 0
        for metric_a, metric_b in PAIRWISE_METRIC_PAIRS:
            same_family = int(_winner_family_id(row, metric_a) == _winner_family_id(row, metric_b))
            pair_agreement_count += same_family
            pair_split_count += 1 - same_family
        seed_row: dict[str, Any] = {
            'key_seed': key_seed,
            'study_role': _safe_str(row.get('study_role')),
            'target_panel_name': _safe_str(row.get('target_panel_name')),
            'target_panel_role': _safe_str(row.get('target_panel_role')),
            'run_type': _safe_str(row.get('run_type')),
            'would_dump': _safe_int(row.get('would_dump')),
            'would_stop': _safe_int(row.get('would_stop')),
            'shadow_rule_id': _safe_str(row.get('shadow_rule_id')),
            'case_shape_label': _safe_str(row.get('case_shape_label')),
            'family_quality_read_label': _safe_str(row.get('family_quality_read_label')),
            'winner_pattern_key': pattern_key,
            'unique_winner_family_count': unique_winner_family_count,
            'truth_agreement_count': _truth_agreement_count(row),
            'pair_agreement_count': pair_agreement_count,
            'pair_split_count': pair_split_count,
            'pattern_seed_count': pattern_counts[pattern_key],
            'pattern_reference_count': len(pattern_reference_seeds.get(pattern_key, [])),
            'pattern_discriminator_count': len(pattern_discriminator_seeds.get(pattern_key, [])),
            'pattern_reference_seeds': '|'.join(str(seed) for seed in sorted(pattern_reference_seeds.get(pattern_key, []))),
            'pattern_discriminator_seeds': '|'.join(str(seed) for seed in sorted(pattern_discriminator_seeds.get(pattern_key, []))),
        }
        for metric_name in WINNER_METRICS:
            seed_row[f'{metric_name}_winner_family_id'] = _winner_family_id(row, metric_name)
            seed_row[f'{metric_name}_winner_symbol'] = metric_to_symbol[metric_name]
        seed_row['pattern_bucket_label'] = _pattern_bucket_label(
            row,
            pattern_reference_count=seed_row['pattern_reference_count'],
            pattern_discriminator_count=seed_row['pattern_discriminator_count'],
        )
        seed_rows.append(seed_row)
    return seed_rows


def _build_pairwise_rows(seed_agreement_rows: Sequence[Mapping[str, Any]], digest_rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    digest_by_seed = {_safe_int(row.get('key_seed')): dict(row) for row in digest_rows}
    pairwise_rows: list[dict[str, Any]] = []
    for seed_row in seed_agreement_rows:
        key_seed = _safe_int(seed_row.get('key_seed'))
        digest_row = digest_by_seed[key_seed]
        for metric_a, metric_b in PAIRWISE_METRIC_PAIRS:
            family_a = _winner_family_id(digest_row, metric_a)
            family_b = _winner_family_id(digest_row, metric_b)
            same_family = int(family_a == family_b)
            pairwise_rows.append({
                'key_seed': key_seed,
                'study_role': _safe_str(seed_row.get('study_role')),
                'target_panel_name': _safe_str(seed_row.get('target_panel_name')),
                'target_panel_role': _safe_str(seed_row.get('target_panel_role')),
                'winner_pattern_key': _safe_str(seed_row.get('winner_pattern_key')),
                'pattern_bucket_label': _safe_str(seed_row.get('pattern_bucket_label')),
                'metric_a': metric_a,
                'metric_b': metric_b,
                'metric_pair': f'{metric_a}__{metric_b}',
                'family_a_id': family_a,
                'family_b_id': family_b,
                'symbol_a': _safe_str(seed_row.get(f'{metric_a}_winner_symbol')),
                'symbol_b': _safe_str(seed_row.get(f'{metric_b}_winner_symbol')),
                'same_family': same_family,
                'pair_label': _pair_label(same_family),
                'value_a': digest_row.get(_pair_value_key(metric_a)),
                'value_b': digest_row.get(_pair_value_key(metric_b)),
                'role_a': _safe_str(digest_row.get(_pair_role_key(metric_a))),
                'role_b': _safe_str(digest_row.get(_pair_role_key(metric_b))),
                'boundaries_a': _safe_str(digest_row.get(_pair_boundaries_key(metric_a))),
                'boundaries_b': _safe_str(digest_row.get(_pair_boundaries_key(metric_b))),
                'trend_a': _safe_str(digest_row.get(_pair_trend_key(metric_a))) if _pair_trend_key(metric_a) else '',
                'trend_b': _safe_str(digest_row.get(_pair_trend_key(metric_b))) if _pair_trend_key(metric_b) else '',
            })
    return pairwise_rows


def _build_agreement_summary(
    seed_rows: Sequence[Mapping[str, Any]],
    pairwise_rows: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    pattern_counts = Counter(_safe_str(row.get('winner_pattern_key')) for row in seed_rows)
    bucket_counts = Counter(_safe_str(row.get('pattern_bucket_label')) for row in seed_rows)
    seeds_by_pattern: dict[str, list[int]] = defaultdict(list)
    pair_counts: dict[str, dict[str, int]] = defaultdict(lambda: {'agree': 0, 'split': 0})
    for row in seed_rows:
        seeds_by_pattern[_safe_str(row.get('winner_pattern_key'))].append(_safe_int(row.get('key_seed')))
    for row in pairwise_rows:
        metric_pair = _safe_str(row.get('metric_pair'))
        pair_counts[metric_pair][_pair_label(_safe_int(row.get('same_family')))] += 1
    reference_patterns = sorted({_safe_str(row.get('winner_pattern_key')) for row in seed_rows if _safe_str(row.get('study_role')) == 'reference'})
    discriminator_patterns = sorted({_safe_str(row.get('winner_pattern_key')) for row in seed_rows if _safe_str(row.get('study_role')) == 'discriminator'})
    return {
        'input_bundle_dir': _relative_path(INPUT_LATE_FAMILY_QUALITY_V1_BUNDLE_DIR),
        'study_seed_count': len(FAMILY_QUALITY_V2_STUDY_SEEDS),
        'seed_agreement_row_count': len(seed_rows),
        'pairwise_row_count': len(pairwise_rows),
        'pattern_counts': dict(sorted(pattern_counts.items())),
        'pattern_bucket_counts': dict(sorted(bucket_counts.items())),
        'seeds_by_pattern': {key: sorted(values) for key, values in sorted(seeds_by_pattern.items())},
        'reference_patterns': reference_patterns,
        'discriminator_patterns': discriminator_patterns,
        'shared_patterns': sorted(set(reference_patterns) & set(discriminator_patterns)),
        'reference_only_patterns': sorted(set(reference_patterns) - set(discriminator_patterns)),
        'discriminator_only_patterns': sorted(set(discriminator_patterns) - set(reference_patterns)),
        'pair_agreement_counts': {pair: counts for pair, counts in sorted(pair_counts.items())},
    }


def _seed_case_bullets(row: Mapping[str, Any]) -> list[str]:
    truth_symbol = _safe_str(row.get('truth_winner_symbol'))
    agreeing_metrics = [metric for metric in WINNER_METRICS if _safe_str(row.get(f'{metric}_winner_symbol')) == truth_symbol]
    split_metrics = [metric for metric in WINNER_METRICS if metric not in agreeing_metrics]
    return [
        f'pattern `{_safe_str(row.get("winner_pattern_key"))}` with bucket `{_safe_str(row.get("pattern_bucket_label"))}`',
        f'truth agrees with: `{", ".join(agreeing_metrics)}`; splits on: `{", ".join(split_metrics) or "none"}`',
        f'current read: stop label `{_safe_str(row.get("case_shape_label")) or "na"}`, family label `{_safe_str(row.get("family_quality_read_label")) or "na"}`',
    ]


def _write_case_markdown(output_dir: Path, seed_rows: Sequence[Mapping[str, Any]]) -> None:
    lines: list[str] = ['# Late Family Quality v2 Cases', '']
    for row in seed_rows:
        key_seed = _safe_int(row.get('key_seed'))
        lines.append(f'## Seed {key_seed}')
        lines.append('')
        lines.append(f'- Study role: `{_safe_str(row.get("study_role"))}`')
        lines.append(f'- Pattern: `{_safe_str(row.get("winner_pattern_key"))}`')
        lines.append(f'- Pattern bucket: `{_safe_str(row.get("pattern_bucket_label"))}`')
        lines.append('')
        lines.append('| metric | family id | symbol |')
        lines.append('| --- | --- | --- |')
        for metric_name in WINNER_METRICS:
            lines.append(
                f"| {metric_name} | {_safe_str(row.get(f'{metric_name}_winner_family_id')) or 'na'} | "
                f"{_safe_str(row.get(f'{metric_name}_winner_symbol')) or 'na'} |"
            )
        lines.append('')
        for bullet in _seed_case_bullets(row):
            lines.append(f'- {bullet}')
        lines.append('')
    (output_dir / 'agreement_cases.md').write_text('\n'.join(lines).rstrip() + '\n', encoding='utf-8')


def main() -> None:
    _require_input_bundle_files(INPUT_LATE_FAMILY_QUALITY_V1_BUNDLE_DIR)
    digest_rows = _select_case_digest_rows(_read_case_digest_rows(INPUT_LATE_FAMILY_QUALITY_V1_BUNDLE_DIR))
    _read_json(INPUT_LATE_FAMILY_QUALITY_V1_BUNDLE_DIR / 'family_quality_summary.json')
    seed_rows = _build_seed_agreement_rows(digest_rows)
    pairwise_rows = _build_pairwise_rows(seed_rows, digest_rows)
    summary = _build_agreement_summary(seed_rows, pairwise_rows)

    output_dir = OUTPUT_BASE_DIR / f'{dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")}__late_family_quality_v2'
    output_dir.mkdir(parents=True, exist_ok=False)
    _write_jsonl(output_dir / 'seed_agreement_rows.jsonl', seed_rows)
    _write_jsonl(output_dir / 'winner_pairwise_rows.jsonl', pairwise_rows)
    _write_json(output_dir / 'agreement_summary.json', summary)
    _write_case_markdown(output_dir, seed_rows)
    print(
        '[late_family_quality_v2] '
        f'seeds={len(seed_rows)} '
        f'pairs={len(pairwise_rows)} '
        f'output={_relative_path(output_dir)}'
    )


if __name__ == '__main__':
    main()
