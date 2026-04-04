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
ANALYSIS_MODE = 'score_panel_v1'
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
SOLVED_MATCH_THRESHOLD = 0.999
REQUIRE_BATCH_SCORING = True
BATCH_CHUNK_SIZE = 256


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


def _qualifies_dump(row: Mapping[str, Any], rows_in_pool: Sequence[Mapping[str, Any]], trust_floor: float, xent_ceiling: float, rival_margin_floor: float, family_support_floor: int) -> tuple[bool, dict[str, Any]]:
    row_d = dict(row)
    trust = _safe_float(row_d.get('replay_word_ngram_trust_score', float('nan')))
    xent = _safe_float(row_d.get('replay_word_ngram_report_xent', float('nan')))
    active = bool(row_d.get('replay_word_ngram_active', False))
    family_id = _safe_str(row_d.get('family_id', ''))
    axis_name, rival_margin = _best_rival_margin(row_d, rows_in_pool)
    anchor_margin = _anchor_margin(row_d, rows_in_pool)
    support_count = _family_support_count(rows_in_pool, family_id, float(trust_floor), float(xent_ceiling))
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
    return ok, dict(
        shadow_primary_axis=axis_name,
        shadow_anchor_margin=float(anchor_margin),
        shadow_best_rival_family_margin=float(rival_margin),
        shadow_family_support_count=int(support_count),
    )


def _annotate_shadow_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped = _group_rows_by_pool(rows)
    out_rows = [dict(row) for row in rows]
    for idx, row in enumerate(out_rows):
        rows_in_pool = grouped.get((_safe_str(row.get('artifact_path', '')), _safe_str(row.get('stage_boundary', ''))), [])
        best_dump = None
        metrics_out: dict[str, Any] = {}
        for trust_floor in TRUST_SCORE_FLOORS:
            for xent_ceiling in REPORT_XENT_CEILINGS:
                for rival_margin_floor in RIVAL_MARGIN_FLOORS:
                    for family_support_floor in FAMILY_SUPPORT_FLOORS:
                        ok, metrics = _qualifies_dump(
                            row,
                            rows_in_pool,
                            trust_floor=float(trust_floor),
                            xent_ceiling=float(xent_ceiling),
                            rival_margin_floor=float(rival_margin_floor),
                            family_support_floor=int(family_support_floor),
                        )
                        if ok:
                            best_dump = f'trust{trust_floor:.2f}_xent{xent_ceiling:.2f}_margin{rival_margin_floor:.2f}_support{int(family_support_floor)}'
                            metrics_out = dict(metrics)
                            break
                    if best_dump:
                        break
                if best_dump:
                    break
            if best_dump:
                break
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
            for threshold in sorted(BOUNDARY_STABILITY_COUNTS, reverse=True):
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


def build_run_shadow_summary(artifact_path: Path, artifact: Mapping[str, Any], rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
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


def _flatten_row(artifact_path: Path, artifact: Mapping[str, Any], row: Mapping[str, Any]) -> dict[str, Any]:
    row_d = dict(row)
    return dict(
        run_id=_safe_str(dict(artifact.get('stage3_diagnostics', {}) or {}).get('space_map_v1', {}).get('run_id', '')),
        artifact_path=_repo_relpath(artifact_path),
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


def analyze_artifact(artifact_path: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    artifact = _read_json(artifact_path)
    run_config_path = artifact_path.parents[1] / 'run_config.json'
    run_config = _read_json(run_config_path) if run_config_path.exists() else {}
    rows = [_flatten_row(artifact_path, artifact, row) for row in collect_candidate_rows(artifact)]
    ctx = ReplayContext(artifact_path, artifact, run_config)
    rescored_rows: list[dict[str, Any]] = []
    for row in rows:
        rescored_rows.append(dict(row, **_collect_row_replay_scores(row, ctx)))
    rescored_rows = _annotate_shadow_rows(rescored_rows)
    if not bool(SCORE_PANEL_DISABLE_FAMILY_STOP):
        rescored_rows = _annotate_stability(rescored_rows)
    run_rows = build_run_shadow_summary(artifact_path, artifact, rescored_rows)
    return rescored_rows, run_rows


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
    lines.extend(['', '## Row data-gap counts', ''])
    for key, value in sorted(dict(gap_report).get('row_gap_counts', {}).items()):
        lines.append(f'- `{key}`: `{int(value)}`')
    (output_dir / 'summary.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')


def main() -> None:
    output_dir = OUTPUT_BASE_DIR / f'{_utc_label()}__score_stop_shadow_v2'
    artifact_paths = discover_artifact_paths()
    all_row_rows: list[dict[str, Any]] = []
    all_run_rows: list[dict[str, Any]] = []
    for artifact_path in artifact_paths:
        try:
            row_rows, run_rows = analyze_artifact(artifact_path)
        except Exception as exc:
            all_run_rows.append(
                dict(
                    run_id='',
                    artifact_path=_repo_relpath(artifact_path),
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

    sweep_summary = build_threshold_sweep_summary(all_run_rows)
    gap_report = build_data_gap_report(all_row_rows, all_run_rows)

    _write_jsonl(output_dir / 'row_scores.jsonl', all_row_rows)
    _write_jsonl(output_dir / 'run_shadow_summary.jsonl', all_run_rows)
    _write_json(output_dir / 'threshold_sweep_summary.json', sweep_summary)
    _write_json(output_dir / 'data_gap_report.json', gap_report)
    write_summary_markdown(output_dir, all_run_rows, sweep_summary, gap_report)

    print(
        '[score_stop_shadow_v2] '
        + f'artifacts={int(len(artifact_paths))} '
        + f'rows={int(len(all_row_rows))} '
        + f'runs={int(len(all_run_rows))} '
        + f'output={_repo_relpath(output_dir)}',
        flush=True,
    )


if __name__ == '__main__':
    main()
