from __future__ import annotations

import datetime as dt
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import numpy as np


def _find_repo_root() -> Path:
    here = Path(__file__).resolve()
    for parent in [here] + list(here.parents):
        if (parent / 'src').exists() and (parent / 'tools').exists():
            return parent
    raise RuntimeError('Could not locate repo root from extract_score_stop_shadow_v2.py')


REPO_ROOT = _find_repo_root()
SRC_DIR = REPO_ROOT / 'src'
import sys
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if SRC_DIR.exists() and str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from tools.benchmarks.periodic_sub_trans.common.batch_eval import score_plaintexts_chunked
from tools.benchmarks.periodic_sub_trans.no_wli import replay_phasec_rescue_sweep as replay_mod
from tools.benchmarks.periodic_sub_trans.no_wli.stage35_candidate_archive import stable_key_hash
from tools.benchmarks.periodic_sub_trans.no_wli.word_ngram_report import (
    extract_word_ngram_report_fields,
    score_word_ngram_report_for_plaintext,
)

FINAL_INSTANCE_GLOB = (
    'output/tools/benchmarks/periodic_sub_trans/no_wli/'
    '*__bench_solve_pipeline_no_wli__*/final_instances/*.json'
)
OUTPUT_BASE_DIR = (
    REPO_ROOT
    / 'output'
    / 'tools'
    / 'benchmarks'
    / 'periodic_sub_trans'
    / 'no_wli'
    / 'analysis'
    / 'score_stop_shadow_v2'
)
MAX_ARTIFACTS = 24
ONLY_REQUIRE_SPACE_MAP_V1 = False
PANEL_FILTERS = ()
ANALYSIS_MODE = 'family_panel_v1'
CORE_PANEL_TARGETS = (
    dict(
        label='solved_control_p5_seed511',
        period=5,
        columns=1,
        key_seed=511,
        min_best_match=0.999,
        require_space_map_v1=False,
    ),
    dict(
        label='selector_sensitive_win_seed411',
        period=9,
        columns=3,
        key_seed=411,
        min_best_match=0.45,
        require_best_stage='stage35_substitution_only',
        require_stage35_accept_reason='accepted',
        require_baseline_differs=1,
        require_space_map_v1=True,
    ),
    dict(
        label='selector_neutral_win_seed611',
        period=9,
        columns=3,
        key_seed=611,
        min_best_match=0.60,
        require_best_stage='stage35_substitution_only',
        require_stage35_accept_reason='accepted',
        require_baseline_differs=0,
        require_space_map_v1=True,
    ),
    dict(
        label='selector_neutral_win_seed711',
        period=9,
        columns=3,
        key_seed=711,
        min_best_match=0.70,
        require_best_stage='stage35_substitution_only',
        require_stage35_accept_reason='accepted',
        require_baseline_differs=0,
        require_space_map_v1=True,
    ),
    dict(
        label='selector_sensitive_reject_seed811',
        period=9,
        columns=3,
        key_seed=811,
        max_best_match=0.60,
        require_best_stage='stage3_full_refine',
        require_stage35_accept_reason='search_score_drop_guard_failed',
        require_baseline_differs=1,
        require_space_map_v1=True,
    ),
    dict(
        label='selector_neutral_reject_seed911',
        period=9,
        columns=3,
        key_seed=911,
        max_best_match=0.30,
        require_best_stage='stage2_search',
        require_stage35_accept_reason='search_score_drop_guard_failed',
        require_baseline_differs=0,
        require_space_map_v1=True,
    ),
    dict(
        label='selector_neutral_win_seed1011',
        period=9,
        columns=3,
        key_seed=1011,
        min_best_match=0.70,
        require_best_stage='stage35_substitution_only',
        require_stage35_accept_reason='accepted',
        require_baseline_differs=0,
        require_space_map_v1=True,
    ),
    dict(
        label='selector_neutral_win_seed1111',
        period=9,
        columns=3,
        key_seed=1111,
        min_best_match=0.50,
        require_best_stage='stage35_substitution_only',
        require_stage35_accept_reason='accepted',
        require_baseline_differs=0,
        require_space_map_v1=True,
    ),
    dict(
        label='selector_neutral_reject_seed1211',
        period=9,
        columns=3,
        key_seed=1211,
        max_best_match=0.35,
        require_best_stage='stage3_full_refine',
        require_stage35_accept_reason='search_score_drop_guard_failed',
        require_baseline_differs=0,
        require_baseline_source='phaseA_selected',
        require_space_map_v1=True,
    ),
)
PRESSURE_PANEL_TARGETS = (
    dict(
        label='selector_neutral_pressure_reject_seed1311',
        period=9,
        columns=3,
        key_seed=1311,
        max_best_match=0.60,
        require_best_stage='stage3_full_refine',
        require_stage35_accept_reason='search_score_drop_guard_failed',
        require_baseline_differs=0,
        require_space_map_v1=True,
    ),
    dict(
        label='selector_neutral_pressure_reject_seed1411',
        period=9,
        columns=3,
        key_seed=1411,
        max_best_match=0.35,
        require_best_stage='stage3_full_refine',
        require_stage35_accept_reason='search_score_drop_guard_failed',
        require_baseline_differs=0,
        require_space_map_v1=True,
    ),
    dict(
        label='selector_neutral_pressure_reject_seed1511',
        period=9,
        columns=3,
        key_seed=1511,
        max_best_match=0.65,
        require_best_stage='stage3_full_refine',
        require_stage35_accept_reason='search_score_drop_guard_failed',
        require_baseline_differs=0,
        require_space_map_v1=True,
    ),
)
FAMILY_PANEL_TARGETS = CORE_PANEL_TARGETS
SCORE_PANEL_MATCH_BANDS = (
    dict(name='solved_or_near_perfect', min_match=0.999, max_match=1.001, target_count=6),
    dict(name='near_solved_high_quality', min_match=0.85, max_match=0.999, target_count=6),
    dict(name='mid_quality', min_match=0.40, max_match=0.85, target_count=8),
    dict(name='bad_or_false_friend', min_match=-0.001, max_match=0.40, target_count=4),
)
SCORE_PANEL_STAGE_BOUNDARIES = (
    'stage2_topk',
    'stage3_topk',
    'phaseC_start',
    'stage35_seed',
    'stage35_archive',
)
SCORE_PANEL_MAX_ROWS_PER_BOUNDARY = 2
SCORE_PANEL_DISABLE_FAMILY_STOP = True
FAMILY_PANEL_STAGE_BOUNDARIES = (
    'phaseC_pool',
    'phaseC_start',
    'stage35_seed',
    'stage35_archive',
)
FAMILY_PANEL_MAX_ROWS_PER_BOUNDARY = 3
LATE_FAMILY_PERSISTENCE_BOUNDARIES = (
    'phaseC_start',
    'stage35_seed',
    'stage35_archive',
)
LATE_FAMILY_PERSISTENCE_MIN_BOUNDARIES = 2
ROW_BOUNDARY_ORDER = {
    'stage2_promoted': 1,
    'stage2_topk': 2,
    'stage3_prep': 3,
    'stage3_topk': 4,
    'phaseC_pool': 5,
    'phaseC_start': 6,
    'stage35_seed': 7,
    'stage35_archive': 8,
}
TRUST_SCORE_FLOORS = (0.30, 0.40, 0.50)
REPORT_XENT_CEILINGS = (24.0, 18.0, 12.0)
RIVAL_MARGIN_FLOORS = (0.00, 0.02, 0.05)
FAMILY_SUPPORT_FLOORS = (1, 2)
BOUNDARY_STABILITY_COUNTS = (1, 2, 3)
FAMILY_PANEL_BOUNDARY_STABILITY_COUNTS = (2, 3)
CONTINUATION_SEARCH_UPLIFT_FLOORS = (0.15,)
CONTINUATION_RULE_STAGE_BOUNDARY = 'stage35_archive'
SOLVED_MATCH_THRESHOLD = 0.999
REQUIRE_BATCH_SCORING = True
BATCH_CHUNK_SIZE = 256
CASE_EXPLANATION_TARGET_SEEDS = (1111, 1311, 1411)


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


def _safe_str(value: Any) -> str:
    return str(value or '')


def _is_finite(value: Any) -> bool:
    try:
        return math.isfinite(float(value))
    except (TypeError, ValueError):
        return False


def _finite_mean(values: Sequence[Any]) -> float:
    finite_values = [
        float(value)
        for value in list(values or [])
        if _is_finite(value)
    ]
    if not finite_values:
        return float('nan')
    return float(np.mean(np.asarray(finite_values, dtype=np.float64)))


def _iter_dump_threshold_rules() -> Iterable[dict[str, Any]]:
    for trust_floor in TRUST_SCORE_FLOORS:
        for xent_ceiling in REPORT_XENT_CEILINGS:
            for rival_margin_floor in RIVAL_MARGIN_FLOORS:
                for family_support_floor in FAMILY_SUPPORT_FLOORS:
                    yield dict(
                        rule_family='trust_dump',
                        trust_floor=float(trust_floor),
                        xent_ceiling=float(xent_ceiling),
                        rival_margin_floor=float(rival_margin_floor),
                        family_support_floor=int(family_support_floor),
                        rule_id=(
                            f'trust{float(trust_floor):.2f}_'
                            f'xent{float(xent_ceiling):.2f}_'
                            f'margin{float(rival_margin_floor):.2f}_'
                            f'support{int(family_support_floor)}'
                        ),
                    )


def _iter_continuation_rules() -> Iterable[dict[str, Any]]:
    for search_uplift_floor in CONTINUATION_SEARCH_UPLIFT_FLOORS:
        yield dict(
            rule_family='continuation_archive',
            search_uplift_floor=float(search_uplift_floor),
            rule_id=f'archive_search_uplift{float(search_uplift_floor):.2f}',
        )


def _margin_at_least(actual: Any, floor: float) -> float:
    value = _safe_float(actual)
    if not _is_finite(value):
        return float('nan')
    return float(value) - float(floor)


def _margin_at_most(actual: Any, ceiling: float) -> float:
    value = _safe_float(actual)
    if not _is_finite(value):
        return float('nan')
    return float(ceiling) - float(value)


def _margin_count_at_least(actual: Any, floor: int) -> int:
    return int(_safe_int(actual, 0) - int(floor))


def _repo_relpath(path: Path) -> str:
    path = Path(path)
    if not path.is_absolute():
        return str(path).replace('\\', '/')
    try:
        return str(path.resolve().relative_to(REPO_ROOT)).replace('\\', '/')
    except ValueError:
        return str(path).replace('\\', '/')


def _jsonify(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): _jsonify(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonify(v) for v in value]
    if isinstance(value, Path):
        return _repo_relpath(value)
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding='utf-8'))


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(_jsonify(dict(payload)), indent=2, sort_keys=True) + '\n', encoding='utf-8')


def _write_jsonl(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', encoding='utf-8', newline='\n') as handle:
        for row in rows:
            handle.write(json.dumps(_jsonify(dict(row)), sort_keys=True) + '\n')


def _utc_label() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')


def _artifact_matches_panel(artifact: Mapping[str, Any]) -> bool:
    period = _safe_int(artifact.get('period', 0), 0)
    columns = _safe_int(artifact.get('columns', 0), 0)
    if not PANEL_FILTERS:
        return True
    return any(period == int(f.get('period', -1)) and columns == int(f.get('columns', -1)) for f in PANEL_FILTERS)


def _artifact_matches_target(
    artifact: Mapping[str, Any],
    *,
    target_cfg: Mapping[str, Any],
) -> bool:
    artifact_d = dict(artifact)
    stage3_diag = dict(artifact_d.get('stage3_diagnostics', {}) or {})
    space_map = dict(stage3_diag.get('space_map_v1', {}) or {})
    if _safe_int(artifact_d.get('period', 0), 0) != _safe_int(target_cfg.get('period', -1), -1):
        return False
    if _safe_int(artifact_d.get('columns', 0), 0) != _safe_int(target_cfg.get('columns', -1), -1):
        return False
    if _safe_int(artifact_d.get('key_seed', 0), 0) != _safe_int(target_cfg.get('key_seed', -1), -1):
        return False
    if bool(target_cfg.get('require_space_map_v1', False)) and not space_map:
        return False
    best_match = _safe_float(artifact_d.get('best_match_ratio', float('nan')))
    min_best_match = _safe_float(target_cfg.get('min_best_match', float('nan')))
    max_best_match = _safe_float(target_cfg.get('max_best_match', float('nan')))
    if _is_finite(min_best_match) and (not _is_finite(best_match) or float(best_match) < float(min_best_match)):
        return False
    if _is_finite(max_best_match) and (not _is_finite(best_match) or float(best_match) > float(max_best_match)):
        return False
    required_best_stage = _safe_str(target_cfg.get('require_best_stage', ''))
    if required_best_stage and _safe_str(artifact_d.get('best_stage', '')) != required_best_stage:
        return False
    required_accept_reason = _safe_str(target_cfg.get('require_stage35_accept_reason', ''))
    if required_accept_reason and _safe_str(stage3_diag.get('stage35_accept_reason', '')) != required_accept_reason:
        return False
    if 'require_baseline_differs' in dict(target_cfg):
        if _safe_int(stage3_diag.get('stage35_baseline_differs_from_phasec_score_winner', 0), 0) != _safe_int(
            target_cfg.get('require_baseline_differs', 0), 0
        ):
            return False
    required_baseline_source = _safe_str(target_cfg.get('require_baseline_source', ''))
    if required_baseline_source and _safe_str(stage3_diag.get('stage35_baseline_candidate_source', '')) != required_baseline_source:
        return False
    return True


def _iter_review_target_cfgs() -> Iterable[dict[str, Any]]:
    for order, target_cfg in enumerate(list(CORE_PANEL_TARGETS or [])):
        yield dict(
            dict(target_cfg),
            target_panel_name='core',
            target_panel_role='benchmark',
            target_order=int(order),
        )
    for order, target_cfg in enumerate(list(PRESSURE_PANEL_TARGETS or [])):
        yield dict(
            dict(target_cfg),
            target_panel_name='pressure',
            target_panel_role='falsification',
            target_order=int(order),
        )


def _discover_review_targets(paths: Sequence[Path]) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    used_paths: set[Path] = set()
    for target_cfg in _iter_review_target_cfgs():
        chosen: Path | None = None
        chosen_artifact: dict[str, Any] | None = None
        for path in paths:
            if path in used_paths:
                continue
            try:
                artifact = _read_json(path)
            except Exception:
                continue
            if _artifact_matches_target(artifact, target_cfg=target_cfg):
                chosen = path
                chosen_artifact = artifact
                break
        if chosen is not None:
            selected.append(
                dict(
                    artifact_path=chosen,
                    artifact=chosen_artifact or {},
                    target_cfg=dict(target_cfg),
                    target_panel_name=_safe_str(target_cfg.get('target_panel_name', '')),
                    target_panel_role=_safe_str(target_cfg.get('target_panel_role', '')),
                    target_label=_safe_str(target_cfg.get('label', '')),
                    target_order=_safe_int(target_cfg.get('target_order', 0), 0),
                )
            )
            used_paths.add(chosen)
    return selected


def _discover_family_panel_paths(paths: Sequence[Path]) -> list[Path]:
    return [Path(dict(target).get('artifact_path')) for target in _discover_review_targets(paths)]


def discover_review_targets() -> list[dict[str, Any]]:
    paths = sorted(
        REPO_ROOT.glob(FINAL_INSTANCE_GLOB),
        key=lambda path: (
            str(path.parents[1].name),
            str(path.name),
        ),
        reverse=True,
    )
    if str(ANALYSIS_MODE) == 'family_panel_v1':
        return _discover_review_targets(paths)
    out: list[dict[str, Any]] = []
    for order, path in enumerate(list(discover_artifact_paths() or [])):
        out.append(
            dict(
                artifact_path=Path(path),
                artifact={},
                target_cfg={},
                target_panel_name='score_panel',
                target_panel_role='sampling',
                target_label='',
                target_order=int(order),
            )
        )
    return out


def _score_panel_band_name(artifact: Mapping[str, Any]) -> str:
    match_value = _safe_float(artifact.get('best_match_ratio', float('nan')))
    if not _is_finite(match_value):
        return ''
    for band_cfg in list(SCORE_PANEL_MATCH_BANDS or []):
        band_d = dict(band_cfg)
        if float(band_d.get('min_match', float('-inf'))) <= float(match_value) < float(
            band_d.get('max_match', float('inf'))
        ):
            return _safe_str(band_d.get('name', ''))
    return ''


def discover_artifact_paths() -> list[Path]:
    paths = sorted(
        REPO_ROOT.glob(FINAL_INSTANCE_GLOB),
        key=lambda path: (
            str(path.parents[1].name),
            str(path.name),
        ),
        reverse=True,
    )
    if str(ANALYSIS_MODE) == 'family_panel_v1':
        return _discover_family_panel_paths(paths)
    out: list[Path] = []
    band_counts = {
        _safe_str(dict(band_cfg).get('name', '')): 0
        for band_cfg in list(SCORE_PANEL_MATCH_BANDS or [])
    }
    band_targets = {
        _safe_str(dict(band_cfg).get('name', '')): _safe_int(dict(band_cfg).get('target_count', 0), 0)
        for band_cfg in list(SCORE_PANEL_MATCH_BANDS or [])
    }
    for path in paths:
        try:
            artifact = _read_json(path)
        except Exception:
            continue
        if not _artifact_matches_panel(artifact):
            continue
        stage3_diag = dict(artifact.get('stage3_diagnostics', {}) or {})
        if ONLY_REQUIRE_SPACE_MAP_V1 and not dict(stage3_diag.get('space_map_v1', {}) or {}):
            continue
        if str(ANALYSIS_MODE) == 'score_panel_v1':
            band_name = _score_panel_band_name(artifact)
            if not band_name:
                continue
            if int(band_counts.get(band_name, 0)) >= int(band_targets.get(band_name, 0)):
                continue
            band_counts[band_name] = int(band_counts.get(band_name, 0)) + 1
        out.append(path)
        if len(out) >= int(MAX_ARTIFACTS):
            break
        if str(ANALYSIS_MODE) == 'score_panel_v1' and band_targets and all(
            int(band_counts.get(name, 0)) >= int(target)
            for name, target in band_targets.items()
            if int(target) > 0
        ):
            break
    return out


def _extract_preview_text(row: Mapping[str, Any]) -> str:
    for key in ('preview_text', 'preview', 'text'):
        value = _safe_str(row.get(key, ''))
        if value:
            return value
    return ''


def _coerce_int_list(value: Any) -> list[int]:
    if value is None:
        return []
    try:
        return [int(x) for x in list(value)]
    except (TypeError, ValueError):
        return []


def _fallback_candidate_hash(row: Mapping[str, Any], stage_boundary: str, stage_rank: int) -> str:
    row_d = dict(row)
    candidate_hash = _safe_str(row_d.get('candidate_hash', ''))
    if candidate_hash:
        return candidate_hash
    end_hash = _safe_str(row_d.get('end_hash', ''))
    if end_hash:
        return end_hash
    key_idx = _coerce_int_list(row_d.get('key_idx', row_d.get('final_key_idx')))
    if key_idx:
        return str(stable_key_hash(key_idx))
    return f'{_safe_str(stage_boundary)}__rank{int(stage_rank)}'


def _append_ranked_fallback_rows(
    rows: list[dict[str, Any]],
    source_rows: Sequence[Mapping[str, Any]],
    *,
    stage_boundary: str,
    default_source: str,
    stage_rank_field: str,
    score_field: str,
    search_score_field: str,
    match_field: str,
) -> None:
    for idx, row in enumerate(list(source_rows or []), start=1):
        if not isinstance(row, Mapping):
            continue
        row_d = dict(row)
        stage_rank = _safe_int(row_d.get(stage_rank_field, idx), idx)
        rows.append(
            dict(
                stage_boundary=_safe_str(stage_boundary),
                candidate_hash=_fallback_candidate_hash(row_d, stage_boundary, stage_rank),
                source=_safe_str(row_d.get('source', default_source)) or _safe_str(default_source),
                lane=_safe_str(row_d.get('lane', '')),
                source_rank=_safe_int(row_d.get('source_rank', 0), 0),
                stage_rank=int(stage_rank),
                final_key_idx=_coerce_int_list(row_d.get('key_idx', row_d.get('final_key_idx'))),
                final_plaintext_idx=_coerce_int_list(
                    row_d.get('plaintext_idx', row_d.get('final_plaintext_idx'))
                ),
                final_score=_safe_float(row_d.get(score_field, float('nan'))),
                final_search_score=_safe_float(row_d.get(search_score_field, float('nan'))),
                final_match=_safe_float(row_d.get(match_field, float('nan'))),
                selected=1,
                eligible=1,
                replay_data_gap_flags=['fallback_row_source', 'missing_space_map_v1'],
            )
        )


def _fallback_state_by_candidate_hash(rows: Sequence[Mapping[str, Any]]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for row in list(rows or []):
        if not isinstance(row, Mapping):
            continue
        row_d = dict(row)
        candidate_hash = _safe_str(row_d.get('candidate_hash', ''))
        if not candidate_hash:
            continue
        if not _coerce_int_list(row_d.get('final_key_idx')) and not _coerce_int_list(
            row_d.get('final_plaintext_idx')
        ):
            continue
        out.setdefault(candidate_hash, row_d)
    return out


def _fallback_rows_from_artifact(artifact: Mapping[str, Any]) -> list[dict[str, Any]]:
    stage3_diag = dict(artifact.get('stage3_diagnostics', {}) or {})
    rows: list[dict[str, Any]] = []
    _append_ranked_fallback_rows(
        rows,
        list(artifact.get('stage2_topk', []) or []),
        stage_boundary='stage2_topk',
        default_source='stage2_topk',
        stage_rank_field='rank',
        score_field='score_judge',
        search_score_field='score_stage2',
        match_field='match_ratio',
    )
    _append_ranked_fallback_rows(
        rows,
        list(artifact.get('stage3_topk', []) or []),
        stage_boundary='stage3_topk',
        default_source='stage3_topk',
        stage_rank_field='rank',
        score_field='score_judge',
        search_score_field='score_raw',
        match_field='match_ratio',
    )
    state_by_hash = _fallback_state_by_candidate_hash(rows)
    for row in list(stage3_diag.get('phaseC_start_summaries', []) or []):
        row_d = dict(row)
        candidate_hash = _safe_str(row_d.get('candidate_hash', ''))
        state_row = dict(state_by_hash.get(candidate_hash, {}) or {})
        rows.append(
            dict(
                stage_boundary='phaseC_start',
                candidate_hash=candidate_hash,
                source=_safe_str(row_d.get('source', '')),
                lane=_safe_str(row_d.get('lane', '')),
                source_rank=_safe_int(row_d.get('source_rank', 0), 0),
                stage_rank=_safe_int(row_d.get('start_idx', 0), 0),
                init_key_idx=_coerce_int_list(row_d.get('init_key_idx')),
                final_key_idx=(
                    _coerce_int_list(row_d.get('final_key_idx'))
                    or _coerce_int_list(state_row.get('final_key_idx'))
                ),
                init_plaintext_idx=_coerce_int_list(row_d.get('init_plaintext_idx')),
                final_plaintext_idx=(
                    _coerce_int_list(row_d.get('final_plaintext_idx'))
                    or _coerce_int_list(state_row.get('final_plaintext_idx'))
                ),
                init_score=_safe_float(row_d.get('init_score', float('nan'))),
                final_score=_safe_float(row_d.get('final_score', float('nan'))),
                init_search_score=_safe_float(row_d.get('init_search_score', float('nan'))),
                final_search_score=_safe_float(row_d.get('final_search_score', float('nan'))),
                init_match=_safe_float(row_d.get('init_match', float('nan'))),
                final_match=_safe_float(row_d.get('final_match', float('nan'))),
                selected=1,
                eligible=_safe_int(row_d.get('eligible_novel_challenger', 0), 0),
                replay_data_gap_flags=['fallback_row_source', 'missing_space_map_v1'],
            )
        )
    for row in list(artifact.get('stage35_seed_rows', []) or []):
        row_d = dict(row)
        rows.append(
            dict(
                stage_boundary='stage35_seed',
                candidate_hash=_safe_str(row_d.get('candidate_hash', '')),
                source=_safe_str(row_d.get('stage3_source', row_d.get('seed_source', ''))),
                lane=_safe_str(row_d.get('lane', '')),
                source_rank=_safe_int(row_d.get('source_rank', 0), 0),
                stage_rank=_safe_int(row_d.get('seed_rank', 0), 0),
                final_key_idx=_coerce_int_list(row_d.get('key_idx')),
                final_plaintext_idx=_coerce_int_list(row_d.get('plaintext_idx')),
                final_score=_safe_float(row_d.get('score', float('nan'))),
                final_search_score=_safe_float(row_d.get('search_score', float('nan'))),
                selected=1,
                replay_data_gap_flags=['fallback_row_source', 'missing_space_map_v1'],
            )
        )
    stage35_archive = list(artifact.get('stage35_archive', []) or [])
    for row in stage35_archive:
        row_d = dict(row)
        rows.append(
            dict(
                stage_boundary='stage35_archive',
                candidate_hash=_safe_str(row_d.get('candidate_hash', '')),
                parent_candidate_hash=_safe_str(row_d.get('parent_hash', '')),
                source=_safe_str(row_d.get('stage3_source', row_d.get('seed_source', ''))),
                lane=_safe_str(row_d.get('lane', '')),
                source_rank=_safe_int(row_d.get('source_rank', 0), 0),
                stage_rank=_safe_int(row_d.get('archive_rank', 0), 0),
                final_key_idx=_coerce_int_list(row_d.get('key_idx')),
                final_plaintext_idx=_coerce_int_list(row_d.get('plaintext_idx')),
                final_score=_safe_float(row_d.get('score', float('nan'))),
                final_search_score=_safe_float(row_d.get('search_score', float('nan'))),
                selected=1,
                replay_data_gap_flags=['fallback_row_source', 'missing_space_map_v1'],
            )
        )
    return rows


def collect_candidate_rows(artifact: Mapping[str, Any]) -> list[dict[str, Any]]:
    stage3_diag = dict(artifact.get('stage3_diagnostics', {}) or {})
    space_map = dict(stage3_diag.get('space_map_v1', {}) or {})
    rows = [dict(row) for row in list(space_map.get('partial_state_rows', []) or []) if isinstance(row, Mapping)]
    if rows:
        out_rows = rows
    else:
        out_rows = _fallback_rows_from_artifact(artifact)
    if str(ANALYSIS_MODE) == 'score_panel_v1':
        out_rows = [
            dict(row)
            for row in out_rows
            if _safe_str(dict(row).get('stage_boundary', '')) in set(SCORE_PANEL_STAGE_BOUNDARIES)
        ]
        grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in sorted(out_rows, key=_boundary_sort_key):
            grouped[_safe_str(dict(row).get('stage_boundary', ''))].append(dict(row))
        capped_rows: list[dict[str, Any]] = []
        for boundary_name in SCORE_PANEL_STAGE_BOUNDARIES:
            capped_rows.extend(
                grouped.get(str(boundary_name), [])[
                    : int(max(1, int(SCORE_PANEL_MAX_ROWS_PER_BOUNDARY)))
                ]
            )
        out_rows = capped_rows
    elif str(ANALYSIS_MODE) == 'family_panel_v1':
        out_rows = [
            dict(row)
            for row in out_rows
            if _safe_str(dict(row).get('stage_boundary', '')) in set(FAMILY_PANEL_STAGE_BOUNDARIES)
        ]
        grouped = defaultdict(list)
        for row in sorted(out_rows, key=_boundary_sort_key):
            grouped[_safe_str(dict(row).get('stage_boundary', ''))].append(dict(row))
        capped_rows = []
        for boundary_name in FAMILY_PANEL_STAGE_BOUNDARIES:
            capped_rows.extend(
                grouped.get(str(boundary_name), [])[
                    : int(max(1, int(FAMILY_PANEL_MAX_ROWS_PER_BOUNDARY)))
                ]
            )
        out_rows = capped_rows
    return out_rows


class ReplayContext:
    def __init__(self, artifact_path: Path, artifact: Mapping[str, Any], run_config: Mapping[str, Any]) -> None:
        self.artifact_path = artifact_path
        self.artifact = dict(artifact)
        self.run_config = dict(run_config)
        self.data_gap_flags: list[str] = []
        self.cipher = None
        self.scorer_full = None
        self.scorer_search = None
        self.scorer_judge = None
        self.word_ngram_runtime = None
        self.ciphertext_idx = np.asarray(self.artifact.get('ciphertext_idx', []), dtype=np.uint8).reshape(-1)
        self.target_plaintext_idx = np.asarray(self.artifact.get('target_plaintext_idx', []), dtype=np.uint8).reshape(-1)
        self._build()

    def _build(self) -> None:
        try:
            self.cipher = replay_mod._build_cipher(self.artifact)
        except Exception:
            self.data_gap_flags.append('replay_cipher_build_failed')
            self.cipher = None
        for scorer_key, attr_name, gap_flag in (
            ('scorer', 'scorer_full', 'replay_full_scorer_build_failed'),
            ('search_scorer', 'scorer_search', 'replay_search_scorer_build_failed'),
            ('judge_scorer', 'scorer_judge', 'replay_judge_scorer_build_failed'),
        ):
            try:
                setattr(
                    self,
                    attr_name,
                    replay_mod._build_stage3_scorer_runtime(
                        artifact=self.artifact,
                        run_config=self.run_config,
                        scorer_key=scorer_key,
                    ),
                )
            except Exception:
                self.data_gap_flags.append(gap_flag)
                setattr(self, attr_name, None)
        try:
            self.word_ngram_runtime = replay_mod._build_stage3_word_ngram_report_runtime(
                artifact=self.artifact,
                run_config=self.run_config,
            )
        except Exception:
            self.data_gap_flags.append('word_ngram_runtime_build_failed')
            self.word_ngram_runtime = None


def _decrypt_plaintext_idx(ctx: ReplayContext, key_idx: Sequence[int]) -> tuple[list[int], list[str]]:
    gaps: list[str] = []
    key_list = [int(x) for x in list(key_idx or [])]
    if not key_list:
        return [], ['missing_key_for_decrypt']
    if ctx.cipher is None:
        return [], ['replay_cipher_unavailable']
    try:
        out = ctx.cipher.decrypt(
            ciphertext=np.asarray(ctx.ciphertext_idx, dtype=np.uint8).reshape(-1),
            key=np.asarray(key_list, dtype=np.uint8).reshape(-1),
        )
        pt = np.asarray(out, dtype=np.uint8).reshape(-1).tolist()
        return [int(x) for x in pt], gaps
    except Exception:
        return [], ['decrypt_failed']


def _score_plaintext(scorer: Any, plaintext_idx: Sequence[int]) -> tuple[float, list[str]]:
    if scorer is None:
        return float('nan'), ['missing_scorer_runtime']
    pt = np.asarray(list(plaintext_idx or []), dtype=np.uint8).reshape(-1)
    if int(pt.size) <= 0:
        return float('nan'), ['missing_plaintext_for_score']
    try:
        scores, _ = score_plaintexts_chunked(
            scorer=scorer,
            plaintexts=[pt],
            wli=None,
            chunk_size=int(BATCH_CHUNK_SIZE),
            require_batch=bool(REQUIRE_BATCH_SCORING),
        )
        if int(np.asarray(scores).size) <= 0:
            return float('nan'), ['empty_score_output']
        return float(np.asarray(scores, dtype=np.float64).reshape(-1)[0]), []
    except Exception:
        return float('nan'), ['score_failed']


def _truth_match(plaintext_idx: Sequence[int], target_plaintext_idx: Sequence[int]) -> float:
    lhs = np.asarray(list(plaintext_idx or []), dtype=np.uint8).reshape(-1)
    rhs = np.asarray(list(target_plaintext_idx or []), dtype=np.uint8).reshape(-1)
    if int(lhs.size) <= 0 or int(rhs.size) <= 0:
        return float('nan')
    size = min(int(lhs.size), int(rhs.size))
    if size <= 0:
        return float('nan')
    return float(np.sum(lhs[:size] == rhs[:size])) / float(size)


def _collect_row_replay_scores(row: Mapping[str, Any], ctx: ReplayContext) -> dict[str, Any]:
    row_d = dict(row)
    gaps = list(row_d.get('replay_data_gap_flags', []) or []) + list(ctx.data_gap_flags)
    final_pt = _coerce_int_list(row_d.get('final_plaintext_idx'))
    final_key = _coerce_int_list(row_d.get('final_key_idx'))
    if not final_pt and final_key:
        final_pt, decrypt_gaps = _decrypt_plaintext_idx(ctx, final_key)
        gaps.extend(decrypt_gaps)
    elif not final_pt:
        gaps.append('missing_plaintext_and_key')

    replay_full_score, full_gaps = _score_plaintext(ctx.scorer_full, final_pt)
    replay_search_score, search_gaps = _score_plaintext(ctx.scorer_search, final_pt)
    replay_judge_score, judge_gaps = _score_plaintext(ctx.scorer_judge, final_pt)
    gaps.extend(full_gaps)
    gaps.extend(search_gaps)
    gaps.extend(judge_gaps)

    if int(ctx.target_plaintext_idx.size) > 0:
        replay_truth_match = _truth_match(final_pt, ctx.target_plaintext_idx.tolist())
    else:
        replay_truth_match = float('nan')
        gaps.append('no_target_plaintext')

    report_payload: dict[str, Any] = {}
    if ctx.word_ngram_runtime is not None:
        try:
            report = score_word_ngram_report_for_plaintext(
                scorer_runtime=ctx.word_ngram_runtime,
                plaintext_idx=final_pt,
                wli=None,
                require_batch_scoring=bool(REQUIRE_BATCH_SCORING),
            )
            report_payload = extract_word_ngram_report_fields(report)
        except Exception:
            gaps.append('word_ngram_score_failed')
            report_payload = {}
    else:
        gaps.append('word_ngram_unavailable_for_run')

    return dict(
        final_plaintext_idx=list(final_pt),
        replay_full_score=float(replay_full_score),
        replay_search_score=float(replay_search_score),
        replay_judge_score=float(replay_judge_score),
        replay_truth_match=float(replay_truth_match),
        replay_word_ngram_available=bool(report_payload.get('word_ngram_judge_available', False)),
        replay_word_ngram_active=bool(report_payload.get('word_ngram_judge_active', False)),
        replay_word_ngram_report_xent=(
            float(report_payload['word_ngram_judge_report_xent'])
            if report_payload.get('word_ngram_judge_report_xent') is not None
            else float('nan')
        ),
        replay_word_ngram_trust_score=(
            float(report_payload['word_ngram_judge_trust_score'])
            if report_payload.get('word_ngram_judge_trust_score') is not None
            else float('nan')
        ),
        replay_word_ngram_inactive_reason=_safe_str(report_payload.get('word_ngram_judge_inactive_reason', '')),
        replay_score_source='decrypt_then_score' if final_key and not _coerce_int_list(row_d.get('final_plaintext_idx')) else 'saved_plaintext_then_score',
        replay_data_gap_flags=sorted(set(str(flag) for flag in gaps if str(flag))),
    )


def _boundary_sort_key(row: Mapping[str, Any]) -> tuple[int, int, str]:
    row_d = dict(row)
    return (
        int(ROW_BOUNDARY_ORDER.get(_safe_str(row_d.get('stage_boundary', '')), 999)),
        _safe_int(row_d.get('stage_rank', 0), 0),
        _safe_str(row_d.get('candidate_hash', '')),
    )


def _group_rows_by_pool(rows: Sequence[Mapping[str, Any]]) -> dict[tuple[str, str], list[dict[str, Any]]]:
    groups: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        row_d = dict(row)
        key = (_safe_str(row_d.get('artifact_path', '')), _safe_str(row_d.get('stage_boundary', '')))
        groups[key].append(row_d)
    return groups


def _row_primary_axis(row: Mapping[str, Any]) -> tuple[str, float]:
    row_d = dict(row)
    trust = _safe_float(row_d.get('replay_word_ngram_trust_score', float('nan')))
    if _is_finite(trust):
        return ('word_ngram_trust', float(trust))
    full_score = _safe_float(row_d.get('replay_full_score', float('nan')))
    if _is_finite(full_score):
        return ('replay_full_score', float(full_score))
    return ('none', float('nan'))


def _family_support_count(rows_in_pool: Sequence[Mapping[str, Any]], family_id: str, trust_floor: float, xent_ceiling: float) -> int:
    count = 0
    for row in rows_in_pool:
        row_d = dict(row)
        if _safe_str(row_d.get('family_id', '')) != str(family_id):
            continue
        trust = _safe_float(row_d.get('replay_word_ngram_trust_score', float('nan')))
        xent = _safe_float(row_d.get('replay_word_ngram_report_xent', float('nan')))
        active = bool(row_d.get('replay_word_ngram_active', False))
        if active and _is_finite(trust) and trust >= float(trust_floor) and (_is_finite(xent) and xent <= float(xent_ceiling)):
            count += 1
    return int(count)


def _best_family_axis(rows_in_pool: Sequence[Mapping[str, Any]], family_id: str, axis_name: str) -> float:
    vals: list[float] = []
    for row in rows_in_pool:
        row_d = dict(row)
        if _safe_str(row_d.get('family_id', '')) != str(family_id):
            continue
        val = _safe_float(row_d.get(axis_name, float('nan')))
        if _is_finite(val):
            vals.append(float(val))
    return max(vals) if vals else float('nan')


def _best_rival_margin(row: Mapping[str, Any], rows_in_pool: Sequence[Mapping[str, Any]]) -> tuple[str, float]:
    row_d = dict(row)
    family_id = _safe_str(row_d.get('family_id', ''))
    axis_name, own_axis = _row_primary_axis(row_d)
    if not axis_name or axis_name == 'none' or not _is_finite(own_axis):
        return (axis_name, float('nan'))
    rival_best = float('nan')
    for rival_family in sorted({_safe_str(r.get('family_id', '')) for r in rows_in_pool if _safe_str(r.get('family_id', '')) and _safe_str(r.get('family_id', '')) != family_id}):
        rival_axis = _best_family_axis(rows_in_pool, rival_family, f'replay_word_ngram_trust_score' if axis_name == 'word_ngram_trust' else 'replay_full_score')
        if _is_finite(rival_axis):
            rival_best = rival_axis if not _is_finite(rival_best) else max(rival_best, rival_axis)
    if not _is_finite(rival_best):
        return (axis_name, float('nan'))
    return (axis_name, float(own_axis) - float(rival_best))


def _anchor_margin(row: Mapping[str, Any], rows_in_pool: Sequence[Mapping[str, Any]]) -> float:
    row_d = dict(row)
    axis_name, own_axis = _row_primary_axis(row_d)
    if not axis_name or axis_name == 'none' or not _is_finite(own_axis):
        return float('nan')
    anchor_hash = ''
    for candidate in rows_in_pool:
        cand = dict(candidate)
        dist = _safe_float(cand.get('distance_to_anchor', float('nan')))
        if _is_finite(dist) and float(dist) == 0.0:
            anchor_hash = _safe_str(cand.get('candidate_hash', ''))
            break
    if not anchor_hash:
        return float('nan')
    for candidate in rows_in_pool:
        cand = dict(candidate)
        if _safe_str(cand.get('candidate_hash', '')) != anchor_hash:
            continue
        anchor_axis = _safe_float(cand.get('replay_word_ngram_trust_score' if axis_name == 'word_ngram_trust' else 'replay_full_score', float('nan')))
        if _is_finite(anchor_axis):
            return float(own_axis) - float(anchor_axis)
    return float('nan')


def _late_family_persistence_metrics(
    row: Mapping[str, Any],
    artifact_rows: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    row_d = dict(row)
    family_id = _safe_str(row_d.get('family_id', ''))
    if not family_id:
        return dict(
            shadow_late_family_persistence_count=0,
            shadow_late_family_persistence_boundaries=[],
            shadow_late_family_persistence_pass=0,
            shadow_late_family_reaches_archive=0,
            shadow_late_family_first_boundary='',
            shadow_late_family_last_boundary='',
        )
    boundary_hits: list[tuple[int, str]] = []
    seen: set[str] = set()
    for candidate in sorted([dict(r) for r in artifact_rows], key=_boundary_sort_key):
        if _safe_str(candidate.get('family_id', '')) != family_id:
            continue
        boundary_name = _safe_str(candidate.get('stage_boundary', ''))
        if boundary_name not in set(LATE_FAMILY_PERSISTENCE_BOUNDARIES):
            continue
        if boundary_name in seen:
            continue
        seen.add(boundary_name)
        boundary_hits.append((_boundary_sort_key(candidate)[0], boundary_name))
    boundary_names = [name for _, name in sorted(boundary_hits, key=lambda x: x[0])]
    persistence_count = int(len(boundary_names))
    return dict(
        shadow_late_family_persistence_count=persistence_count,
        shadow_late_family_persistence_boundaries=list(boundary_names),
        shadow_late_family_persistence_pass=int(
            persistence_count >= int(LATE_FAMILY_PERSISTENCE_MIN_BOUNDARIES)
        ),
        shadow_late_family_reaches_archive=int('stage35_archive' in set(boundary_names)),
        shadow_late_family_first_boundary=_safe_str(boundary_names[0] if boundary_names else ''),
        shadow_late_family_last_boundary=_safe_str(boundary_names[-1] if boundary_names else ''),
    )


def _best_family_boundary_axis(
    artifact_rows: Sequence[Mapping[str, Any]],
    family_id: str,
    boundary_name: str,
    axis_name: str,
) -> float:
    vals: list[float] = []
    for row in artifact_rows:
        row_d = dict(row)
        if _safe_str(row_d.get('family_id', '')) != str(family_id):
            continue
        if _safe_str(row_d.get('stage_boundary', '')) != str(boundary_name):
            continue
        val = _safe_float(row_d.get(axis_name, float('nan')))
        if _is_finite(val):
            vals.append(float(val))
    return max(vals) if vals else float('nan')


def _late_family_continuation_metrics(
    row: Mapping[str, Any],
    artifact_rows: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    row_d = dict(row)
    family_id = _safe_str(row_d.get('family_id', ''))
    current_boundary = _safe_str(row_d.get('stage_boundary', ''))
    if not family_id:
        return dict(
            shadow_late_family_phasec_search_score=float('nan'),
            shadow_late_family_current_boundary_best_search_score=float('nan'),
            shadow_late_family_search_uplift=float('nan'),
            shadow_late_family_phasec_full_score=float('nan'),
            shadow_late_family_current_boundary_best_full_score=float('nan'),
            shadow_late_family_full_uplift=float('nan'),
        )
    phasec_search = _best_family_boundary_axis(
        artifact_rows,
        family_id,
        'phaseC_start',
        'replay_search_score',
    )
    current_search = _best_family_boundary_axis(
        artifact_rows,
        family_id,
        current_boundary,
        'replay_search_score',
    )
    phasec_full = _best_family_boundary_axis(
        artifact_rows,
        family_id,
        'phaseC_start',
        'replay_full_score',
    )
    current_full = _best_family_boundary_axis(
        artifact_rows,
        family_id,
        current_boundary,
        'replay_full_score',
    )
    search_uplift = float('nan')
    if _is_finite(phasec_search) and _is_finite(current_search):
        search_uplift = float(current_search) - float(phasec_search)
    full_uplift = float('nan')
    if _is_finite(phasec_full) and _is_finite(current_full):
        full_uplift = float(current_full) - float(phasec_full)
    return dict(
        shadow_late_family_phasec_search_score=float(phasec_search),
        shadow_late_family_current_boundary_best_search_score=float(current_search),
        shadow_late_family_search_uplift=float(search_uplift),
        shadow_late_family_phasec_full_score=float(phasec_full),
        shadow_late_family_current_boundary_best_full_score=float(current_full),
        shadow_late_family_full_uplift=float(full_uplift),
    )


def _diagnostic_dump_metrics(
    row: Mapping[str, Any],
    rows_in_pool: Sequence[Mapping[str, Any]],
    *,
    trust_floor: float,
    xent_ceiling: float,
    rival_margin_floor: float,
    family_support_floor: int,
) -> dict[str, Any]:
    row_d = dict(row)
    trust = _safe_float(row_d.get('replay_word_ngram_trust_score', float('nan')))
    xent = _safe_float(row_d.get('replay_word_ngram_report_xent', float('nan')))
    active = bool(row_d.get('replay_word_ngram_active', False))
    family_id = _safe_str(row_d.get('family_id', ''))
    axis_name, rival_margin = _best_rival_margin(row_d, rows_in_pool)
    anchor_margin = _anchor_margin(row_d, rows_in_pool)
    support_count = _family_support_count(
        rows_in_pool,
        family_id,
        float(trust_floor),
        float(xent_ceiling),
    )
    blockers: list[str] = []
    if not active:
        blockers.append('word_ngram_inactive')
    if not _is_finite(trust):
        blockers.append('missing_trust')
    elif float(trust) < float(trust_floor):
        blockers.append('trust_below_floor')
    if not _is_finite(xent):
        blockers.append('missing_xent')
    elif float(xent) > float(xent_ceiling):
        blockers.append('xent_above_ceiling')
    if support_count < int(family_support_floor):
        blockers.append('family_support_below_floor')
    if _is_finite(rival_margin) and float(rival_margin) < float(rival_margin_floor):
        blockers.append('rival_margin_below_floor')
    return dict(
        shadow_primary_axis=axis_name,
        shadow_anchor_margin=float(anchor_margin),
        shadow_best_rival_family_margin=float(rival_margin),
        shadow_family_support_count=int(support_count),
        shadow_diag_trust_floor=float(trust_floor),
        shadow_diag_xent_ceiling=float(xent_ceiling),
        shadow_diag_rival_margin_floor=float(rival_margin_floor),
        shadow_diag_family_support_floor=int(family_support_floor),
        shadow_diag_word_ngram_active=int(active),
        shadow_diag_trust_pass=int(_is_finite(trust) and float(trust) >= float(trust_floor)),
        shadow_diag_xent_pass=int(_is_finite(xent) and float(xent) <= float(xent_ceiling)),
        shadow_diag_rival_margin_pass=int((not _is_finite(rival_margin)) or float(rival_margin) >= float(rival_margin_floor)),
        shadow_diag_family_support_pass=int(support_count >= int(family_support_floor)),
        shadow_diag_blockers=sorted(set(str(blocker) for blocker in blockers)),
    )


def _negative_deficit(values: Sequence[Any]) -> float:
    deficits = [abs(float(value)) for value in list(values or []) if _is_finite(value) and float(value) < 0.0]
    if not deficits:
        return 0.0
    return float(sum(deficits))


def _worst_negative_margin(values: Sequence[Any]) -> float:
    deficits = [abs(float(value)) for value in list(values or []) if _is_finite(value) and float(value) < 0.0]
    if not deficits:
        return 0.0
    return float(max(deficits))


def _primary_blocker_from_metrics(
    blocker_pairs: Sequence[tuple[str, Any]],
    blockers: Sequence[str],
) -> str:
    blockers_set = {str(blocker) for blocker in list(blockers or [])}
    best_name = ''
    best_value = float('-inf')
    for name, value in list(blocker_pairs or []):
        if str(name) not in blockers_set:
            continue
        if not _is_finite(value):
            return str(name)
        if float(value) > best_value:
            best_value = float(value)
            best_name = str(name)
    if best_name:
        return best_name
    return _safe_str(list(blockers or [''])[0] if list(blockers or []) else '')


def _evaluate_dump_rule(
    row: Mapping[str, Any],
    rows_in_pool: Sequence[Mapping[str, Any]],
    *,
    trust_floor: float,
    xent_ceiling: float,
    rival_margin_floor: float,
    family_support_floor: int,
) -> dict[str, Any]:
    row_d = dict(row)
    trust = _safe_float(row_d.get('replay_word_ngram_trust_score', float('nan')))
    xent = _safe_float(row_d.get('replay_word_ngram_report_xent', float('nan')))
    active = bool(row_d.get('replay_word_ngram_active', False))
    metrics = _diagnostic_dump_metrics(
        row,
        rows_in_pool,
        trust_floor=float(trust_floor),
        xent_ceiling=float(xent_ceiling),
        rival_margin_floor=float(rival_margin_floor),
        family_support_floor=int(family_support_floor),
    )
    rival_margin = _safe_float(metrics.get('shadow_best_rival_family_margin', float('nan')))
    support_count = _safe_int(metrics.get('shadow_family_support_count', 0), 0)
    if str(ANALYSIS_MODE) == 'score_panel_v1':
        ok = bool(
            active
            and _is_finite(trust)
            and float(trust) >= float(trust_floor)
            and _is_finite(xent)
            and float(xent) <= float(xent_ceiling)
        )
    else:
        ok = bool(
            active
            and _is_finite(trust)
            and float(trust) >= float(trust_floor)
            and _is_finite(xent)
            and float(xent) <= float(xent_ceiling)
            and support_count >= int(family_support_floor)
            and (not _is_finite(rival_margin) or float(rival_margin) >= float(rival_margin_floor))
        )
    trust_margin = _margin_at_least(trust, float(trust_floor))
    xent_margin = _margin_at_most(xent, float(xent_ceiling))
    rival_margin_margin = (
        float('nan')
        if not _is_finite(rival_margin)
        else _margin_at_least(rival_margin, float(rival_margin_floor))
    )
    family_support_margin = float(_margin_count_at_least(support_count, int(family_support_floor)))
    blockers = list(metrics.get('shadow_diag_blockers', []) or [])
    primary_blocker = _primary_blocker_from_metrics(
        [
            ('trust_below_floor', -trust_margin),
            ('xent_above_ceiling', -xent_margin),
            ('family_support_below_floor', -family_support_margin),
            ('rival_margin_below_floor', -rival_margin_margin),
            ('word_ngram_inactive', float('inf')),
            ('missing_trust', float('inf')),
            ('missing_xent', float('inf')),
        ],
        blockers,
    )
    return dict(
        metrics,
        rule_family='trust_dump',
        rule_id=(
            f'trust{float(trust_floor):.2f}_'
            f'xent{float(xent_ceiling):.2f}_'
            f'margin{float(rival_margin_floor):.2f}_'
            f'support{int(family_support_floor)}'
        ),
        **{'pass': int(ok)},
        trust_floor=float(trust_floor),
        xent_ceiling=float(xent_ceiling),
        rival_margin_floor=float(rival_margin_floor),
        family_support_floor=int(family_support_floor),
        shadow_margin_trust=float(trust_margin),
        shadow_margin_xent=float(xent_margin),
        shadow_margin_rival_margin=float(rival_margin_margin),
        shadow_margin_family_support=float(family_support_margin),
        shadow_margin_archive_search_uplift=float('nan'),
        failed_gate_count=int(len(blockers)),
        worst_negative_margin=float(
            _worst_negative_margin(
                [trust_margin, xent_margin, rival_margin_margin, family_support_margin]
            )
        ),
        total_negative_deficit=float(
            _negative_deficit(
                [trust_margin, xent_margin, rival_margin_margin, family_support_margin]
            )
        ),
        primary_blocker=str(primary_blocker),
    )


def _qualifies_continuation_dump(
    row: Mapping[str, Any],
    artifact_rows: Sequence[Mapping[str, Any]],
    *,
    search_uplift_floor: float,
) -> tuple[bool, dict[str, Any]]:
    eval_out = _evaluate_continuation_rule(
        row,
        artifact_rows,
        search_uplift_floor=search_uplift_floor,
    )
    return bool(int(eval_out.get('pass', 0) or 0) == 1), dict(eval_out)


def _evaluate_continuation_rule(
    row: Mapping[str, Any],
    artifact_rows: Sequence[Mapping[str, Any]],
    *,
    search_uplift_floor: float,
) -> dict[str, Any]:
    metrics = _late_family_continuation_metrics(row, artifact_rows)
    boundary_name = _safe_str(dict(row).get('stage_boundary', ''))
    search_uplift = _safe_float(metrics.get('shadow_late_family_search_uplift', float('nan')))
    blockers: list[str] = []
    if boundary_name != str(CONTINUATION_RULE_STAGE_BOUNDARY):
        blockers.append('not_archive_boundary')
    elif not _is_finite(search_uplift):
        blockers.append('missing_search_uplift')
    elif float(search_uplift) < float(search_uplift_floor):
        blockers.append('archive_search_uplift_below_floor')
    ok = bool(
        boundary_name == str(CONTINUATION_RULE_STAGE_BOUNDARY)
        and _is_finite(search_uplift)
        and float(search_uplift) >= float(search_uplift_floor)
    )
    uplift_margin = (
        float('nan')
        if not _is_finite(search_uplift)
        else _margin_at_least(search_uplift, float(search_uplift_floor))
    )
    primary_blocker = _primary_blocker_from_metrics(
        [
            ('archive_search_uplift_below_floor', -uplift_margin),
            ('not_archive_boundary', float('inf')),
            ('missing_search_uplift', float('inf')),
        ],
        blockers,
    )
    return dict(
        metrics,
        rule_family='continuation_archive',
        rule_id=f'archive_search_uplift{float(search_uplift_floor):.2f}',
        **{'pass': int(ok)},
        search_uplift_floor=float(search_uplift_floor),
        shadow_margin_trust=float('nan'),
        shadow_margin_xent=float('nan'),
        shadow_margin_rival_margin=float('nan'),
        shadow_margin_family_support=float('nan'),
        shadow_margin_archive_search_uplift=float(uplift_margin),
        shadow_diag_blockers=sorted(set(str(blocker) for blocker in blockers)),
        failed_gate_count=int(len(blockers)),
        worst_negative_margin=float(_worst_negative_margin([uplift_margin])),
        total_negative_deficit=float(_negative_deficit([uplift_margin])),
        primary_blocker=str(primary_blocker),
    )


def _build_threshold_matrix_rows_for_row(
    row: Mapping[str, Any],
    rows_in_pool: Sequence[Mapping[str, Any]],
    artifact_rows: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    row_d = dict(row)
    threshold_rows: list[dict[str, Any]] = []
    for rule_cfg in _iter_dump_threshold_rules():
        threshold_rows.append(
            dict(
                artifact_path=_safe_str(row_d.get('artifact_path', '')),
                run_id=_safe_str(row_d.get('run_id', '')),
                target_panel_name=_safe_str(row_d.get('target_panel_name', '')),
                target_panel_role=_safe_str(row_d.get('target_panel_role', '')),
                target_label=_safe_str(row_d.get('target_label', '')),
                target_order=_safe_int(row_d.get('target_order', 0), 0),
                key_seed=_safe_int(row_d.get('key_seed', 0), 0),
                stage_boundary=_safe_str(row_d.get('stage_boundary', '')),
                stage_rank=_safe_int(row_d.get('stage_rank', 0), 0),
                candidate_hash=_safe_str(row_d.get('candidate_hash', '')),
                family_id=_safe_str(row_d.get('family_id', '')),
                is_first_firing_rule=0,
                **_evaluate_dump_rule(
                    row_d,
                    rows_in_pool,
                    trust_floor=float(rule_cfg.get('trust_floor', float('nan'))),
                    xent_ceiling=float(rule_cfg.get('xent_ceiling', float('nan'))),
                    rival_margin_floor=float(rule_cfg.get('rival_margin_floor', float('nan'))),
                    family_support_floor=int(rule_cfg.get('family_support_floor', 0)),
                ),
            )
        )
    if str(ANALYSIS_MODE) == 'family_panel_v1':
        for rule_cfg in _iter_continuation_rules():
            threshold_rows.append(
                dict(
                    artifact_path=_safe_str(row_d.get('artifact_path', '')),
                    run_id=_safe_str(row_d.get('run_id', '')),
                    target_panel_name=_safe_str(row_d.get('target_panel_name', '')),
                    target_panel_role=_safe_str(row_d.get('target_panel_role', '')),
                    target_label=_safe_str(row_d.get('target_label', '')),
                    target_order=_safe_int(row_d.get('target_order', 0), 0),
                    key_seed=_safe_int(row_d.get('key_seed', 0), 0),
                    stage_boundary=_safe_str(row_d.get('stage_boundary', '')),
                    stage_rank=_safe_int(row_d.get('stage_rank', 0), 0),
                    candidate_hash=_safe_str(row_d.get('candidate_hash', '')),
                    family_id=_safe_str(row_d.get('family_id', '')),
                    is_first_firing_rule=0,
                    **_evaluate_continuation_rule(
                        row_d,
                        artifact_rows,
                        search_uplift_floor=float(rule_cfg.get('search_uplift_floor', float('nan'))),
                    ),
                )
            )
    return threshold_rows


def _pick_nearest_pass_rule(
    threshold_rows: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    failed_rows = [
        dict(row)
        for row in list(threshold_rows or [])
        if int(dict(row).get('pass', 0) or 0) == 0
    ]
    if not failed_rows:
        return {}
    failed_rows.sort(
        key=lambda row: (
            _safe_int(row.get('failed_gate_count', 999999), 999999),
            _safe_float(row.get('worst_negative_margin', float('inf'))),
            _safe_float(row.get('total_negative_deficit', float('inf'))),
            _safe_str(row.get('rule_id', '')),
        )
    )
    return failed_rows[0]


def _annotate_shadow_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped = _group_rows_by_pool(rows)
    out_rows = [dict(row) for row in rows]
    by_artifact: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in out_rows:
        by_artifact[_safe_str(row.get('artifact_path', ''))].append(dict(row))
    diagnostic_trust_floor = float(min(TRUST_SCORE_FLOORS))
    diagnostic_xent_ceiling = float(max(REPORT_XENT_CEILINGS))
    diagnostic_rival_margin_floor = float(min(RIVAL_MARGIN_FLOORS))
    diagnostic_family_support_floor = int(min(FAMILY_SUPPORT_FLOORS))
    for idx, row in enumerate(out_rows):
        rows_in_pool = grouped.get((_safe_str(row.get('artifact_path', '')), _safe_str(row.get('stage_boundary', ''))), [])
        artifact_rows = by_artifact.get(_safe_str(row.get('artifact_path', '')), [])
        best_dump = None
        metrics_out: dict[str, Any] = _diagnostic_dump_metrics(
            row,
            rows_in_pool,
            trust_floor=diagnostic_trust_floor,
            xent_ceiling=diagnostic_xent_ceiling,
            rival_margin_floor=diagnostic_rival_margin_floor,
            family_support_floor=diagnostic_family_support_floor,
        )
        metrics_out.update(_late_family_persistence_metrics(row, artifact_rows))
        metrics_out.update(_late_family_continuation_metrics(row, artifact_rows))
        threshold_rows = _build_threshold_matrix_rows_for_row(row, rows_in_pool, artifact_rows)
        selected_rule_row: dict[str, Any] = {}
        for threshold_row in threshold_rows:
            threshold_row_d = dict(threshold_row)
            if _safe_str(threshold_row_d.get('rule_family', '')) == 'continuation_archive':
                continue
            if int(threshold_row_d.get('pass', 0) or 0) == 1:
                best_dump = _safe_str(threshold_row_d.get('rule_id', ''))
                selected_rule_row = dict(threshold_row_d)
                break
        if best_dump is None and str(ANALYSIS_MODE) == 'family_panel_v1':
            for threshold_row in threshold_rows:
                threshold_row_d = dict(threshold_row)
                if _safe_str(threshold_row_d.get('rule_family', '')) != 'continuation_archive':
                    continue
                if int(threshold_row_d.get('pass', 0) or 0) == 1:
                    best_dump = _safe_str(threshold_row_d.get('rule_id', ''))
                    selected_rule_row = dict(threshold_row_d)
                    break
        for threshold_row in threshold_rows:
            threshold_row['is_first_firing_rule'] = int(
                bool(best_dump) and _safe_str(dict(threshold_row).get('rule_id', '')) == str(best_dump)
            )
        nearest_rule = _pick_nearest_pass_rule(threshold_rows)
        margin_row = dict(selected_rule_row) if selected_rule_row else dict(nearest_rule)
        nearest_pass_deficit = _safe_float(nearest_rule.get('worst_negative_margin', float('nan')))
        nearest_pass_signed_margin = (
            float('nan')
            if not _is_finite(nearest_pass_deficit)
            else -abs(float(nearest_pass_deficit))
        )
        metrics_out = dict(
            metrics_out,
            shadow_margin_rule_id=_safe_str(margin_row.get('rule_id', '')),
            shadow_margin_rule_kind=('selected' if selected_rule_row else 'nearest'),
            shadow_margin_trust=_safe_float(margin_row.get('shadow_margin_trust', float('nan'))),
            shadow_margin_xent=_safe_float(margin_row.get('shadow_margin_xent', float('nan'))),
            shadow_margin_rival_margin=_safe_float(margin_row.get('shadow_margin_rival_margin', float('nan'))),
            shadow_margin_family_support=_safe_float(margin_row.get('shadow_margin_family_support', float('nan'))),
            shadow_margin_archive_search_uplift=_safe_float(
                margin_row.get('shadow_margin_archive_search_uplift', float('nan'))
            ),
            shadow_nearest_pass_rule_id=(
                '' if selected_rule_row else _safe_str(nearest_rule.get('rule_id', ''))
            ),
            shadow_nearest_pass_blocker=(
                '' if selected_rule_row else _safe_str(nearest_rule.get('primary_blocker', ''))
            ),
            shadow_nearest_pass_margin=(
                float('nan')
                if selected_rule_row
                else float(nearest_pass_signed_margin)
            ),
            shadow_nearest_pass_deficit=(
                float('nan')
                if selected_rule_row
                else float(nearest_pass_deficit)
            ),
            shadow_gate_fail_count=(
                0 if selected_rule_row else _safe_int(nearest_rule.get('failed_gate_count', 0), 0)
            ),
            _shadow_threshold_matrix_rows=[dict(threshold_row) for threshold_row in threshold_rows],
        )
        out_rows[idx] = dict(
            row,
            **metrics_out,
            shadow_high_score_rule_id=str(best_dump or ''),
            shadow_high_score_would_dump=int(best_dump is not None),
            shadow_high_score_would_stop=0,
            shadow_stability_rule_id='',
            shadow_stability_would_stop=0,
        )
    return out_rows


def _annotate_stability(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows_sorted = sorted([dict(r) for r in rows], key=_boundary_sort_key)
    by_artifact: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows_sorted:
        by_artifact[_safe_str(row.get('artifact_path', ''))].append(row)
    out_rows: list[dict[str, Any]] = []
    thresholds = (
        FAMILY_PANEL_BOUNDARY_STABILITY_COUNTS
        if str(ANALYSIS_MODE) == 'family_panel_v1'
        else BOUNDARY_STABILITY_COUNTS
    )
    for artifact_path, artifact_rows in by_artifact.items():
        family_boundary_hits: dict[str, list[tuple[int, int, dict[str, Any]]]] = defaultdict(list)
        for row in artifact_rows:
            if int(row.get('shadow_high_score_would_dump', 0) or 0) != 1:
                continue
            fam = _safe_str(row.get('family_id', ''))
            if not fam:
                continue
            family_boundary_hits[fam].append((_boundary_sort_key(row)[0], _safe_int(row.get('stage_rank', 0), 0), row))
        stable_rows: dict[str, tuple[int, str]] = {}
        for fam, hits in family_boundary_hits.items():
            uniq_boundaries = []
            seen = set()
            for boundary_order, stage_rank, row in sorted(hits, key=lambda x: (x[0], x[1])):
                if boundary_order in seen:
                    continue
                seen.add(boundary_order)
                uniq_boundaries.append((boundary_order, stage_rank, row))
            best_threshold = 0
            best_row: dict[str, Any] | None = None
            for threshold in sorted(thresholds, reverse=True):
                if len(uniq_boundaries) >= int(threshold):
                    best_threshold = int(threshold)
                    best_row = dict(uniq_boundaries[int(threshold) - 1][2])
                    break
            if best_threshold > 0 and best_row is not None:
                stable_rows[_safe_str(best_row.get('candidate_hash', ''))] = (
                    int(best_threshold),
                    _safe_str(best_row.get('stage_boundary', '')),
                )
        for row in artifact_rows:
            row_d = dict(row)
            key = _safe_str(row_d.get('candidate_hash', ''))
            stable_info = stable_rows.get(key, None)
            if stable_info is not None:
                threshold, stage_boundary = stable_info
                row_d['shadow_stability_rule_id'] = f'family_boundary_support_{int(threshold)}'
                row_d['shadow_stability_would_stop'] = 1
                row_d['shadow_high_score_would_stop'] = 1
                row_d['shadow_first_trigger_stage_boundary'] = str(stage_boundary)
                row_d['shadow_first_trigger_stage_rank'] = _safe_int(row_d.get('stage_rank', 0), 0)
                row_d['shadow_family_boundary_support_count'] = int(threshold)
            else:
                row_d.setdefault('shadow_first_trigger_stage_boundary', '')
                row_d.setdefault('shadow_first_trigger_stage_rank', 0)
                row_d.setdefault('shadow_family_boundary_support_count', 0)
            out_rows.append(row_d)
    return out_rows


def _strip_private_analysis_fields(row: Mapping[str, Any]) -> dict[str, Any]:
    return {
        str(k): v
        for k, v in dict(row).items()
        if not str(k).startswith('_shadow_')
    }


def _label_false_stop(run_row: Mapping[str, Any], artifact: Mapping[str, Any]) -> str:
    run_d = dict(run_row)
    artifact_d = dict(artifact)
    if int(run_d.get('would_stop', 0) or 0) != 1:
        return ''
    candidate_truth = _safe_float(run_d.get('would_stop_truth_match', float('nan')))
    best_match_ratio = _safe_float(artifact_d.get('best_match_ratio', float('nan')))
    if not _is_finite(candidate_truth):
        return 'unknown_without_truth'
    if _is_finite(best_match_ratio) and float(best_match_ratio) > float(candidate_truth) + 1e-9:
        return 'false_stop_before_better_truth'
    if _is_finite(best_match_ratio) and best_match_ratio >= SOLVED_MATCH_THRESHOLD and candidate_truth < SOLVED_MATCH_THRESHOLD:
        return 'false_stop_before_true_solution'
    return 'not_false_stop_on_fixture'


def _estimate_saved_runtime_proxy(artifact: Mapping[str, Any], stop_boundary: str) -> float:
    stage3_diag = dict(artifact.get('stage3_diagnostics', {}) or {})
    stage35_runtime = _safe_float(stage3_diag.get('stage35_runtime_seconds', float('nan')))
    if not _is_finite(stage35_runtime):
        return float('nan')
    if stop_boundary in {'stage2_promoted', 'stage3_prep', 'phaseC_pool', 'phaseC_start'}:
        return float(stage35_runtime)
    if stop_boundary == 'stage35_seed':
        return float(stage35_runtime) * 0.5
    if stop_boundary == 'stage35_archive':
        return float(stage35_runtime) * 0.25
    return float('nan')


def _estimate_saved_evals_proxy(artifact: Mapping[str, Any], stop_boundary: str) -> float:
    stage3_diag = dict(artifact.get('stage3_diagnostics', {}) or {})
    stage35_evals = _safe_float(stage3_diag.get('stage35_evals', float('nan')))
    if not _is_finite(stage35_evals):
        return float('nan')
    if stop_boundary in {'stage2_promoted', 'stage3_prep', 'phaseC_pool', 'phaseC_start'}:
        return float(stage35_evals)
    if stop_boundary == 'stage35_seed':
        return float(stage35_evals) * 0.5
    if stop_boundary == 'stage35_archive':
        return float(stage35_evals) * 0.25
    return float('nan')


def build_run_shadow_summary(
    artifact_path: Path,
    artifact: Mapping[str, Any],
    rows: Sequence[Mapping[str, Any]],
    *,
    target_panel_name: str = '',
    target_panel_role: str = '',
    target_label: str = '',
    target_order: int = 0,
) -> list[dict[str, Any]]:
    rows_sorted = sorted([dict(r) for r in rows], key=_boundary_sort_key)
    by_rule: dict[tuple[str, int], list[dict[str, Any]]] = defaultdict(list)
    for row in rows_sorted:
        dump_rule_id = _safe_str(row.get('shadow_high_score_rule_id', ''))
        stop_rule_id = _safe_str(row.get('shadow_stability_rule_id', ''))
        if dump_rule_id:
            by_rule[(dump_rule_id, 0)].append(dict(row))
        if stop_rule_id and _safe_int(row.get('shadow_stability_would_stop', 0), 0) == 1:
            by_rule[(stop_rule_id, 1)].append(dict(row))
    summaries: list[dict[str, Any]] = []
    stage3_diag = dict(artifact.get('stage3_diagnostics', {}) or {})
    run_type = 'unknown'
    best_match = _safe_float(artifact.get('best_match_ratio', float('nan')))
    best_stage = _safe_str(artifact.get('best_stage', ''))
    if _is_finite(best_match) and best_match >= SOLVED_MATCH_THRESHOLD:
        run_type = 'solved_control'
    elif _safe_int(stage3_diag.get('stage35_accept_passed', 0), 0) == 1 and best_stage == 'stage35_substitution_only':
        run_type = 'stage35_live_win'
    for (rule_id, would_stop_flag), triggered_rows in sorted(by_rule.items()):
        first_row = triggered_rows[0]
        stop_boundary = ''
        stop_candidate_hash = ''
        stop_family_id = ''
        stop_primary_axis = ''
        stop_truth_match = float('nan')
        if int(would_stop_flag) == 1:
            stop_boundary = _safe_str(
                first_row.get('shadow_first_trigger_stage_boundary', '')
            ) or _safe_str(first_row.get('stage_boundary', ''))
            stop_candidate_hash = _safe_str(first_row.get('candidate_hash', ''))
            stop_family_id = _safe_str(first_row.get('family_id', ''))
            stop_primary_axis = _safe_str(first_row.get('shadow_primary_axis', ''))
            stop_truth_match = _safe_float(
                first_row.get('replay_truth_match', float('nan'))
            )
        summary = dict(
            run_id=_safe_str(dict(artifact.get('stage3_diagnostics', {}) or {}).get('space_map_v1', {}).get('run_id', '')),
            artifact_path=_repo_relpath(artifact_path),
            target_panel_name=_safe_str(target_panel_name),
            target_panel_role=_safe_str(target_panel_role),
            target_label=_safe_str(target_label),
            target_order=_safe_int(target_order, 0),
            tier_name=_safe_str(artifact.get('tier', artifact.get('tier_name', ''))),
            text_id=_safe_int(artifact.get('text_id', 0), 0),
            key_seed=_safe_int(artifact.get('key_seed', 0), 0),
            period=_safe_int(artifact.get('period', 0), 0),
            columns=_safe_int(artifact.get('columns', 0), 0),
            best_stage=best_stage,
            best_match_ratio=float(best_match),
            run_type=run_type,
            shadow_rule_id=rule_id,
            would_dump=1,
            would_stop=int(would_stop_flag),
            would_stop_stage_boundary=stop_boundary,
            would_stop_candidate_hash=str(stop_candidate_hash),
            would_stop_family_id=str(stop_family_id),
            would_stop_primary_axis=str(stop_primary_axis),
            would_stop_truth_match=float(stop_truth_match),
            saved_runtime_seconds_proxy=_estimate_saved_runtime_proxy(artifact, stop_boundary),
            potential_saved_evals_proxy=_estimate_saved_evals_proxy(artifact, stop_boundary),
            data_gap_flags=sorted(set([*list(first_row.get('replay_data_gap_flags', []) or [])])),
        )
        summary['shadow_false_stop_label'] = _label_false_stop(summary, artifact)
        summary['would_stop_false_positive'] = int(summary['shadow_false_stop_label'].startswith('false_stop'))
        summary['would_stop_before_true_solution'] = int(summary['shadow_false_stop_label'] == 'false_stop_before_true_solution')
        summaries.append(summary)
    if not summaries:
        summaries.append(
            dict(
                run_id=_safe_str(dict(artifact.get('stage3_diagnostics', {}) or {}).get('space_map_v1', {}).get('run_id', '')),
                artifact_path=_repo_relpath(artifact_path),
                target_panel_name=_safe_str(target_panel_name),
                target_panel_role=_safe_str(target_panel_role),
                target_label=_safe_str(target_label),
                target_order=_safe_int(target_order, 0),
                tier_name=_safe_str(artifact.get('tier', artifact.get('tier_name', ''))),
                text_id=_safe_int(artifact.get('text_id', 0), 0),
                key_seed=_safe_int(artifact.get('key_seed', 0), 0),
                period=_safe_int(artifact.get('period', 0), 0),
                columns=_safe_int(artifact.get('columns', 0), 0),
                best_stage=best_stage,
                best_match_ratio=float(best_match),
                run_type=run_type,
                shadow_rule_id='',
                would_dump=0,
                would_stop=0,
                would_stop_stage_boundary='',
                would_stop_candidate_hash='',
                would_stop_family_id='',
                would_stop_primary_axis='',
                would_stop_truth_match=float('nan'),
                saved_runtime_seconds_proxy=float('nan'),
                potential_saved_evals_proxy=float('nan'),
                data_gap_flags=[],
                shadow_false_stop_label='',
                would_stop_false_positive=0,
                would_stop_before_true_solution=0,
            )
        )
    return summaries


def _flatten_row(
    artifact_path: Path,
    artifact: Mapping[str, Any],
    row: Mapping[str, Any],
    *,
    target_panel_name: str = '',
    target_panel_role: str = '',
    target_label: str = '',
    target_order: int = 0,
) -> dict[str, Any]:
    row_d = dict(row)
    return dict(
        run_id=_safe_str(dict(artifact.get('stage3_diagnostics', {}) or {}).get('space_map_v1', {}).get('run_id', '')),
        artifact_path=_repo_relpath(artifact_path),
        target_panel_name=_safe_str(target_panel_name),
        target_panel_role=_safe_str(target_panel_role),
        target_label=_safe_str(target_label),
        target_order=_safe_int(target_order, 0),
        tier_name=_safe_str(artifact.get('tier', artifact.get('tier_name', ''))),
        text_id=_safe_int(artifact.get('text_id', 0), 0),
        key_seed=_safe_int(artifact.get('key_seed', 0), 0),
        stage_boundary=_safe_str(row_d.get('stage_boundary', '')),
        candidate_hash=_safe_str(row_d.get('candidate_hash', '')),
        parent_candidate_hash=_safe_str(row_d.get('parent_candidate_hash', '')),
        parent_link_kind=_safe_str(row_d.get('parent_link_kind', '')),
        family_view_id=_safe_str(row_d.get('family_view_id', '')),
        family_id=_safe_str(row_d.get('family_id', '')),
        family_id_kind=_safe_str(row_d.get('family_id_kind', '')),
        distance_to_anchor=_safe_float(row_d.get('distance_to_anchor', float('nan'))),
        source=_safe_str(row_d.get('source', '')),
        lane=_safe_str(row_d.get('lane', '')),
        source_rank=_safe_int(row_d.get('source_rank', 0), 0),
        stage_rank=_safe_int(row_d.get('stage_rank', 0), 0),
        init_key_idx=_coerce_int_list(row_d.get('init_key_idx')),
        final_key_idx=_coerce_int_list(row_d.get('final_key_idx')),
        init_plaintext_idx=_coerce_int_list(row_d.get('init_plaintext_idx')),
        final_plaintext_idx=_coerce_int_list(row_d.get('final_plaintext_idx')),
        preview_text=_extract_preview_text(row_d),
        init_score=_safe_float(row_d.get('init_score', float('nan'))),
        final_score=_safe_float(row_d.get('final_score', float('nan'))),
        init_search_score=_safe_float(row_d.get('init_search_score', float('nan'))),
        final_search_score=_safe_float(row_d.get('final_search_score', float('nan'))),
        init_match=_safe_float(row_d.get('init_match', float('nan'))),
        final_match=_safe_float(row_d.get('final_match', float('nan'))),
        score_gain=_safe_float(row_d.get('score_gain', float('nan'))),
        match_gain=_safe_float(row_d.get('match_gain', float('nan'))),
        selected=_safe_int(row_d.get('selected', 0), 0),
        eligible=_safe_int(row_d.get('eligible', 0), 0),
        rejected=_safe_int(row_d.get('rejected', 0), 0),
        selection_policy=_safe_str(row_d.get('selection_policy', '')),
        reject_reason=_safe_str(row_d.get('reject_reason', '')),
        admitted_by_next_stage=_safe_int(row_d.get('admitted_by_next_stage', 0), 0),
        next_stage_accept_reason=_safe_str(row_d.get('next_stage_accept_reason', '')),
        continued_best_candidate_hash=_safe_str(row_d.get('continued_best_candidate_hash', '')),
        continued_best_score=_safe_float(row_d.get('continued_best_score', float('nan'))),
        continued_best_match=_safe_float(row_d.get('continued_best_match', float('nan'))),
        replay_data_gap_flags=sorted(set(str(flag) for flag in list(row_d.get('replay_data_gap_flags', []) or []) if str(flag))),
    )


def analyze_artifact(review_target: Mapping[str, Any] | Path) -> tuple[
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
]:
    if isinstance(review_target, Mapping):
        review_d = dict(review_target)
        artifact_path = Path(review_d.get('artifact_path'))
        artifact = dict(review_d.get('artifact') or {})
        if not artifact:
            artifact = _read_json(artifact_path)
        target_panel_name = _safe_str(review_d.get('target_panel_name', ''))
        target_panel_role = _safe_str(review_d.get('target_panel_role', ''))
        target_label = _safe_str(review_d.get('target_label', ''))
        target_order = _safe_int(review_d.get('target_order', 0), 0)
    else:
        artifact_path = Path(review_target)
        artifact = _read_json(artifact_path)
        target_panel_name = ''
        target_panel_role = ''
        target_label = ''
        target_order = 0
    run_config_path = artifact_path.parents[1] / 'run_config.json'
    run_config = _read_json(run_config_path) if run_config_path.exists() else {}
    rows = [
        _flatten_row(
            artifact_path,
            artifact,
            row,
            target_panel_name=target_panel_name,
            target_panel_role=target_panel_role,
            target_label=target_label,
            target_order=target_order,
        )
        for row in collect_candidate_rows(artifact)
    ]
    ctx = ReplayContext(artifact_path, artifact, run_config)
    rescored_rows: list[dict[str, Any]] = []
    for row in rows:
        rescored_rows.append(dict(row, **_collect_row_replay_scores(row, ctx)))
    rescored_rows = _annotate_shadow_rows(rescored_rows)
    if not bool(SCORE_PANEL_DISABLE_FAMILY_STOP):
        rescored_rows = _annotate_stability(rescored_rows)
    threshold_rows: list[dict[str, Any]] = []
    public_row_rows: list[dict[str, Any]] = []
    for row in rescored_rows:
        row_d = dict(row)
        public_row_rows.append(_strip_private_analysis_fields(row_d))
        threshold_rows.extend(
            [
                _strip_private_analysis_fields(dict(threshold_row))
                for threshold_row in list(row_d.get('_shadow_threshold_matrix_rows', []) or [])
            ]
        )
    run_rows = build_run_shadow_summary(
        artifact_path,
        artifact,
        public_row_rows,
        target_panel_name=target_panel_name,
        target_panel_role=target_panel_role,
        target_label=target_label,
        target_order=target_order,
    )
    return public_row_rows, run_rows, threshold_rows


def build_threshold_sweep_summary(run_rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    rows = [dict(r) for r in run_rows]
    by_rule: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_rule[_safe_str(row.get('shadow_rule_id', ''))].append(row)
    summary_rows: list[dict[str, Any]] = []
    for rule_id, members in sorted(by_rule.items()):
        if not rule_id:
            continue
        summary_rows.append(
            dict(
                shadow_rule_id=rule_id,
                run_count=len(members),
                would_stop_count=sum(int(m.get('would_stop', 0) or 0) for m in members),
                false_positive_count=sum(int(m.get('would_stop_false_positive', 0) or 0) for m in members),
                before_true_solution_count=sum(int(m.get('would_stop_before_true_solution', 0) or 0) for m in members),
                solved_control_count=sum(1 for m in members if _safe_str(m.get('run_type', '')) == 'solved_control'),
                stage35_live_win_count=sum(1 for m in members if _safe_str(m.get('run_type', '')) == 'stage35_live_win'),
                mean_saved_runtime_seconds_proxy=_finite_mean(
                    [
                        _safe_float(
                            m.get('saved_runtime_seconds_proxy', float('nan'))
                        )
                        for m in members
                    ]
                ),
            )
        )
    return dict(
        generated_utc=dt.datetime.now(dt.timezone.utc).isoformat(),
        run_rule_rows=summary_rows,
    )


def build_threshold_matrix_summary(threshold_rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in list(threshold_rows or []):
        row_d = dict(row)
        grouped[
            (
                _safe_str(row_d.get('target_panel_name', '')),
                _safe_str(row_d.get('rule_id', '')),
            )
        ].append(row_d)
    summary_rows: list[dict[str, Any]] = []
    for (panel_name, rule_id), members in sorted(grouped.items()):
        summary_rows.append(
            dict(
                target_panel_name=panel_name,
                rule_id=rule_id,
                row_count=len(members),
                pass_count=sum(int(dict(m).get('pass', 0) or 0) for m in members),
                first_hit_count=sum(int(dict(m).get('is_first_firing_rule', 0) or 0) for m in members),
                nearest_miss_count=sum(
                    1
                    for m in members
                    if int(dict(m).get('pass', 0) or 0) == 0
                    and _safe_int(dict(m).get('failed_gate_count', 0), 0) > 0
                ),
                mean_total_negative_deficit=_finite_mean(
                    [_safe_float(dict(m).get('total_negative_deficit', float('nan'))) for m in members]
                ),
            )
        )
    return dict(
        generated_utc=dt.datetime.now(dt.timezone.utc).isoformat(),
        threshold_rule_rows=summary_rows,
    )


def _select_case_explanation_rows(
    run_rows: Sequence[Mapping[str, Any]],
    row_rows: Sequence[Mapping[str, Any]],
    threshold_rows: Sequence[Mapping[str, Any]],
) -> dict[int, dict[str, Any]]:
    out: dict[int, dict[str, Any]] = {}
    for seed in list(CASE_EXPLANATION_TARGET_SEEDS or []):
        out[int(seed)] = dict(
            key_seed=int(seed),
            run_row={},
            row_rows=[],
            threshold_rows=[],
        )
    for row in list(run_rows or []):
        row_d = dict(row)
        seed = _safe_int(row_d.get('key_seed', 0), 0)
        if seed in out and not out[seed].get('run_row'):
            out[seed]['run_row'] = row_d
    for row in list(row_rows or []):
        row_d = dict(row)
        seed = _safe_int(row_d.get('key_seed', 0), 0)
        if seed in out:
            out[seed]['row_rows'].append(row_d)
    for row in list(threshold_rows or []):
        row_d = dict(row)
        seed = _safe_int(row_d.get('key_seed', 0), 0)
        if seed in out:
            out[seed]['threshold_rows'].append(row_d)
    return out


def _pick_best_row_by_metric(
    rows: Sequence[Mapping[str, Any]],
    *,
    metric_key: str,
    require_stage_boundary: str | None = None,
) -> dict[str, Any]:
    candidates: list[dict[str, Any]] = []
    for row in list(rows or []):
        row_d = dict(row)
        if require_stage_boundary and _safe_str(row_d.get('stage_boundary', '')) != str(require_stage_boundary):
            continue
        metric_value = _safe_float(row_d.get(metric_key, float('nan')))
        if not _is_finite(metric_value):
            continue
        candidates.append(row_d)
    if not candidates:
        return {}
    candidates.sort(
        key=lambda row: (
            -float(_safe_float(dict(row).get(metric_key, float('nan')))),
            -_boundary_sort_key(row)[0],
            _safe_int(dict(row).get('stage_rank', 0), 0),
            _safe_str(dict(row).get('candidate_hash', '')),
        )
    )
    return candidates[0]


def _pick_best_archive_row_by_uplift(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    return _pick_best_row_by_metric(
        rows,
        metric_key='shadow_late_family_search_uplift',
        require_stage_boundary=CONTINUATION_RULE_STAGE_BOUNDARY,
    )


def _pick_current_firing_row(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    candidates = [
        dict(row)
        for row in list(rows or [])
        if int(dict(row).get('shadow_high_score_would_dump', 0) or 0) == 1
    ]
    if not candidates:
        return {}
    candidates.sort(
        key=lambda row: (
            -_boundary_sort_key(row)[0],
            -float(_safe_float(dict(row).get('replay_truth_match', float('-inf')))),
            _safe_int(dict(row).get('stage_rank', 0), 0),
            _safe_str(dict(row).get('candidate_hash', '')),
        )
    )
    return candidates[0]


def _same_nonempty_family(left: Mapping[str, Any], right: Mapping[str, Any]) -> int:
    left_family = _safe_str(dict(left).get('family_id', ''))
    right_family = _safe_str(dict(right).get('family_id', ''))
    return int(bool(left_family) and bool(right_family) and left_family == right_family)


def _same_nonempty_family_id(left_family: Any, right_family: Any) -> int:
    left = _safe_str(left_family)
    right = _safe_str(right_family)
    return int(bool(left) and bool(right) and left == right)


def _case_metric_fields(prefix: str, row: Mapping[str, Any]) -> dict[str, Any]:
    row_d = dict(row or {})
    return {
        f'{prefix}_candidate_hash': _safe_str(row_d.get('candidate_hash', '')),
        f'{prefix}_stage_boundary': _safe_str(row_d.get('stage_boundary', '')),
        f'{prefix}_family_id': _safe_str(row_d.get('family_id', '')),
        f'{prefix}_match': _safe_float(row_d.get('replay_truth_match', float('nan'))),
        f'{prefix}_trust': _safe_float(row_d.get('replay_word_ngram_trust_score', float('nan'))),
        f'{prefix}_xent': _safe_float(row_d.get('replay_word_ngram_report_xent', float('nan'))),
        f'{prefix}_family_support': _safe_int(row_d.get('shadow_family_support_count', 0), 0),
        f'{prefix}_rival_margin': _safe_float(row_d.get('shadow_best_rival_family_margin', float('nan'))),
        f'{prefix}_persistence_count': _safe_int(row_d.get('shadow_late_family_persistence_count', 0), 0),
        f'{prefix}_archive_search_uplift': _safe_float(
            row_d.get('shadow_late_family_search_uplift', float('nan'))
        ),
    }


def _label_case_explanation(case_row: Mapping[str, Any]) -> tuple[str, str, str]:
    row_d = dict(case_row)
    would_dump = _safe_int(row_d.get('would_dump', 0), 0)
    run_type = _safe_str(row_d.get('run_type', ''))
    rule_id = _safe_str(row_d.get('shadow_rule_id', ''))
    best_truth_trust = _safe_float(row_d.get('best_truth_trust', float('nan')))
    best_truth_support = _safe_int(row_d.get('best_truth_family_support', 0), 0)
    best_truth_uplift = _safe_float(row_d.get('best_truth_archive_search_uplift', float('nan')))
    current_firing_match = _safe_float(row_d.get('current_firing_match', float('nan')))
    best_truth_match = _safe_float(row_d.get('best_truth_match', float('nan')))
    if (
        would_dump == 0
        and run_type == 'stage35_live_win'
        and (_is_finite(best_truth_trust) and float(best_truth_trust) < float(min(TRUST_SCORE_FLOORS)))
        and best_truth_support <= 0
        and (not _is_finite(best_truth_uplift) or float(best_truth_uplift) <= 0.0)
    ):
        return (
            'accepted_miss_outside_current_model',
            'mixed',
            'truth_row_not_trust_led',
        )
    if would_dump == 1 and rule_id.startswith('trust'):
        return (
            'trust_false_fire',
            'trust',
            'trust_rule_admits_weak_family',
        )
    if would_dump == 1 and rule_id.startswith('archive_search_uplift'):
        primary = 'archive_rule_prefers_low_truth_uplift'
        if _is_finite(current_firing_match) and _is_finite(best_truth_match):
            if _same_nonempty_family_id(
                row_d.get('current_firing_family_id', ''),
                row_d.get('best_truth_family_id', ''),
            ):
                primary = 'same_family_different_boundary'
            elif float(current_firing_match) + 1e-9 < float(best_truth_match):
                primary = 'archive_rule_prefers_low_truth_uplift'
        return (
            'archive_false_fire',
            'archive_uplift',
            primary,
        )
    return ('ambiguous', 'none', 'different_family_disagreement')


def build_case_explanations(
    run_rows: Sequence[Mapping[str, Any]],
    row_rows: Sequence[Mapping[str, Any]],
    threshold_rows: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    selected = _select_case_explanation_rows(run_rows, row_rows, threshold_rows)
    out_rows: list[dict[str, Any]] = []
    for seed in list(CASE_EXPLANATION_TARGET_SEEDS or []):
        case = dict(selected.get(int(seed), {}) or {})
        run_row = dict(case.get('run_row') or {})
        if not run_row:
            continue
        case_rows = [dict(row) for row in list(case.get('row_rows', []) or [])]
        best_truth = _pick_best_row_by_metric(case_rows, metric_key='replay_truth_match')
        best_trust = _pick_best_row_by_metric(case_rows, metric_key='replay_word_ngram_trust_score')
        best_uplift = _pick_best_row_by_metric(case_rows, metric_key='shadow_late_family_search_uplift')
        best_archive_uplift = _pick_best_archive_row_by_uplift(case_rows)
        current_firing = _pick_current_firing_row(case_rows)
        case_row = dict(
            key_seed=_safe_int(run_row.get('key_seed', 0), 0),
            target_panel_name=_safe_str(run_row.get('target_panel_name', '')),
            target_panel_role=_safe_str(run_row.get('target_panel_role', '')),
            run_type=_safe_str(run_row.get('run_type', '')),
            would_dump=_safe_int(run_row.get('would_dump', 0), 0),
            would_stop=_safe_int(run_row.get('would_stop', 0), 0),
            shadow_rule_id=_safe_str(run_row.get('shadow_rule_id', '')),
            **_case_metric_fields('best_truth', best_truth),
            best_truth_nearest_pass_rule_id=_safe_str(best_truth.get('shadow_nearest_pass_rule_id', '')),
            best_truth_nearest_pass_blocker=_safe_str(best_truth.get('shadow_nearest_pass_blocker', '')),
            best_truth_nearest_pass_margin=_safe_float(best_truth.get('shadow_nearest_pass_margin', float('nan'))),
            best_truth_nearest_pass_deficit=_safe_float(best_truth.get('shadow_nearest_pass_deficit', float('nan'))),
            **_case_metric_fields('best_trust', best_trust),
            **_case_metric_fields('best_uplift', best_uplift),
            **_case_metric_fields('best_archive_uplift', best_archive_uplift),
            **_case_metric_fields('current_firing', current_firing),
            truth_equals_trust_family=_same_nonempty_family(best_truth, best_trust),
            truth_equals_uplift_family=_same_nonempty_family(best_truth, best_uplift),
            truth_equals_firing_family=_same_nonempty_family(best_truth, current_firing),
            trust_equals_firing_family=_same_nonempty_family(best_trust, current_firing),
            uplift_equals_firing_family=_same_nonempty_family(best_uplift, current_firing),
        )
        shape_label, axis_label, primary_explanation = _label_case_explanation(case_row)
        case_row.update(
            case_shape_label=shape_label,
            decision_axis_label=axis_label,
            primary_explanation=primary_explanation,
        )
        out_rows.append(case_row)
    return out_rows


def build_case_explanation_summary(
    case_rows: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    shape_counts: Counter[str] = Counter()
    axis_counts: Counter[str] = Counter()
    seeds_by_shape: dict[str, list[int]] = defaultdict(list)
    seeds_by_axis: dict[str, list[int]] = defaultdict(list)
    for row in list(case_rows or []):
        row_d = dict(row)
        shape = _safe_str(row_d.get('case_shape_label', ''))
        axis = _safe_str(row_d.get('decision_axis_label', ''))
        seed = _safe_int(row_d.get('key_seed', 0), 0)
        shape_counts[shape] += 1
        axis_counts[axis] += 1
        seeds_by_shape[shape].append(seed)
        seeds_by_axis[axis].append(seed)
    return dict(
        generated_utc=dt.datetime.now(dt.timezone.utc).isoformat(),
        target_seed_count=len(list(case_rows or [])),
        shape_counts=dict(sorted(shape_counts.items())),
        decision_axis_counts=dict(sorted(axis_counts.items())),
        seeds_by_shape={key: sorted(values) for key, values in sorted(seeds_by_shape.items())},
        seeds_by_decision_axis={key: sorted(values) for key, values in sorted(seeds_by_axis.items())},
    )


def write_case_explanations_markdown(
    output_dir: Path,
    case_rows: Sequence[Mapping[str, Any]],
) -> None:
    lines = [
        '# case_explanations',
        '',
    ]
    for row in sorted(
        [dict(r) for r in list(case_rows or [])],
        key=lambda row: _safe_int(row.get('key_seed', 0), 0),
    ):
        seed = _safe_int(row.get('key_seed', 0), 0)
        lines.extend(
            [
                f'## seed{seed}',
                '',
                f'- panel: `{_safe_str(row.get("target_panel_name", ""))}`',
                f'- verdict: `dump={_safe_int(row.get("would_dump", 0), 0)}` `stop={_safe_int(row.get("would_stop", 0), 0)}`',
                f'- rule: `{_safe_str(row.get("shadow_rule_id", ""))}`',
                '',
                '| view | boundary | family | truth | trust | xent | support | rival | persistence | uplift |',
                '| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |',
            ]
        )
        for prefix, label in (
            ('best_truth', 'best_truth'),
            ('best_trust', 'best_trust'),
            ('best_uplift', 'best_uplift'),
            ('best_archive_uplift', 'best_archive_uplift'),
            ('current_firing', 'current_firing'),
        ):
            lines.append(
                '| {label} | {boundary} | {family} | {truth:.3f} | {trust:.3f} | {xent:.3f} | {support} | {rival:.3f} | {persist} | {uplift:.3f} |'.format(
                    label=label,
                    boundary=_safe_str(row.get(f'{prefix}_stage_boundary', '')),
                    family=_safe_str(row.get(f'{prefix}_family_id', '')),
                    truth=_safe_float(row.get(f'{prefix}_match', float('nan'))),
                    trust=_safe_float(row.get(f'{prefix}_trust', float('nan'))),
                    xent=_safe_float(row.get(f'{prefix}_xent', float('nan'))),
                    support=_safe_int(row.get(f'{prefix}_family_support', 0), 0),
                    rival=_safe_float(row.get(f'{prefix}_rival_margin', float('nan'))),
                    persist=_safe_int(row.get(f'{prefix}_persistence_count', 0), 0),
                    uplift=_safe_float(row.get(f'{prefix}_archive_search_uplift', float('nan'))),
                )
            )
        lines.extend(
            [
                '',
                f'- current rule action: `{_safe_str(row.get("shadow_rule_id", "")) or "no_dump"}`',
                f'- best-truth nearest miss: `{_safe_str(row.get("best_truth_nearest_pass_rule_id", ""))}` blocker=`{_safe_str(row.get("best_truth_nearest_pass_blocker", ""))}` signed_margin=`{_safe_float(row.get("best_truth_nearest_pass_margin", float("nan"))):.3f}` deficit=`{_safe_float(row.get("best_truth_nearest_pass_deficit", float("nan"))):.3f}`',
                f'- interpretation: `{_safe_str(row.get("case_shape_label", ""))}` / `{_safe_str(row.get("decision_axis_label", ""))}` / `{_safe_str(row.get("primary_explanation", ""))}`',
                '',
            ]
        )
    (output_dir / 'case_explanations.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')


def build_data_gap_report(row_rows: Sequence[Mapping[str, Any]], run_rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    row_gap_counts: Counter[str] = Counter()
    for row in row_rows:
        for flag in list(dict(row).get('replay_data_gap_flags', []) or []):
            row_gap_counts[str(flag)] += 1
    run_gap_counts: Counter[str] = Counter()
    for row in run_rows:
        for flag in list(dict(row).get('data_gap_flags', []) or []):
            run_gap_counts[str(flag)] += 1
    return dict(
        generated_utc=dt.datetime.now(dt.timezone.utc).isoformat(),
        row_gap_counts=dict(sorted(row_gap_counts.items())),
        run_gap_counts=dict(sorted(run_gap_counts.items())),
    )


def write_summary_markdown(output_dir: Path, run_rows: Sequence[Mapping[str, Any]], sweep_summary: Mapping[str, Any], gap_report: Mapping[str, Any]) -> None:
    lines = [
        '# score_stop_shadow_v2',
        '',
        f'- generated: `{dt.datetime.now(dt.timezone.utc).isoformat()}`',
        f'- analysis mode: `{str(ANALYSIS_MODE)}`',
        f'- analyzed runs: `{int(len(run_rows))}`',
        '',
        '## Rule summary',
        '',
        '| rule | runs | false positives | solved controls | stage35 live wins | mean saved runtime proxy |',
        '| --- | ---: | ---: | ---: | ---: | ---: |',
    ]
    for row in list(dict(sweep_summary).get('run_rule_rows', []) or []):
        lines.append(
            '| {rule} | {runs} | {fp} | {sc} | {wins} | {saved:.3f} |'.format(
                rule=_safe_str(dict(row).get('shadow_rule_id', '')),
                runs=_safe_int(dict(row).get('run_count', 0), 0),
                fp=_safe_int(dict(row).get('false_positive_count', 0), 0),
                sc=_safe_int(dict(row).get('solved_control_count', 0), 0),
                wins=_safe_int(dict(row).get('stage35_live_win_count', 0), 0),
                saved=_safe_float(dict(row).get('mean_saved_runtime_seconds_proxy', float('nan'))),
            )
        )
    panel_groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in list(run_rows or []):
        panel_groups[_safe_str(dict(row).get('target_panel_name', ''))].append(dict(row))
    for panel_name, heading in (('core', 'Core benchmark panel'), ('pressure', 'Pressure falsification panel')):
        members = list(panel_groups.get(panel_name, []) or [])
        if not members:
            continue
        lines.extend([
            '',
            f'## {heading}',
            '',
            '| seed | run type | dump | stop | rule |',
            '| --- | --- | ---: | ---: | --- |',
        ])
        for row in sorted(
            members,
            key=lambda member: (
                _safe_int(dict(member).get('target_order', 0), 0),
                _safe_int(dict(member).get('key_seed', 0), 0),
            ),
        ):
            row_d = dict(row)
            lines.append(
                '| {seed} | {run_type} | {dump} | {stop} | {rule} |'.format(
                    seed=_safe_int(row_d.get('key_seed', 0), 0),
                    run_type=_safe_str(row_d.get('run_type', '')),
                    dump=_safe_int(row_d.get('would_dump', 0), 0),
                    stop=_safe_int(row_d.get('would_stop', 0), 0),
                    rule=_safe_str(row_d.get('shadow_rule_id', '')),
                )
            )
    if panel_groups.get('core') and panel_groups.get('pressure'):
        lines.extend([
            '',
            '## Combined caution note',
            '',
            '- core benchmark panel remains the continuity benchmark',
            '- pressure panel is adversarial falsification pressure, not continuity',
        ])
    lines.extend(['', '## Row data-gap counts', ''])
    for key, value in sorted(dict(gap_report).get('row_gap_counts', {}).items()):
        lines.append(f'- `{key}`: `{int(value)}`')
    (output_dir / 'summary.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')


def main() -> None:
    output_dir = OUTPUT_BASE_DIR / f'{_utc_label()}__score_stop_shadow_v2'
    review_targets = discover_review_targets()
    all_row_rows: list[dict[str, Any]] = []
    all_run_rows: list[dict[str, Any]] = []
    all_threshold_rows: list[dict[str, Any]] = []
    for review_target in review_targets:
        review_d = dict(review_target)
        artifact_path = Path(review_d.get('artifact_path'))
        try:
            row_rows, run_rows, threshold_rows = analyze_artifact(review_target)
        except Exception as exc:
            all_run_rows.append(
                dict(
                    run_id='',
                    artifact_path=_repo_relpath(artifact_path),
                    target_panel_name=_safe_str(review_d.get('target_panel_name', '')),
                    target_panel_role=_safe_str(review_d.get('target_panel_role', '')),
                    target_label=_safe_str(review_d.get('target_label', '')),
                    target_order=_safe_int(review_d.get('target_order', 0), 0),
                    tier_name='',
                    text_id=0,
                    key_seed=0,
                    period=0,
                    columns=0,
                    best_stage='',
                    best_match_ratio=float('nan'),
                    run_type='analysis_error',
                    shadow_rule_id='',
                    would_dump=0,
                    would_stop=0,
                    would_stop_stage_boundary='',
                    would_stop_candidate_hash='',
                    would_stop_family_id='',
                    would_stop_primary_axis='',
                    would_stop_truth_match=float('nan'),
                    saved_runtime_seconds_proxy=float('nan'),
                    potential_saved_evals_proxy=float('nan'),
                    data_gap_flags=[f'analysis_failed:{type(exc).__name__}'],
                    shadow_false_stop_label='',
                    would_stop_false_positive=0,
                    would_stop_before_true_solution=0,
                )
            )
            continue
        all_row_rows.extend(row_rows)
        all_run_rows.extend(run_rows)
        all_threshold_rows.extend(threshold_rows)

    sweep_summary = build_threshold_sweep_summary(all_run_rows)
    threshold_matrix_summary = build_threshold_matrix_summary(all_threshold_rows)
    case_rows = build_case_explanations(all_run_rows, all_row_rows, all_threshold_rows)
    case_summary = build_case_explanation_summary(case_rows)
    gap_report = build_data_gap_report(all_row_rows, all_run_rows)

    _write_jsonl(output_dir / 'row_scores.jsonl', all_row_rows)
    _write_jsonl(output_dir / 'gate_margin_rows.jsonl', all_row_rows)
    _write_jsonl(output_dir / 'run_shadow_summary.jsonl', all_run_rows)
    _write_jsonl(output_dir / 'threshold_matrix_rows.jsonl', all_threshold_rows)
    _write_jsonl(output_dir / 'case_explanations.jsonl', case_rows)
    _write_json(output_dir / 'threshold_sweep_summary.json', sweep_summary)
    _write_json(output_dir / 'threshold_matrix_summary.json', threshold_matrix_summary)
    _write_json(output_dir / 'case_explanation_summary.json', case_summary)
    _write_json(output_dir / 'data_gap_report.json', gap_report)
    write_summary_markdown(output_dir, all_run_rows, sweep_summary, gap_report)
    write_case_explanations_markdown(output_dir, case_rows)

    print(
        '[score_stop_shadow_v2] '
        + f'artifacts={int(len(review_targets))} '
        + f'rows={int(len(all_row_rows))} '
        + f'runs={int(len(all_run_rows))} '
        + f'output={_repo_relpath(output_dir)}',
        flush=True,
    )


if __name__ == '__main__':
    main()
