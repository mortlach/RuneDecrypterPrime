from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from statistics import mean
from typing import Any, Dict, Mapping, Sequence


LIVE_FEATURE_AUDIT_FIELDS: tuple[tuple[str, str, bool], ...] = (
    ("final_score", "score_features", True),
    ("score_gain", "score_features", True),
    ("source_rank", "structural_features", True),
    ("eligible_novel_challenger", "structural_features", True),
    ("is_non_anchor", "structural_features", True),
    ("is_phasea_selected", "structural_features", True),
    ("novelty_distance_to_anchor", "structural_features", True),
    ("word_ngram_score", "lexical_features", True),
    ("plausible_fragment_count", "lexical_features", True),
    ("longest_plausible_run", "lexical_features", True),
    ("dictionary_fragment_density", "lexical_features", True),
    ("garbage_penalty", "lexical_features", True),
    ("init_score", "score_auxiliary", False),
    ("init_search_score", "score_auxiliary", False),
    ("score_gap_to_winner", "score_auxiliary", False),
    ("score_gap_to_anchor", "score_auxiliary", False),
    ("source", "structural_auxiliary", False),
    ("lane", "structural_auxiliary", False),
    ("selection_bucket", "structural_auxiliary", False),
    ("selected_by_novel_policy", "structural_auxiliary", False),
    ("novelty_min_distance_to_selected_challenger", "structural_auxiliary", False),
)


def _safe_float(value: Any, default: float = float("nan")) -> float:
    try:
        out = float(value)
    except (TypeError, ValueError):
        return float(default)
    return float(out)


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return int(default)


def _finite_or_zero(value: Any) -> float:
    out = _safe_float(value)
    return float(out) if math.isfinite(out) else 0.0


def _value_present(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, float):
        return bool(math.isfinite(value))
    return True


def load_late_stage_frontier_fixture(path: Path) -> Dict[str, Any]:
    return dict(json.loads(path.read_text(encoding="utf-8")))


def load_phasec_truth_gap_rows(path: Path) -> list[Dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, list):
        return [dict(row) for row in payload if isinstance(row, Mapping)]
    if isinstance(payload, Mapping):
        rows = payload.get("rows", [])
        return [dict(row) for row in list(rows) if isinstance(row, Mapping)]
    return []


def build_truth_gap_benchmark_summary(
    rows: Sequence[Mapping[str, Any]] | None,
) -> Dict[str, Any]:
    norm_rows = [dict(row) for row in list(rows or []) if isinstance(row, Mapping)]
    truth_gaps = [
        _safe_float(row.get("truth_gap_vs_winner"))
        for row in norm_rows
        if math.isfinite(_safe_float(row.get("truth_gap_vs_winner")))
    ]
    score_gaps = [
        _safe_float(row.get("score_gap_vs_winner"))
        for row in norm_rows
        if math.isfinite(_safe_float(row.get("score_gap_vs_winner")))
    ]
    disagreement_rows = [
        row
        for row in norm_rows
        if _safe_int(row.get("winner_and_best_truth_differ", 0), 0) == 1
    ]
    winner_source_counts: Dict[str, int] = {}
    challenger_source_counts: Dict[str, int] = {}
    start_policy_counts: Dict[str, int] = {}
    for row in norm_rows:
        winner_source = str(row.get("winner_source", "") or "")
        challenger_source = str(row.get("challenger_source", "") or "")
        start_policy = str(row.get("phaseC_start_policy", "") or "")
        winner_source_counts[winner_source] = winner_source_counts.get(winner_source, 0) + 1
        challenger_source_counts[challenger_source] = (
            challenger_source_counts.get(challenger_source, 0) + 1
        )
        start_policy_counts[start_policy] = start_policy_counts.get(start_policy, 0) + 1
    top_row = max(
        disagreement_rows,
        key=lambda row: _safe_float(row.get("truth_gap_vs_winner"), float("-inf")),
        default={},
    )
    distinct_patterns = build_truth_gap_pattern_rows(norm_rows)
    return dict(
        row_count=int(len(norm_rows)),
        disagreement_row_count=int(len(disagreement_rows)),
        mean_truth_gap=(float(mean(truth_gaps)) if truth_gaps else None),
        max_truth_gap=(
            float(max(truth_gaps))
            if truth_gaps
            else None
        ),
        mean_score_gap=(float(mean(score_gaps)) if score_gaps else None),
        winner_source_counts=winner_source_counts,
        challenger_source_counts=challenger_source_counts,
        start_policy_counts=start_policy_counts,
        distinct_pattern_count=int(len(distinct_patterns)),
        distinct_patterns=distinct_patterns,
        top_truth_gap_row=dict(top_row),
    )


def build_truth_gap_pattern_rows(
    rows: Sequence[Mapping[str, Any]] | None,
) -> list[Dict[str, Any]]:
    pattern_map: Dict[tuple[Any, ...], Dict[str, Any]] = {}
    for row_obj in list(rows or []):
        if not isinstance(row_obj, Mapping):
            continue
        row = dict(row_obj)
        key = (
            str(row.get("winner_candidate_hash", "") or ""),
            str(row.get("challenger_candidate_hash", "") or ""),
            str(row.get("winner_source", "") or ""),
            str(row.get("challenger_source", "") or ""),
            str(row.get("phaseC_start_policy", "") or ""),
            int(_safe_int(row.get("phaseB_top_n_used", 0), 0)),
            round(_safe_float(row.get("truth_gap_vs_winner"), 0.0), 6),
            round(_safe_float(row.get("score_gap_vs_winner"), 0.0), 6),
        )
        if key not in pattern_map:
            pattern_map[key] = dict(
                count=0,
                winner_candidate_hash=key[0],
                challenger_candidate_hash=key[1],
                winner_source=key[2],
                challenger_source=key[3],
                phaseC_start_policy=key[4],
                phaseB_top_n_used=key[5],
                truth_gap_vs_winner=key[6],
                score_gap_vs_winner=key[7],
            )
        pattern_map[key]["count"] = int(pattern_map[key]["count"]) + 1
    return sorted(
        (dict(row) for row in pattern_map.values()),
        key=lambda row: (
            -_safe_int(row.get("count", 0), 0),
            -_safe_float(row.get("truth_gap_vs_winner"), float("-inf")),
        ),
    )


def _truth_gap_pattern_key(row: Mapping[str, Any]) -> tuple[Any, ...]:
    row_obj = dict(row or {})
    return (
        str(row_obj.get("winner_candidate_hash", "") or ""),
        str(row_obj.get("challenger_candidate_hash", "") or ""),
        str(row_obj.get("winner_source", "") or ""),
        str(row_obj.get("challenger_source", "") or ""),
        str(row_obj.get("phaseC_start_policy", "") or ""),
        int(_safe_int(row_obj.get("phaseB_top_n_used", 0), 0)),
        round(_safe_float(row_obj.get("truth_gap_vs_winner"), 0.0), 6),
        round(_safe_float(row_obj.get("score_gap_vs_winner"), 0.0), 6),
    )


def build_late_stage_candidate_feature_table(
    fixture: Mapping[str, Any],
) -> list[Dict[str, Any]]:
    fixture_obj = dict(fixture or {})
    candidates = [
        dict(row)
        for row in list(fixture_obj.get("candidates", []) or [])
        if isinstance(row, Mapping)
    ]
    winner_hash = str(fixture_obj.get("score_selected_winner_hash", "") or "")
    oracle_hash = str(fixture_obj.get("oracle_best_explored_hash", "") or "")
    anchor_row = next(
        (
            dict(row)
            for row in candidates
            if str(row.get("lane", "") or "") == "anchor"
        ),
        {},
    )
    winner_row = next(
        (
            dict(row)
            for row in candidates
            if str(row.get("candidate_hash", "") or "") == winner_hash
        ),
        anchor_row,
    )
    anchor_score = _safe_float(anchor_row.get("final_score"))
    winner_score = _safe_float(winner_row.get("final_score"))

    out: list[Dict[str, Any]] = []
    for row in candidates:
        final_score = _safe_float(row.get("final_score"))
        init_score = _safe_float(row.get("init_score"))
        score_gain = _safe_float(row.get("score_gain"))
        row_out = dict(
            candidate_hash=str(row.get("candidate_hash", "") or ""),
            lane=str(row.get("lane", "") or ""),
            source=str(row.get("source", "") or ""),
            source_rank=_safe_int(row.get("source_rank", 0), 0),
            selection_bucket=str(row.get("selection_bucket", "") or ""),
            selected_by_novel_policy=_safe_int(
                row.get("selected_by_novel_policy", 0), 0
            ),
            eligible_novel_challenger=_safe_int(
                row.get("eligible_novel_challenger", 0), 0
            ),
            is_anchor=int(1 if str(row.get("lane", "") or "") == "anchor" else 0),
            is_non_anchor=int(1 if str(row.get("lane", "") or "") != "anchor" else 0),
            is_phasea_selected=int(
                1 if str(row.get("source", "") or "") == "phaseA_selected" else 0
            ),
            is_phaseb_topk_source=int(
                1 if str(row.get("source", "") or "") == "phaseB_topk" else 0
            ),
            is_stage3_best_phaseb_source=int(
                1
                if str(row.get("source", "") or "") == "stage3_best_phaseB"
                else 0
            ),
            is_score_selected_winner=int(
                1 if str(row.get("candidate_hash", "") or "") == winner_hash else 0
            ),
            is_oracle_best_explored=int(
                1 if str(row.get("candidate_hash", "") or "") == oracle_hash else 0
            ),
            final_score=(float(final_score) if math.isfinite(final_score) else None),
            init_score=(float(init_score) if math.isfinite(init_score) else None),
            score_gain=(float(score_gain) if math.isfinite(score_gain) else None),
            init_search_score=(
                float(_safe_float(row.get("init_search_score")))
                if math.isfinite(_safe_float(row.get("init_search_score")))
                else None
            ),
            final_match=(
                float(_safe_float(row.get("final_match")))
                if math.isfinite(_safe_float(row.get("final_match")))
                else None
            ),
            init_match=(
                float(_safe_float(row.get("init_match")))
                if math.isfinite(_safe_float(row.get("init_match")))
                else None
            ),
            score_gap_to_winner=(
                float(final_score - winner_score)
                if math.isfinite(final_score) and math.isfinite(winner_score)
                else None
            ),
            score_gap_to_anchor=(
                float(final_score - anchor_score)
                if math.isfinite(final_score) and math.isfinite(anchor_score)
                else None
            ),
            novelty_distance_to_anchor=(
                _safe_int(row.get("novelty_distance_to_anchor"))
                if row.get("novelty_distance_to_anchor", None) is not None
                else None
            ),
            novelty_min_distance_to_selected_challenger=(
                _safe_int(row.get("novelty_min_distance_to_selected_challenger"))
                if row.get("novelty_min_distance_to_selected_challenger", None)
                is not None
                else None
            ),
            replay_final_key_available=int(1 if list(row.get("final_key_idx", [])) else 0),
            replay_final_plaintext_available=int(
                1 if list(row.get("final_plaintext_idx", [])) else 0
            ),
            word_ngram_score=(
                float(_safe_float(row.get("word_ngram_score")))
                if math.isfinite(_safe_float(row.get("word_ngram_score")))
                else None
            ),
            plausible_fragment_count=(
                _safe_int(row.get("plausible_fragment_count"))
                if row.get("plausible_fragment_count", None) is not None
                else None
            ),
            longest_plausible_run=(
                _safe_int(row.get("longest_plausible_run"))
                if row.get("longest_plausible_run", None) is not None
                else None
            ),
            dictionary_fragment_density=(
                float(_safe_float(row.get("dictionary_fragment_density")))
                if math.isfinite(_safe_float(row.get("dictionary_fragment_density")))
                else None
            ),
            garbage_penalty=(
                float(_safe_float(row.get("garbage_penalty")))
                if math.isfinite(_safe_float(row.get("garbage_penalty")))
                else None
            ),
        )
        out.append(row_out)
    return out


def build_frontier_trial_material_rows(
    fixture: Mapping[str, Any],
) -> list[Dict[str, Any]]:
    candidates = [
        dict(row)
        for row in list(dict(fixture or {}).get("candidates", []) or [])
        if isinstance(row, Mapping)
    ]
    out: list[Dict[str, Any]] = []
    for row in candidates:
        final_key_idx = [
            _safe_int(value)
            for value in list(row.get("final_key_idx", []) or [])
        ]
        final_plaintext_idx = [
            _safe_int(value)
            for value in list(row.get("final_plaintext_idx", []) or [])
        ]
        out.append(
            dict(
                candidate_hash=str(row.get("candidate_hash", "") or ""),
                lane=str(row.get("lane", "") or ""),
                source=str(row.get("source", "") or ""),
                source_rank=_safe_int(row.get("source_rank", 0), 0),
                final_key_idx=final_key_idx,
                final_plaintext_idx=final_plaintext_idx,
                replay_material_complete=int(
                    1 if final_key_idx and final_plaintext_idx else 0
                ),
            )
        )
    return out


def select_legacy_frontier_winner(
    feature_rows: Sequence[Mapping[str, Any]],
    *,
    winner_hash: str = "",
) -> Dict[str, Any]:
    rows = [dict(row) for row in list(feature_rows or []) if isinstance(row, Mapping)]
    if winner_hash:
        for row in rows:
            if str(row.get("candidate_hash", "") or "") == str(winner_hash):
                return dict(row)
    return dict(
        max(
            rows,
            key=lambda row: (
                _safe_float(row.get("final_score"), float("-inf")),
                _safe_float(row.get("final_match"), float("-inf")),
                -_safe_int(row.get("source_rank", 0), 0),
            ),
            default={},
        )
    )


@dataclass(frozen=True)
class WeightedLateStageRerankerConfig:
    final_score_weight: float = 1.0
    score_gain_weight: float = 0.75
    init_score_weight: float = 0.0
    init_search_score_weight: float = 0.0
    score_gap_to_winner_weight: float = 0.0
    score_gap_to_anchor_weight: float = 0.0
    novelty_distance_weight: float = 0.0001
    eligible_novel_bonus: float = 0.005
    non_anchor_bonus: float = 0.015
    phasea_selected_bonus: float = 0.003
    phaseb_topk_penalty_weight: float = 0.0
    stage3_best_phaseb_penalty_weight: float = 0.0
    source_rank_penalty_weight: float = 0.002
    anchor_penalty: float = 0.01
    word_ngram_weight: float = 0.0
    plausible_fragment_weight: float = 0.0
    longest_plausible_run_weight: float = 0.0
    dictionary_fragment_density_weight: float = 0.0
    garbage_penalty_weight: float = 0.0


@dataclass(frozen=True)
class PairwiseLateStageRerankerConfig:
    final_score_diff_weight: float = 0.5
    score_gain_diff_weight: float = 0.8
    novelty_distance_diff_weight: float = 0.0001
    eligible_novel_diff_weight: float = 0.01
    non_anchor_diff_weight: float = 0.02
    phasea_selected_diff_weight: float = 0.004
    source_rank_penalty_diff_weight: float = 0.002
    anchor_penalty_diff_weight: float = 0.015
    word_ngram_diff_weight: float = 0.0
    plausible_fragment_diff_weight: float = 0.0
    longest_plausible_run_diff_weight: float = 0.0
    dictionary_fragment_density_diff_weight: float = 0.0
    garbage_penalty_diff_weight: float = 0.0


def build_weighted_score_only_config() -> WeightedLateStageRerankerConfig:
    return WeightedLateStageRerankerConfig(
        final_score_weight=1.0,
        score_gain_weight=0.75,
        novelty_distance_weight=0.0,
        eligible_novel_bonus=0.0,
        non_anchor_bonus=0.0,
        phasea_selected_bonus=0.0,
        source_rank_penalty_weight=0.0,
        anchor_penalty=0.0,
        word_ngram_weight=0.0,
        plausible_fragment_weight=0.0,
        longest_plausible_run_weight=0.0,
        dictionary_fragment_density_weight=0.0,
        garbage_penalty_weight=0.0,
    )


def build_weighted_score_plus_novelty_config() -> WeightedLateStageRerankerConfig:
    return WeightedLateStageRerankerConfig(
        final_score_weight=1.0,
        score_gain_weight=0.75,
        novelty_distance_weight=0.0001,
        eligible_novel_bonus=0.005,
        non_anchor_bonus=0.015,
        phasea_selected_bonus=0.003,
        source_rank_penalty_weight=0.002,
        anchor_penalty=0.01,
        word_ngram_weight=0.0,
        plausible_fragment_weight=0.0,
        longest_plausible_run_weight=0.0,
        dictionary_fragment_density_weight=0.0,
        garbage_penalty_weight=0.0,
    )


def build_weighted_score_plus_lexical_config() -> WeightedLateStageRerankerConfig:
    return WeightedLateStageRerankerConfig(
        final_score_weight=1.0,
        score_gain_weight=0.75,
        novelty_distance_weight=0.0,
        eligible_novel_bonus=0.0,
        non_anchor_bonus=0.0,
        phasea_selected_bonus=0.0,
        source_rank_penalty_weight=0.0,
        anchor_penalty=0.0,
        word_ngram_weight=0.02,
        plausible_fragment_weight=0.002,
        longest_plausible_run_weight=0.001,
        dictionary_fragment_density_weight=0.02,
        garbage_penalty_weight=0.02,
    )


def build_weighted_score_plus_novelty_plus_lexical_config(
) -> WeightedLateStageRerankerConfig:
    return WeightedLateStageRerankerConfig(
        final_score_weight=1.0,
        score_gain_weight=0.75,
        novelty_distance_weight=0.0001,
        eligible_novel_bonus=0.005,
        non_anchor_bonus=0.015,
        phasea_selected_bonus=0.003,
        source_rank_penalty_weight=0.002,
        anchor_penalty=0.01,
        word_ngram_weight=0.02,
        plausible_fragment_weight=0.002,
        longest_plausible_run_weight=0.001,
        dictionary_fragment_density_weight=0.02,
        garbage_penalty_weight=0.02,
    )


def build_weighted_score_plus_novelty_plus_score_gap_to_winner_config(
) -> WeightedLateStageRerankerConfig:
    return WeightedLateStageRerankerConfig(
        final_score_weight=1.0,
        score_gain_weight=0.75,
        score_gap_to_winner_weight=0.25,
        novelty_distance_weight=0.0001,
        eligible_novel_bonus=0.005,
        non_anchor_bonus=0.015,
        phasea_selected_bonus=0.003,
        source_rank_penalty_weight=0.002,
        anchor_penalty=0.01,
    )


def build_weighted_score_plus_novelty_plus_score_gap_to_anchor_config(
) -> WeightedLateStageRerankerConfig:
    return WeightedLateStageRerankerConfig(
        final_score_weight=1.0,
        score_gain_weight=0.75,
        score_gap_to_anchor_weight=0.25,
        novelty_distance_weight=0.0001,
        eligible_novel_bonus=0.005,
        non_anchor_bonus=0.015,
        phasea_selected_bonus=0.003,
        source_rank_penalty_weight=0.002,
        anchor_penalty=0.01,
    )


def build_weighted_score_plus_novelty_plus_init_score_config(
) -> WeightedLateStageRerankerConfig:
    return WeightedLateStageRerankerConfig(
        final_score_weight=1.0,
        score_gain_weight=0.75,
        init_score_weight=0.25,
        novelty_distance_weight=0.0001,
        eligible_novel_bonus=0.005,
        non_anchor_bonus=0.015,
        phasea_selected_bonus=0.003,
        source_rank_penalty_weight=0.002,
        anchor_penalty=0.01,
    )


def build_weighted_score_plus_novelty_plus_init_search_score_config(
) -> WeightedLateStageRerankerConfig:
    return WeightedLateStageRerankerConfig(
        final_score_weight=1.0,
        score_gain_weight=0.75,
        init_search_score_weight=0.001,
        novelty_distance_weight=0.0001,
        eligible_novel_bonus=0.005,
        non_anchor_bonus=0.015,
        phasea_selected_bonus=0.003,
        source_rank_penalty_weight=0.002,
        anchor_penalty=0.01,
    )


def build_weighted_score_plus_novelty_plus_phaseb_topk_penalty_config(
) -> WeightedLateStageRerankerConfig:
    return WeightedLateStageRerankerConfig(
        final_score_weight=1.0,
        score_gain_weight=0.75,
        novelty_distance_weight=0.0001,
        eligible_novel_bonus=0.005,
        non_anchor_bonus=0.015,
        phasea_selected_bonus=0.003,
        phaseb_topk_penalty_weight=0.03,
        source_rank_penalty_weight=0.002,
        anchor_penalty=0.01,
    )


def build_weighted_score_plus_novelty_plus_stage3_best_phaseb_penalty_config(
) -> WeightedLateStageRerankerConfig:
    return WeightedLateStageRerankerConfig(
        final_score_weight=1.0,
        score_gain_weight=0.75,
        novelty_distance_weight=0.0001,
        eligible_novel_bonus=0.005,
        non_anchor_bonus=0.015,
        phasea_selected_bonus=0.003,
        stage3_best_phaseb_penalty_weight=0.03,
        source_rank_penalty_weight=0.002,
        anchor_penalty=0.01,
    )


def build_weighted_score_plus_novelty_plus_source_penalties_config(
) -> WeightedLateStageRerankerConfig:
    return WeightedLateStageRerankerConfig(
        final_score_weight=1.0,
        score_gain_weight=0.75,
        novelty_distance_weight=0.0001,
        eligible_novel_bonus=0.005,
        non_anchor_bonus=0.015,
        phasea_selected_bonus=0.003,
        phaseb_topk_penalty_weight=0.03,
        stage3_best_phaseb_penalty_weight=0.02,
        source_rank_penalty_weight=0.002,
        anchor_penalty=0.01,
    )


def build_weighted_ablation_configs() -> Dict[str, WeightedLateStageRerankerConfig]:
    return dict(
        score_only=build_weighted_score_only_config(),
        score_plus_novelty=build_weighted_score_plus_novelty_config(),
        score_plus_lexical=build_weighted_score_plus_lexical_config(),
        score_plus_novelty_plus_lexical=(
            build_weighted_score_plus_novelty_plus_lexical_config()
        ),
    )


def build_weighted_numeric_ablation_configs() -> Dict[str, WeightedLateStageRerankerConfig]:
    return dict(
        score_plus_novelty=build_weighted_score_plus_novelty_config(),
        score_plus_novelty_plus_score_gap_to_winner=(
            build_weighted_score_plus_novelty_plus_score_gap_to_winner_config()
        ),
        score_plus_novelty_plus_score_gap_to_anchor=(
            build_weighted_score_plus_novelty_plus_score_gap_to_anchor_config()
        ),
        score_plus_novelty_plus_init_score=(
            build_weighted_score_plus_novelty_plus_init_score_config()
        ),
        score_plus_novelty_plus_init_search_score=(
            build_weighted_score_plus_novelty_plus_init_search_score_config()
        ),
    )


def build_weighted_categorical_ablation_configs() -> Dict[str, WeightedLateStageRerankerConfig]:
    return dict(
        score_plus_novelty=build_weighted_score_plus_novelty_config(),
        score_plus_novelty_plus_phaseb_topk_penalty=(
            build_weighted_score_plus_novelty_plus_phaseb_topk_penalty_config()
        ),
        score_plus_novelty_plus_stage3_best_phaseb_penalty=(
            build_weighted_score_plus_novelty_plus_stage3_best_phaseb_penalty_config()
        ),
        score_plus_novelty_plus_source_penalties=(
            build_weighted_score_plus_novelty_plus_source_penalties_config()
        ),
    )


def score_weighted_frontier_candidate(
    feature_row: Mapping[str, Any],
    *,
    config: WeightedLateStageRerankerConfig,
) -> float:
    row = dict(feature_row or {})
    score = 0.0
    score += config.final_score_weight * _finite_or_zero(row.get("final_score"))
    score += config.score_gain_weight * _finite_or_zero(row.get("score_gain"))
    score += config.init_score_weight * _finite_or_zero(row.get("init_score"))
    score += config.init_search_score_weight * _finite_or_zero(
        row.get("init_search_score")
    )
    score += config.score_gap_to_winner_weight * _finite_or_zero(
        row.get("score_gap_to_winner")
    )
    score += config.score_gap_to_anchor_weight * _finite_or_zero(
        row.get("score_gap_to_anchor")
    )
    score += config.novelty_distance_weight * float(
        max(_safe_int(row.get("novelty_distance_to_anchor", 0), 0), 0)
    )
    score += config.eligible_novel_bonus * float(
        _safe_int(row.get("eligible_novel_challenger", 0), 0)
    )
    score += config.non_anchor_bonus * float(_safe_int(row.get("is_non_anchor", 0), 0))
    score += config.phasea_selected_bonus * float(
        _safe_int(row.get("is_phasea_selected", 0), 0)
    )
    score -= config.phaseb_topk_penalty_weight * float(
        _safe_int(row.get("is_phaseb_topk_source", 0), 0)
    )
    score -= config.stage3_best_phaseb_penalty_weight * float(
        _safe_int(row.get("is_stage3_best_phaseb_source", 0), 0)
    )
    score -= config.source_rank_penalty_weight * float(
        max(_safe_int(row.get("source_rank", 1), 1) - 1, 0)
    )
    score -= config.anchor_penalty * float(_safe_int(row.get("is_anchor", 0), 0))
    score += config.word_ngram_weight * _finite_or_zero(row.get("word_ngram_score"))
    score += config.plausible_fragment_weight * float(
        max(_safe_int(row.get("plausible_fragment_count", 0), 0), 0)
    )
    score += config.longest_plausible_run_weight * float(
        max(_safe_int(row.get("longest_plausible_run", 0), 0), 0)
    )
    score += config.dictionary_fragment_density_weight * _finite_or_zero(
        row.get("dictionary_fragment_density")
    )
    score -= config.garbage_penalty_weight * _finite_or_zero(row.get("garbage_penalty"))
    return float(score)


def select_weighted_frontier_candidate(
    feature_rows: Sequence[Mapping[str, Any]],
    *,
    config: WeightedLateStageRerankerConfig | None = None,
) -> Dict[str, Any]:
    cfg = config or WeightedLateStageRerankerConfig()
    rows = [dict(row) for row in list(feature_rows or []) if isinstance(row, Mapping)]
    scored_rows = []
    for row in rows:
        row_out = dict(row)
        row_out["experimental_score"] = score_weighted_frontier_candidate(
            row_out,
            config=cfg,
        )
        scored_rows.append(row_out)
    return dict(
        max(
            scored_rows,
            key=lambda row: (
                _safe_float(row.get("experimental_score"), float("-inf")),
                _safe_float(row.get("final_score"), float("-inf")),
                _safe_float(row.get("final_match"), float("-inf")),
                -_safe_int(row.get("source_rank", 0), 0),
            ),
            default={},
        )
    )


def build_weighted_margin_explanation(
    challenger_row: Mapping[str, Any],
    incumbent_row: Mapping[str, Any],
    *,
    config: WeightedLateStageRerankerConfig,
) -> Dict[str, Any]:
    challenger = dict(challenger_row or {})
    incumbent = dict(incumbent_row or {})
    contributions = dict(
        final_score=(
            config.final_score_weight
            * (
                _finite_or_zero(challenger.get("final_score"))
                - _finite_or_zero(incumbent.get("final_score"))
            )
        ),
        score_gain=(
            config.score_gain_weight
            * (
                _finite_or_zero(challenger.get("score_gain"))
                - _finite_or_zero(incumbent.get("score_gain"))
            )
        ),
        init_score=(
            config.init_score_weight
            * (
                _finite_or_zero(challenger.get("init_score"))
                - _finite_or_zero(incumbent.get("init_score"))
            )
        ),
        init_search_score=(
            config.init_search_score_weight
            * (
                _finite_or_zero(challenger.get("init_search_score"))
                - _finite_or_zero(incumbent.get("init_search_score"))
            )
        ),
        score_gap_to_winner=(
            config.score_gap_to_winner_weight
            * (
                _finite_or_zero(challenger.get("score_gap_to_winner"))
                - _finite_or_zero(incumbent.get("score_gap_to_winner"))
            )
        ),
        score_gap_to_anchor=(
            config.score_gap_to_anchor_weight
            * (
                _finite_or_zero(challenger.get("score_gap_to_anchor"))
                - _finite_or_zero(incumbent.get("score_gap_to_anchor"))
            )
        ),
        novelty_distance_to_anchor=(
            config.novelty_distance_weight
            * float(
                max(_safe_int(challenger.get("novelty_distance_to_anchor", 0), 0), 0)
                - max(_safe_int(incumbent.get("novelty_distance_to_anchor", 0), 0), 0)
            )
        ),
        eligible_novel_challenger=(
            config.eligible_novel_bonus
            * float(
                _safe_int(challenger.get("eligible_novel_challenger", 0), 0)
                - _safe_int(incumbent.get("eligible_novel_challenger", 0), 0)
            )
        ),
        non_anchor=(
            config.non_anchor_bonus
            * float(
                _safe_int(challenger.get("is_non_anchor", 0), 0)
                - _safe_int(incumbent.get("is_non_anchor", 0), 0)
            )
        ),
        phasea_selected=(
            config.phasea_selected_bonus
            * float(
                _safe_int(challenger.get("is_phasea_selected", 0), 0)
                - _safe_int(incumbent.get("is_phasea_selected", 0), 0)
            )
        ),
        phaseb_topk_penalty=(
            -config.phaseb_topk_penalty_weight
            * float(
                _safe_int(challenger.get("is_phaseb_topk_source", 0), 0)
                - _safe_int(incumbent.get("is_phaseb_topk_source", 0), 0)
            )
        ),
        stage3_best_phaseb_penalty=(
            -config.stage3_best_phaseb_penalty_weight
            * float(
                _safe_int(challenger.get("is_stage3_best_phaseb_source", 0), 0)
                - _safe_int(incumbent.get("is_stage3_best_phaseb_source", 0), 0)
            )
        ),
        source_rank_penalty=(
            -config.source_rank_penalty_weight
            * float(
                max(_safe_int(challenger.get("source_rank", 1), 1) - 1, 0)
                - max(_safe_int(incumbent.get("source_rank", 1), 1) - 1, 0)
            )
        ),
        anchor_penalty=(
            -config.anchor_penalty
            * float(
                _safe_int(challenger.get("is_anchor", 0), 0)
                - _safe_int(incumbent.get("is_anchor", 0), 0)
            )
        ),
        word_ngram_score=(
            config.word_ngram_weight
            * (
                _finite_or_zero(challenger.get("word_ngram_score"))
                - _finite_or_zero(incumbent.get("word_ngram_score"))
            )
        ),
        plausible_fragment_count=(
            config.plausible_fragment_weight
            * float(
                max(_safe_int(challenger.get("plausible_fragment_count", 0), 0), 0)
                - max(_safe_int(incumbent.get("plausible_fragment_count", 0), 0), 0)
            )
        ),
        longest_plausible_run=(
            config.longest_plausible_run_weight
            * float(
                max(_safe_int(challenger.get("longest_plausible_run", 0), 0), 0)
                - max(_safe_int(incumbent.get("longest_plausible_run", 0), 0), 0)
            )
        ),
        dictionary_fragment_density=(
            config.dictionary_fragment_density_weight
            * (
                _finite_or_zero(challenger.get("dictionary_fragment_density"))
                - _finite_or_zero(incumbent.get("dictionary_fragment_density"))
            )
        ),
        garbage_penalty=(
            -config.garbage_penalty_weight
            * (
                _finite_or_zero(challenger.get("garbage_penalty"))
                - _finite_or_zero(incumbent.get("garbage_penalty"))
            )
        ),
    )
    group_totals = dict(
        score_features=float(
            contributions["final_score"]
            + contributions["score_gain"]
            + contributions["init_score"]
            + contributions["init_search_score"]
            + contributions["score_gap_to_winner"]
            + contributions["score_gap_to_anchor"]
        ),
        structural_features=float(
            contributions["novelty_distance_to_anchor"]
            + contributions["eligible_novel_challenger"]
            + contributions["non_anchor"]
            + contributions["phasea_selected"]
            + contributions["phaseb_topk_penalty"]
            + contributions["stage3_best_phaseb_penalty"]
            + contributions["source_rank_penalty"]
            + contributions["anchor_penalty"]
        ),
        lexical_features=float(
            contributions["word_ngram_score"]
            + contributions["plausible_fragment_count"]
            + contributions["longest_plausible_run"]
            + contributions["dictionary_fragment_density"]
            + contributions["garbage_penalty"]
        ),
    )
    dominant_group = max(group_totals, key=lambda k: group_totals[k]) if group_totals else ""
    return dict(
        challenger_candidate_hash=str(challenger.get("candidate_hash", "") or ""),
        incumbent_candidate_hash=str(incumbent.get("candidate_hash", "") or ""),
        total_margin=float(sum(float(v) for v in contributions.values())),
        group_totals=group_totals,
        dominant_positive_group=str(dominant_group),
        feature_contributions={k: float(v) for k, v in contributions.items()},
    )


def score_pairwise_challenger_margin(
    challenger_row: Mapping[str, Any],
    incumbent_row: Mapping[str, Any],
    *,
    config: PairwiseLateStageRerankerConfig,
) -> float:
    challenger = dict(challenger_row or {})
    incumbent = dict(incumbent_row or {})
    margin = 0.0
    margin += config.final_score_diff_weight * (
        _finite_or_zero(challenger.get("final_score"))
        - _finite_or_zero(incumbent.get("final_score"))
    )
    margin += config.score_gain_diff_weight * (
        _finite_or_zero(challenger.get("score_gain"))
        - _finite_or_zero(incumbent.get("score_gain"))
    )
    margin += config.novelty_distance_diff_weight * float(
        max(_safe_int(challenger.get("novelty_distance_to_anchor", 0), 0), 0)
        - max(_safe_int(incumbent.get("novelty_distance_to_anchor", 0), 0), 0)
    )
    margin += config.eligible_novel_diff_weight * float(
        _safe_int(challenger.get("eligible_novel_challenger", 0), 0)
        - _safe_int(incumbent.get("eligible_novel_challenger", 0), 0)
    )
    margin += config.non_anchor_diff_weight * float(
        _safe_int(challenger.get("is_non_anchor", 0), 0)
        - _safe_int(incumbent.get("is_non_anchor", 0), 0)
    )
    margin += config.phasea_selected_diff_weight * float(
        _safe_int(challenger.get("is_phasea_selected", 0), 0)
        - _safe_int(incumbent.get("is_phasea_selected", 0), 0)
    )
    margin -= config.source_rank_penalty_diff_weight * float(
        max(_safe_int(challenger.get("source_rank", 1), 1) - 1, 0)
        - max(_safe_int(incumbent.get("source_rank", 1), 1) - 1, 0)
    )
    margin -= config.anchor_penalty_diff_weight * float(
        _safe_int(challenger.get("is_anchor", 0), 0)
        - _safe_int(incumbent.get("is_anchor", 0), 0)
    )
    margin += config.word_ngram_diff_weight * (
        _finite_or_zero(challenger.get("word_ngram_score"))
        - _finite_or_zero(incumbent.get("word_ngram_score"))
    )
    margin += config.plausible_fragment_diff_weight * float(
        max(_safe_int(challenger.get("plausible_fragment_count", 0), 0), 0)
        - max(_safe_int(incumbent.get("plausible_fragment_count", 0), 0), 0)
    )
    margin += config.longest_plausible_run_diff_weight * float(
        max(_safe_int(challenger.get("longest_plausible_run", 0), 0), 0)
        - max(_safe_int(incumbent.get("longest_plausible_run", 0), 0), 0)
    )
    margin += config.dictionary_fragment_density_diff_weight * (
        _finite_or_zero(challenger.get("dictionary_fragment_density"))
        - _finite_or_zero(incumbent.get("dictionary_fragment_density"))
    )
    margin -= config.garbage_penalty_diff_weight * (
        _finite_or_zero(challenger.get("garbage_penalty"))
        - _finite_or_zero(incumbent.get("garbage_penalty"))
    )
    return float(margin)


def select_pairwise_frontier_candidate(
    feature_rows: Sequence[Mapping[str, Any]],
    *,
    winner_hash: str = "",
    config: PairwiseLateStageRerankerConfig | None = None,
) -> Dict[str, Any]:
    cfg = config or PairwiseLateStageRerankerConfig()
    rows = [dict(row) for row in list(feature_rows or []) if isinstance(row, Mapping)]
    incumbent = select_legacy_frontier_winner(rows, winner_hash=winner_hash)
    if not incumbent:
        return {}
    best_margin = float("-inf")
    best_row = dict(incumbent)
    for row in rows:
        if str(row.get("candidate_hash", "") or "") == str(
            incumbent.get("candidate_hash", "") or ""
        ):
            continue
        margin = score_pairwise_challenger_margin(row, incumbent, config=cfg)
        row_out = dict(row)
        row_out["pairwise_margin_vs_legacy"] = float(margin)
        if margin > best_margin:
            best_margin = float(margin)
            best_row = row_out
    if best_margin <= 0.0:
        incumbent_out = dict(incumbent)
        incumbent_out["pairwise_margin_vs_legacy"] = 0.0
        return incumbent_out
    return dict(best_row)


def build_pairwise_margin_explanation(
    challenger_row: Mapping[str, Any],
    incumbent_row: Mapping[str, Any],
    *,
    config: PairwiseLateStageRerankerConfig,
) -> Dict[str, Any]:
    challenger = dict(challenger_row or {})
    incumbent = dict(incumbent_row or {})
    contributions = dict(
        final_score_diff=(
            config.final_score_diff_weight
            * (
                _finite_or_zero(challenger.get("final_score"))
                - _finite_or_zero(incumbent.get("final_score"))
            )
        ),
        score_gain_diff=(
            config.score_gain_diff_weight
            * (
                _finite_or_zero(challenger.get("score_gain"))
                - _finite_or_zero(incumbent.get("score_gain"))
            )
        ),
        novelty_distance_diff=(
            config.novelty_distance_diff_weight
            * float(
                max(_safe_int(challenger.get("novelty_distance_to_anchor", 0), 0), 0)
                - max(_safe_int(incumbent.get("novelty_distance_to_anchor", 0), 0), 0)
            )
        ),
        eligible_novel_diff=(
            config.eligible_novel_diff_weight
            * float(
                _safe_int(challenger.get("eligible_novel_challenger", 0), 0)
                - _safe_int(incumbent.get("eligible_novel_challenger", 0), 0)
            )
        ),
        non_anchor_diff=(
            config.non_anchor_diff_weight
            * float(
                _safe_int(challenger.get("is_non_anchor", 0), 0)
                - _safe_int(incumbent.get("is_non_anchor", 0), 0)
            )
        ),
        phasea_selected_diff=(
            config.phasea_selected_diff_weight
            * float(
                _safe_int(challenger.get("is_phasea_selected", 0), 0)
                - _safe_int(incumbent.get("is_phasea_selected", 0), 0)
            )
        ),
        source_rank_penalty_diff=(
            -config.source_rank_penalty_diff_weight
            * float(
                max(_safe_int(challenger.get("source_rank", 1), 1) - 1, 0)
                - max(_safe_int(incumbent.get("source_rank", 1), 1) - 1, 0)
            )
        ),
        anchor_penalty_diff=(
            -config.anchor_penalty_diff_weight
            * float(
                _safe_int(challenger.get("is_anchor", 0), 0)
                - _safe_int(incumbent.get("is_anchor", 0), 0)
            )
        ),
        word_ngram_diff=(
            config.word_ngram_diff_weight
            * (
                _finite_or_zero(challenger.get("word_ngram_score"))
                - _finite_or_zero(incumbent.get("word_ngram_score"))
            )
        ),
        plausible_fragment_diff=(
            config.plausible_fragment_diff_weight
            * float(
                max(_safe_int(challenger.get("plausible_fragment_count", 0), 0), 0)
                - max(_safe_int(incumbent.get("plausible_fragment_count", 0), 0), 0)
            )
        ),
        longest_plausible_run_diff=(
            config.longest_plausible_run_diff_weight
            * float(
                max(_safe_int(challenger.get("longest_plausible_run", 0), 0), 0)
                - max(_safe_int(incumbent.get("longest_plausible_run", 0), 0), 0)
            )
        ),
        dictionary_fragment_density_diff=(
            config.dictionary_fragment_density_diff_weight
            * (
                _finite_or_zero(challenger.get("dictionary_fragment_density"))
                - _finite_or_zero(incumbent.get("dictionary_fragment_density"))
            )
        ),
        garbage_penalty_diff=(
            -config.garbage_penalty_diff_weight
            * (
                _finite_or_zero(challenger.get("garbage_penalty"))
                - _finite_or_zero(incumbent.get("garbage_penalty"))
            )
        ),
    )
    group_totals = dict(
        score_features=float(
            contributions["final_score_diff"] + contributions["score_gain_diff"]
        ),
        structural_features=float(
            contributions["novelty_distance_diff"]
            + contributions["eligible_novel_diff"]
            + contributions["non_anchor_diff"]
            + contributions["phasea_selected_diff"]
            + contributions["source_rank_penalty_diff"]
            + contributions["anchor_penalty_diff"]
        ),
        lexical_features=float(
            contributions["word_ngram_diff"]
            + contributions["plausible_fragment_diff"]
            + contributions["longest_plausible_run_diff"]
            + contributions["dictionary_fragment_density_diff"]
            + contributions["garbage_penalty_diff"]
        ),
    )
    dominant_group = max(group_totals, key=lambda k: group_totals[k]) if group_totals else ""
    return dict(
        challenger_candidate_hash=str(challenger.get("candidate_hash", "") or ""),
        incumbent_candidate_hash=str(incumbent.get("candidate_hash", "") or ""),
        total_margin=float(sum(float(v) for v in contributions.values())),
        group_totals=group_totals,
        dominant_positive_group=str(dominant_group),
        feature_contributions={k: float(v) for k, v in contributions.items()},
    )


def build_stagea_data_realism_summary(
    dataset_summary: Mapping[str, Any],
) -> Dict[str, Any]:
    summary = dict(dataset_summary or {})
    patterns = [
        dict(row)
        for row in list(summary.get("distinct_patterns", []) or [])
        if isinstance(row, Mapping)
    ]
    dominant = dict(patterns[0]) if patterns else {}
    row_count = int(_safe_int(summary.get("row_count", 0), 0))
    dominant_count = int(_safe_int(dominant.get("count", 0), 0))
    dominant_fraction = float(dominant_count) / float(row_count) if row_count else 0.0
    broader_lift_status = (
        "thin"
        if row_count <= 20 or dominant_fraction >= 0.5 or int(len(patterns)) <= 5
        else "credible"
    )
    return dict(
        row_count=row_count,
        distinct_pattern_count=int(_safe_int(summary.get("distinct_pattern_count", 0), 0)),
        dominant_pattern_count=dominant_count,
        dominant_pattern_fraction=dominant_fraction,
        dominant_pattern=dict(dominant),
        broader_lift_status=str(broader_lift_status),
    )


def build_stagea_feature_story(
    fixture: Mapping[str, Any],
    *,
    weighted_config: WeightedLateStageRerankerConfig | None = None,
    pairwise_config: PairwiseLateStageRerankerConfig | None = None,
) -> Dict[str, Any]:
    feature_rows = build_late_stage_candidate_feature_table(fixture)
    legacy = select_legacy_frontier_winner(
        feature_rows,
        winner_hash=str(fixture.get("score_selected_winner_hash", "") or ""),
    )
    weighted_cfg = weighted_config or WeightedLateStageRerankerConfig()
    weighted_score_only_cfg = build_weighted_score_only_config()
    weighted_score_only = select_weighted_frontier_candidate(
        feature_rows,
        config=weighted_score_only_cfg,
    )
    weighted_full = select_weighted_frontier_candidate(feature_rows, config=weighted_cfg)
    pairwise_cfg = pairwise_config or PairwiseLateStageRerankerConfig()
    pairwise = select_pairwise_frontier_candidate(
        feature_rows,
        winner_hash=str(fixture.get("score_selected_winner_hash", "") or ""),
        config=pairwise_cfg,
    )
    return dict(
        model_ladder=dict(
            legacy_candidate_hash=str(legacy.get("candidate_hash", "") or ""),
            weighted_score_only_candidate_hash=str(
                weighted_score_only.get("candidate_hash", "") or ""
            ),
            weighted_full_candidate_hash=str(
                weighted_full.get("candidate_hash", "") or ""
            ),
            pairwise_candidate_hash=str(pairwise.get("candidate_hash", "") or ""),
        ),
        weighted_margin_explanation=build_weighted_margin_explanation(
            weighted_full,
            legacy,
            config=weighted_cfg,
        ),
        pairwise_margin_explanation=build_pairwise_margin_explanation(
            pairwise,
            legacy,
            config=pairwise_cfg,
        ),
    )


def build_disagreement_frontier_row_audit(
    truth_gap_rows: Sequence[Mapping[str, Any]] | None,
    *,
    weighted_config: WeightedLateStageRerankerConfig | None = None,
    pairwise_config: PairwiseLateStageRerankerConfig | None = None,
) -> list[Dict[str, Any]]:
    from tools.benchmarks.periodic_sub_trans.no_wli.late_stage_frontier_fixture import (
        build_late_stage_frontier_fixture,
    )

    out: list[Dict[str, Any]] = []
    for row_obj in list(truth_gap_rows or []):
        if not isinstance(row_obj, Mapping):
            continue
        row = dict(row_obj)
        artifact_path = Path(str(row.get("artifact_path", "") or ""))
        if not artifact_path.exists():
            continue
        artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
        fixture = build_late_stage_frontier_fixture(
            artifact_path=artifact_path,
            artifact=artifact,
            fixture_id=str(artifact_path.stem),
        )
        feature_story = build_stagea_feature_story(
            fixture,
            weighted_config=weighted_config,
            pairwise_config=pairwise_config,
        )
        selector_eval = build_frontier_selector_evaluation(
            fixture,
            config=weighted_config,
        )
        out.append(
            dict(
                artifact_path=str(artifact_path).replace("\\", "/"),
                pattern_key="|".join(str(x) for x in _truth_gap_pattern_key(row)),
                winner_candidate_hash=str(row.get("winner_candidate_hash", "") or ""),
                challenger_candidate_hash=str(
                    row.get("challenger_candidate_hash", "") or ""
                ),
                phaseC_start_policy=str(row.get("phaseC_start_policy", "") or ""),
                phaseB_top_n_used=int(_safe_int(row.get("phaseB_top_n_used", 0), 0)),
                truth_gap_vs_winner=_safe_float(row.get("truth_gap_vs_winner")),
                score_gap_vs_winner=_safe_float(row.get("score_gap_vs_winner")),
                weighted_candidate_hash=str(
                    feature_story["model_ladder"]["weighted_full_candidate_hash"]
                ),
                weighted_score_only_candidate_hash=str(
                    feature_story["model_ladder"]["weighted_score_only_candidate_hash"]
                ),
                pairwise_candidate_hash=str(
                    feature_story["model_ladder"]["pairwise_candidate_hash"]
                ),
                weighted_dominant_group=str(
                    feature_story["weighted_margin_explanation"][
                        "dominant_positive_group"
                    ]
                ),
                pairwise_dominant_group=str(
                    feature_story["pairwise_margin_explanation"][
                        "dominant_positive_group"
                    ]
                ),
                weighted_rescued_from_legacy=int(
                    selector_eval.get("rescued_from_legacy", 0) or 0
                ),
                pairwise_rescued_from_legacy=int(
                    selector_eval.get("pairwise_rescued_from_legacy", 0) or 0
                ),
            )
        )
    return out


def build_disagreement_frontier_pattern_audit(
    truth_gap_rows: Sequence[Mapping[str, Any]] | None,
    *,
    weighted_config: WeightedLateStageRerankerConfig | None = None,
    pairwise_config: PairwiseLateStageRerankerConfig | None = None,
) -> list[Dict[str, Any]]:
    row_audit = build_disagreement_frontier_row_audit(
        truth_gap_rows,
        weighted_config=weighted_config,
        pairwise_config=pairwise_config,
    )
    pattern_map: Dict[str, Dict[str, Any]] = {}
    for row in row_audit:
        pattern_key = str(row.get("pattern_key", "") or "")
        if pattern_key not in pattern_map:
            pattern_map[pattern_key] = dict(
                pattern_key=pattern_key,
                count=0,
                winner_candidate_hash=str(row.get("winner_candidate_hash", "") or ""),
                challenger_candidate_hash=str(
                    row.get("challenger_candidate_hash", "") or ""
                ),
                phaseC_start_policy=str(row.get("phaseC_start_policy", "") or ""),
                phaseB_top_n_used=int(_safe_int(row.get("phaseB_top_n_used", 0), 0)),
                truth_gap_vs_winner=_safe_float(row.get("truth_gap_vs_winner")),
                score_gap_vs_winner=_safe_float(row.get("score_gap_vs_winner")),
                weighted_rescued_count=0,
                pairwise_rescued_count=0,
                weighted_dominant_group_counts={},
                pairwise_dominant_group_counts={},
            )
        target = pattern_map[pattern_key]
        target["count"] = int(target["count"]) + 1
        target["weighted_rescued_count"] = int(target["weighted_rescued_count"]) + int(
            _safe_int(row.get("weighted_rescued_from_legacy", 0), 0)
        )
        target["pairwise_rescued_count"] = int(target["pairwise_rescued_count"]) + int(
            _safe_int(row.get("pairwise_rescued_from_legacy", 0), 0)
        )
        weighted_group = str(row.get("weighted_dominant_group", "") or "")
        pairwise_group = str(row.get("pairwise_dominant_group", "") or "")
        weighted_counts = dict(target["weighted_dominant_group_counts"])
        pairwise_counts = dict(target["pairwise_dominant_group_counts"])
        weighted_counts[weighted_group] = weighted_counts.get(weighted_group, 0) + 1
        pairwise_counts[pairwise_group] = pairwise_counts.get(pairwise_group, 0) + 1
        target["weighted_dominant_group_counts"] = weighted_counts
        target["pairwise_dominant_group_counts"] = pairwise_counts
    return sorted(
        (dict(row) for row in pattern_map.values()),
        key=lambda row: (-_safe_int(row.get("count", 0), 0), -_safe_float(row.get("truth_gap_vs_winner"), float("-inf"))),
    )


def build_frontier_challenger_vs_winner_case_summary(
    *,
    artifact_path: Path,
    winner_candidate_hash: str,
    challenger_candidate_hash: str,
    weighted_config: WeightedLateStageRerankerConfig | None = None,
    pairwise_config: PairwiseLateStageRerankerConfig | None = None,
) -> Dict[str, Any]:
    from tools.benchmarks.periodic_sub_trans.no_wli.late_stage_frontier_fixture import (
        build_late_stage_frontier_fixture,
    )

    artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
    fixture = build_late_stage_frontier_fixture(
        artifact_path=artifact_path,
        artifact=artifact,
        fixture_id=str(artifact_path.stem),
    )
    feature_rows = build_late_stage_candidate_feature_table(fixture)
    winner_row = next(
        (
            dict(row)
            for row in feature_rows
            if str(row.get("candidate_hash", "") or "") == str(winner_candidate_hash)
        ),
        {},
    )
    challenger_row = next(
        (
            dict(row)
            for row in feature_rows
            if str(row.get("candidate_hash", "") or "") == str(challenger_candidate_hash)
        ),
        {},
    )
    weighted_margin = build_weighted_margin_explanation(
        challenger_row,
        winner_row,
        config=weighted_config or WeightedLateStageRerankerConfig(),
    )
    pairwise_margin = build_pairwise_margin_explanation(
        challenger_row,
        winner_row,
        config=pairwise_config or PairwiseLateStageRerankerConfig(),
    )
    return dict(
        artifact_path=str(artifact_path).replace("\\", "/"),
        winner_candidate_hash=str(winner_candidate_hash or ""),
        challenger_candidate_hash=str(challenger_candidate_hash or ""),
        winner_source=str(winner_row.get("source", "") or ""),
        challenger_source=str(challenger_row.get("source", "") or ""),
        winner_source_rank=_safe_int(winner_row.get("source_rank", 0), 0),
        challenger_source_rank=_safe_int(challenger_row.get("source_rank", 0), 0),
        winner_final_score=winner_row.get("final_score"),
        challenger_final_score=challenger_row.get("final_score"),
        winner_final_match=winner_row.get("final_match"),
        challenger_final_match=challenger_row.get("final_match"),
        challenger_eligible_novel=_safe_int(
            challenger_row.get("eligible_novel_challenger", 0),
            0,
        ),
        challenger_novelty_distance_to_anchor=challenger_row.get(
            "novelty_distance_to_anchor"
        ),
        weighted_margin_total=weighted_margin.get("total_margin"),
        weighted_group_totals=dict(weighted_margin.get("group_totals", {})),
        pairwise_margin_total=pairwise_margin.get("total_margin"),
        pairwise_group_totals=dict(pairwise_margin.get("group_totals", {})),
    )


def build_case_live_feature_audit(
    *,
    artifact_path: Path,
    winner_candidate_hash: str,
    challenger_candidate_hash: str,
) -> Dict[str, Any]:
    from tools.benchmarks.periodic_sub_trans.no_wli.late_stage_frontier_fixture import (
        build_late_stage_frontier_fixture,
    )

    artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
    fixture = build_late_stage_frontier_fixture(
        artifact_path=artifact_path,
        artifact=artifact,
        fixture_id=str(artifact_path.stem),
    )
    feature_rows = build_late_stage_candidate_feature_table(fixture)
    winner_row = next(
        (
            dict(row)
            for row in feature_rows
            if str(row.get("candidate_hash", "") or "") == str(winner_candidate_hash)
        ),
        {},
    )
    challenger_row = next(
        (
            dict(row)
            for row in feature_rows
            if str(row.get("candidate_hash", "") or "") == str(challenger_candidate_hash)
        ),
        {},
    )
    present_and_used: list[Dict[str, Any]] = []
    present_but_unused: list[Dict[str, Any]] = []
    absent_today: list[Dict[str, Any]] = []
    for field_name, group_name, used_by_current_model in LIVE_FEATURE_AUDIT_FIELDS:
        challenger_value = challenger_row.get(field_name)
        winner_value = winner_row.get(field_name)
        row = dict(
            field=field_name,
            group=group_name,
            used_by_current_model=int(1 if used_by_current_model else 0),
            challenger_value=challenger_value,
            winner_value=winner_value,
            differs_from_winner=int(
                1 if str(challenger_value) != str(winner_value) else 0
            ),
        )
        if _value_present(challenger_value):
            if used_by_current_model:
                present_and_used.append(row)
            else:
                present_but_unused.append(row)
        else:
            absent_today.append(row)
    return dict(
        artifact_path=str(artifact_path).replace("\\", "/"),
        winner_candidate_hash=str(winner_candidate_hash or ""),
        challenger_candidate_hash=str(challenger_candidate_hash or ""),
        present_and_used=present_and_used,
        present_but_unused=present_but_unused,
        absent_today=absent_today,
    )


def build_stagea_rescued_vs_unrecovered_contrast(
    truth_gap_rows: Sequence[Mapping[str, Any]] | None,
    *,
    weighted_config: WeightedLateStageRerankerConfig | None = None,
    pairwise_config: PairwiseLateStageRerankerConfig | None = None,
) -> Dict[str, Any]:
    row_audit = build_disagreement_frontier_row_audit(
        truth_gap_rows,
        weighted_config=weighted_config,
        pairwise_config=pairwise_config,
    )
    rescued_row = next(
        (
            dict(row)
            for row in row_audit
            if _safe_int(row.get("weighted_rescued_from_legacy", 0), 0) == 1
        ),
        {},
    )
    unrecovered_row = next(
        (
            dict(row)
            for row in row_audit
            if _safe_int(row.get("weighted_rescued_from_legacy", 0), 0) == 0
        ),
        {},
    )

    rescued_case = (
        build_frontier_challenger_vs_winner_case_summary(
            artifact_path=Path(str(rescued_row.get("artifact_path", "") or "")),
            winner_candidate_hash=str(rescued_row.get("winner_candidate_hash", "") or ""),
            challenger_candidate_hash=str(
                rescued_row.get("challenger_candidate_hash", "") or ""
            ),
            weighted_config=weighted_config,
            pairwise_config=pairwise_config,
        )
        if rescued_row
        else {}
    )
    unrecovered_case = (
        build_frontier_challenger_vs_winner_case_summary(
            artifact_path=Path(str(unrecovered_row.get("artifact_path", "") or "")),
            winner_candidate_hash=str(
                unrecovered_row.get("winner_candidate_hash", "") or ""
            ),
            challenger_candidate_hash=str(
                unrecovered_row.get("challenger_candidate_hash", "") or ""
            ),
            weighted_config=weighted_config,
            pairwise_config=pairwise_config,
        )
        if unrecovered_row
        else {}
    )
    return dict(
        rescued_case=rescued_case,
        unrecovered_case=unrecovered_case,
    )


def build_stagea_unrecovered_case_feature_audit(
    truth_gap_rows: Sequence[Mapping[str, Any]] | None,
) -> Dict[str, Any]:
    row_audit = build_disagreement_frontier_row_audit(truth_gap_rows)
    rescued_row = next(
        (
            dict(row)
            for row in row_audit
            if _safe_int(row.get("weighted_rescued_from_legacy", 0), 0) == 1
        ),
        {},
    )
    unrecovered_row = next(
        (
            dict(row)
            for row in row_audit
            if _safe_int(row.get("weighted_rescued_from_legacy", 0), 0) == 0
        ),
        {},
    )
    return dict(
        rescued_case=(
            build_case_live_feature_audit(
                artifact_path=Path(str(rescued_row.get("artifact_path", "") or "")),
                winner_candidate_hash=str(
                    rescued_row.get("winner_candidate_hash", "") or ""
                ),
                challenger_candidate_hash=str(
                    rescued_row.get("challenger_candidate_hash", "") or ""
                ),
            )
            if rescued_row
            else {}
        ),
        unrecovered_case=(
            build_case_live_feature_audit(
                artifact_path=Path(str(unrecovered_row.get("artifact_path", "") or "")),
                winner_candidate_hash=str(
                    unrecovered_row.get("winner_candidate_hash", "") or ""
                ),
                challenger_candidate_hash=str(
                    unrecovered_row.get("challenger_candidate_hash", "") or ""
                ),
            )
            if unrecovered_row
            else {}
        ),
    )


def build_stagea_weighted_ablation_sweep(
    truth_gap_rows: Sequence[Mapping[str, Any]] | None,
) -> Dict[str, Any]:
    from tools.benchmarks.periodic_sub_trans.no_wli.late_stage_frontier_fixture import (
        build_late_stage_frontier_fixture,
    )

    configs = build_weighted_ablation_configs()
    row_audit: list[Dict[str, Any]] = []
    for row_obj in list(truth_gap_rows or []):
        if not isinstance(row_obj, Mapping):
            continue
        row = dict(row_obj)
        artifact_path = Path(str(row.get("artifact_path", "") or ""))
        if not artifact_path.exists():
            continue
        artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
        fixture = build_late_stage_frontier_fixture(
            artifact_path=artifact_path,
            artifact=artifact,
            fixture_id=str(artifact_path.stem),
        )
        feature_rows = build_late_stage_candidate_feature_table(fixture)
        legacy = select_legacy_frontier_winner(
            feature_rows,
            winner_hash=str(fixture.get("score_selected_winner_hash", "") or ""),
        )
        pattern_key = "|".join(str(x) for x in _truth_gap_pattern_key(row))
        row_entry = dict(
            artifact_path=str(artifact_path).replace("\\", "/"),
            pattern_key=pattern_key,
            winner_candidate_hash=str(row.get("winner_candidate_hash", "") or ""),
            challenger_candidate_hash=str(
                row.get("challenger_candidate_hash", "") or ""
            ),
            truth_gap_vs_winner=_safe_float(row.get("truth_gap_vs_winner")),
            score_gap_vs_winner=_safe_float(row.get("score_gap_vs_winner")),
            models={},
        )
        for name, cfg in configs.items():
            selected = select_weighted_frontier_candidate(feature_rows, config=cfg)
            row_entry["models"][name] = dict(
                candidate_hash=str(selected.get("candidate_hash", "") or ""),
                truth_match=selected.get("final_match"),
                rescued_from_legacy=int(
                    1
                    if str(selected.get("candidate_hash", "") or "")
                    != str(legacy.get("candidate_hash", "") or "")
                    and _safe_float(selected.get("final_match"), float("-inf"))
                    > _safe_float(legacy.get("final_match"), float("-inf"))
                    else 0
                ),
            )
        row_audit.append(row_entry)

    model_summary: Dict[str, Dict[str, Any]] = {}
    for name in configs:
        rescued_rows = [
            row for row in row_audit if int(row["models"][name]["rescued_from_legacy"]) == 1
        ]
        rescued_patterns = {
            str(row.get("pattern_key", "") or "") for row in rescued_rows
        }
        model_summary[name] = dict(
            rescued_row_count=int(len(rescued_rows)),
            rescued_pattern_count=int(len(rescued_patterns)),
            selected_candidate_hashes=sorted(
                {
                    str(row["models"][name]["candidate_hash"])
                    for row in row_audit
                    if str(row["models"][name]["candidate_hash"])
                }
            ),
        )
    return dict(
        models=model_summary,
        row_audit=row_audit,
    )


def build_stagea_numeric_field_ablation_sweep(
    truth_gap_rows: Sequence[Mapping[str, Any]] | None,
) -> Dict[str, Any]:
    from tools.benchmarks.periodic_sub_trans.no_wli.late_stage_frontier_fixture import (
        build_late_stage_frontier_fixture,
    )

    configs = build_weighted_numeric_ablation_configs()
    row_audit: list[Dict[str, Any]] = []
    for row_obj in list(truth_gap_rows or []):
        if not isinstance(row_obj, Mapping):
            continue
        row = dict(row_obj)
        artifact_path = Path(str(row.get("artifact_path", "") or ""))
        if not artifact_path.exists():
            continue
        artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
        fixture = build_late_stage_frontier_fixture(
            artifact_path=artifact_path,
            artifact=artifact,
            fixture_id=str(artifact_path.stem),
        )
        feature_rows = build_late_stage_candidate_feature_table(fixture)
        legacy = select_legacy_frontier_winner(
            feature_rows,
            winner_hash=str(fixture.get("score_selected_winner_hash", "") or ""),
        )
        pattern_key = "|".join(str(x) for x in _truth_gap_pattern_key(row))
        row_entry = dict(
            artifact_path=str(artifact_path).replace("\\", "/"),
            pattern_key=pattern_key,
            winner_candidate_hash=str(row.get("winner_candidate_hash", "") or ""),
            challenger_candidate_hash=str(
                row.get("challenger_candidate_hash", "") or ""
            ),
            truth_gap_vs_winner=_safe_float(row.get("truth_gap_vs_winner")),
            score_gap_vs_winner=_safe_float(row.get("score_gap_vs_winner")),
            models={},
        )
        for name, cfg in configs.items():
            selected = select_weighted_frontier_candidate(feature_rows, config=cfg)
            row_entry["models"][name] = dict(
                candidate_hash=str(selected.get("candidate_hash", "") or ""),
                truth_match=selected.get("final_match"),
                rescued_from_legacy=int(
                    1
                    if str(selected.get("candidate_hash", "") or "")
                    != str(legacy.get("candidate_hash", "") or "")
                    and _safe_float(selected.get("final_match"), float("-inf"))
                    > _safe_float(legacy.get("final_match"), float("-inf"))
                    else 0
                ),
            )
        row_audit.append(row_entry)

    model_summary: Dict[str, Dict[str, Any]] = {}
    for name in configs:
        rescued_rows = [
            row
            for row in row_audit
            if int(row["models"][name]["rescued_from_legacy"]) == 1
        ]
        rescued_patterns = {
            str(row.get("pattern_key", "") or "") for row in rescued_rows
        }
        model_summary[name] = dict(
            rescued_row_count=int(len(rescued_rows)),
            rescued_pattern_count=int(len(rescued_patterns)),
            rescued_unrecovered_class=int(
                1
                if any(
                    str(row.get("challenger_candidate_hash", "") or "")
                    == "e45c25ba171877fd"
                    and int(row["models"][name]["rescued_from_legacy"]) == 1
                    for row in row_audit
                )
                else 0
            ),
            selected_candidate_hashes=sorted(
                {
                    str(row["models"][name]["candidate_hash"])
                    for row in row_audit
                    if str(row["models"][name]["candidate_hash"])
                }
            ),
        )
    return dict(
        models=model_summary,
        row_audit=row_audit,
    )


def build_stagea_categorical_field_ablation_sweep(
    truth_gap_rows: Sequence[Mapping[str, Any]] | None,
) -> Dict[str, Any]:
    from tools.benchmarks.periodic_sub_trans.no_wli.late_stage_frontier_fixture import (
        build_late_stage_frontier_fixture,
    )

    configs = build_weighted_categorical_ablation_configs()
    row_audit: list[Dict[str, Any]] = []
    for row_obj in list(truth_gap_rows or []):
        if not isinstance(row_obj, Mapping):
            continue
        row = dict(row_obj)
        artifact_path = Path(str(row.get("artifact_path", "") or ""))
        if not artifact_path.exists():
            continue
        artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
        fixture = build_late_stage_frontier_fixture(
            artifact_path=artifact_path,
            artifact=artifact,
            fixture_id=str(artifact_path.stem),
        )
        feature_rows = build_late_stage_candidate_feature_table(fixture)
        legacy = select_legacy_frontier_winner(
            feature_rows,
            winner_hash=str(fixture.get("score_selected_winner_hash", "") or ""),
        )
        pattern_key = "|".join(str(x) for x in _truth_gap_pattern_key(row))
        row_entry = dict(
            artifact_path=str(artifact_path).replace("\\", "/"),
            pattern_key=pattern_key,
            winner_candidate_hash=str(row.get("winner_candidate_hash", "") or ""),
            challenger_candidate_hash=str(
                row.get("challenger_candidate_hash", "") or ""
            ),
            truth_gap_vs_winner=_safe_float(row.get("truth_gap_vs_winner")),
            score_gap_vs_winner=_safe_float(row.get("score_gap_vs_winner")),
            models={},
        )
        for name, cfg in configs.items():
            selected = select_weighted_frontier_candidate(feature_rows, config=cfg)
            row_entry["models"][name] = dict(
                candidate_hash=str(selected.get("candidate_hash", "") or ""),
                truth_match=selected.get("final_match"),
                rescued_from_legacy=int(
                    1
                    if str(selected.get("candidate_hash", "") or "")
                    != str(legacy.get("candidate_hash", "") or "")
                    and _safe_float(selected.get("final_match"), float("-inf"))
                    > _safe_float(legacy.get("final_match"), float("-inf"))
                    else 0
                ),
            )
        row_audit.append(row_entry)

    model_summary: Dict[str, Dict[str, Any]] = {}
    for name in configs:
        rescued_rows = [
            row
            for row in row_audit
            if int(row["models"][name]["rescued_from_legacy"]) == 1
        ]
        rescued_patterns = {
            str(row.get("pattern_key", "") or "") for row in rescued_rows
        }
        model_summary[name] = dict(
            rescued_row_count=int(len(rescued_rows)),
            rescued_pattern_count=int(len(rescued_patterns)),
            rescued_unrecovered_class=int(
                1
                if any(
                    str(row.get("challenger_candidate_hash", "") or "")
                    == "e45c25ba171877fd"
                    and int(row["models"][name]["rescued_from_legacy"]) == 1
                    for row in row_audit
                )
                else 0
            ),
            selected_candidate_hashes=sorted(
                {
                    str(row["models"][name]["candidate_hash"])
                    for row in row_audit
                    if str(row["models"][name]["candidate_hash"])
                }
            ),
        )
    return dict(
        models=model_summary,
        row_audit=row_audit,
    )


def build_stagea_weighted_robustness_sweep(
    truth_gap_rows: Sequence[Mapping[str, Any]] | None,
) -> Dict[str, Any]:
    from tools.benchmarks.periodic_sub_trans.no_wli.late_stage_frontier_fixture import (
        build_late_stage_frontier_fixture,
    )

    score_scales = (0.9, 1.0, 1.1)
    novelty_scales = (0.8, 1.0, 1.2)
    eligible_scales = (0.8, 1.0, 1.2)
    rank_penalty_scales = (0.8, 1.0, 1.2)
    configs: list[tuple[str, WeightedLateStageRerankerConfig]] = []
    idx = 0
    for score_scale in score_scales:
        for novelty_scale in novelty_scales:
            for eligible_scale in eligible_scales:
                for rank_scale in rank_penalty_scales:
                    idx += 1
                    configs.append(
                        (
                            f"cfg_{idx:03d}",
                            WeightedLateStageRerankerConfig(
                                final_score_weight=1.0 * score_scale,
                                score_gain_weight=0.75,
                                novelty_distance_weight=0.0001 * novelty_scale,
                                eligible_novel_bonus=0.005 * eligible_scale,
                                non_anchor_bonus=0.015,
                                phasea_selected_bonus=0.003,
                                source_rank_penalty_weight=0.002 * rank_scale,
                                anchor_penalty=0.01,
                            ),
                        )
                    )

    row_results: list[Dict[str, Any]] = []
    for row_obj in list(truth_gap_rows or []):
        if not isinstance(row_obj, Mapping):
            continue
        row = dict(row_obj)
        artifact_path = Path(str(row.get("artifact_path", "") or ""))
        if not artifact_path.exists():
            continue
        artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
        fixture = build_late_stage_frontier_fixture(
            artifact_path=artifact_path,
            artifact=artifact,
            fixture_id=str(artifact_path.stem),
        )
        feature_rows = build_late_stage_candidate_feature_table(fixture)
        legacy = select_legacy_frontier_winner(
            feature_rows,
            winner_hash=str(fixture.get("score_selected_winner_hash", "") or ""),
        )
        pattern_key = "|".join(str(x) for x in _truth_gap_pattern_key(row))
        rescue_count = 0
        selected_hashes: Dict[str, int] = {}
        for _, cfg in configs:
            selected = select_weighted_frontier_candidate(feature_rows, config=cfg)
            selected_hash = str(selected.get("candidate_hash", "") or "")
            selected_hashes[selected_hash] = selected_hashes.get(selected_hash, 0) + 1
            if (
                selected_hash != str(legacy.get("candidate_hash", "") or "")
                and _safe_float(selected.get("final_match"), float("-inf"))
                > _safe_float(legacy.get("final_match"), float("-inf"))
            ):
                rescue_count += 1
        row_results.append(
            dict(
                pattern_key=pattern_key,
                challenger_candidate_hash=str(
                    row.get("challenger_candidate_hash", "") or ""
                ),
                rescue_count=int(rescue_count),
                total_configs=int(len(configs)),
                selected_hash_counts=selected_hashes,
            )
        )

    dominant_rows = [
        row for row in row_results if row.get("challenger_candidate_hash") == "9002ee09917e5a0d"
    ]
    unrecovered_rows = [
        row for row in row_results if row.get("challenger_candidate_hash") == "e45c25ba171877fd"
    ]
    return dict(
        total_configs=int(len(configs)),
        dominant_pattern_all_configs_rescued=int(
            1
            if dominant_rows and all(
                int(row.get("rescue_count", 0)) == int(len(configs))
                for row in dominant_rows
            )
            else 0
        ),
        unrecovered_class_any_config_rescued=int(
            1
            if unrecovered_rows and any(int(row.get("rescue_count", 0)) > 0 for row in unrecovered_rows)
            else 0
        ),
        row_results=row_results,
    )


def build_frontier_selector_evaluation(
    fixture: Mapping[str, Any],
    *,
    config: WeightedLateStageRerankerConfig | None = None,
) -> Dict[str, Any]:
    feature_rows = build_late_stage_candidate_feature_table(fixture)
    legacy = select_legacy_frontier_winner(
        feature_rows,
        winner_hash=str(fixture.get("score_selected_winner_hash", "") or ""),
    )
    revised = select_weighted_frontier_candidate(feature_rows, config=config)
    pairwise = select_pairwise_frontier_candidate(
        feature_rows,
        winner_hash=str(fixture.get("score_selected_winner_hash", "") or ""),
    )
    oracle_hash = str(fixture.get("oracle_best_explored_hash", "") or "")
    oracle_row = next(
        (
            dict(row)
            for row in feature_rows
            if str(row.get("candidate_hash", "") or "") == oracle_hash
        ),
        {},
    )
    pair_total = 0
    pair_correct = 0
    for left_idx, left in enumerate(feature_rows):
        left_truth = _safe_float(left.get("final_match"))
        left_score = _safe_float(left.get("experimental_score"), float("nan"))
        if not math.isfinite(left_score):
            left_score = score_weighted_frontier_candidate(
                left,
                config=config or WeightedLateStageRerankerConfig(),
            )
        for right in feature_rows[left_idx + 1 :]:
            right_truth = _safe_float(right.get("final_match"))
            if not math.isfinite(left_truth) or not math.isfinite(right_truth):
                continue
            if left_truth == right_truth:
                continue
            right_score = _safe_float(right.get("experimental_score"), float("nan"))
            if not math.isfinite(right_score):
                right_score = score_weighted_frontier_candidate(
                    right,
                    config=config or WeightedLateStageRerankerConfig(),
                )
            truth_prefers_left = left_truth > right_truth
            score_prefers_left = left_score > right_score
            pair_total += 1
            if truth_prefers_left == score_prefers_left:
                pair_correct += 1
    return dict(
        legacy_candidate_hash=str(legacy.get("candidate_hash", "") or ""),
        revised_candidate_hash=str(revised.get("candidate_hash", "") or ""),
        pairwise_candidate_hash=str(pairwise.get("candidate_hash", "") or ""),
        oracle_best_candidate_hash=str(oracle_row.get("candidate_hash", "") or ""),
        legacy_truth_match=legacy.get("final_match"),
        revised_truth_match=revised.get("final_match"),
        pairwise_truth_match=pairwise.get("final_match"),
        oracle_best_truth_match=oracle_row.get("final_match"),
        rescued_from_legacy=int(
            1
            if str(revised.get("candidate_hash", "") or "")
            != str(legacy.get("candidate_hash", "") or "")
            and _safe_float(revised.get("final_match"), float("-inf"))
            > _safe_float(legacy.get("final_match"), float("-inf"))
            else 0
        ),
        pairwise_rescued_from_legacy=int(
            1
            if str(pairwise.get("candidate_hash", "") or "")
            != str(legacy.get("candidate_hash", "") or "")
            and _safe_float(pairwise.get("final_match"), float("-inf"))
            > _safe_float(legacy.get("final_match"), float("-inf"))
            else 0
        ),
        oracle_best_in_top3=int(
            1
            if oracle_hash
            and oracle_hash
            in [
                str(row.get("candidate_hash", "") or "")
                for row in sorted(
                    (
                        dict(row, experimental_score=score_weighted_frontier_candidate(
                            row,
                            config=config or WeightedLateStageRerankerConfig(),
                        ))
                        for row in feature_rows
                    ),
                    key=lambda row: (
                        _safe_float(row.get("experimental_score"), float("-inf")),
                        _safe_float(row.get("final_score"), float("-inf")),
                    ),
                    reverse=True,
                )[:3]
            ]
            else 0
        ),
        pairwise_truth_accuracy=(
            float(pair_correct) / float(pair_total) if pair_total else None
        ),
    )


def write_late_stage_selector_stagea_report(
    *,
    fixture: Mapping[str, Any],
    truth_gap_rows: Sequence[Mapping[str, Any]] | None,
    output_dir: Path,
    weighted_config: WeightedLateStageRerankerConfig | None = None,
) -> Dict[str, Any]:
    fixture_obj = dict(fixture or {})
    feature_rows = build_late_stage_candidate_feature_table(fixture_obj)
    trial_rows = build_frontier_trial_material_rows(fixture_obj)
    dataset_summary = build_truth_gap_benchmark_summary(truth_gap_rows)
    data_realism = build_stagea_data_realism_summary(dataset_summary)
    selector_eval = build_frontier_selector_evaluation(
        fixture_obj,
        config=weighted_config,
    )
    feature_story = build_stagea_feature_story(
        fixture_obj,
        weighted_config=weighted_config,
    )
    disagreement_row_audit = build_disagreement_frontier_row_audit(
        truth_gap_rows,
        weighted_config=weighted_config,
    )
    disagreement_pattern_audit = build_disagreement_frontier_pattern_audit(
        truth_gap_rows,
        weighted_config=weighted_config,
    )
    rescued_vs_unrecovered_contrast = build_stagea_rescued_vs_unrecovered_contrast(
        truth_gap_rows,
        weighted_config=weighted_config,
    )
    unrecovered_case_feature_audit = build_stagea_unrecovered_case_feature_audit(
        truth_gap_rows,
    )
    weighted_ablation_sweep = build_stagea_weighted_ablation_sweep(truth_gap_rows)
    numeric_field_ablation_sweep = build_stagea_numeric_field_ablation_sweep(
        truth_gap_rows
    )
    categorical_field_ablation_sweep = build_stagea_categorical_field_ablation_sweep(
        truth_gap_rows
    )
    weighted_robustness_sweep = build_stagea_weighted_robustness_sweep(
        truth_gap_rows
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    summary = dict(
        fixture_id=str(fixture_obj.get("fixture_id", "") or ""),
        score_selected_winner_hash=str(
            fixture_obj.get("score_selected_winner_hash", "") or ""
        ),
        oracle_best_explored_hash=str(
            fixture_obj.get("oracle_best_explored_hash", "") or ""
        ),
        frontier_key_material_complete=int(
            fixture_obj.get("frontier_key_material_complete", 0) or 0
        ),
        dataset_summary=dataset_summary,
        data_realism=data_realism,
        selector_evaluation=selector_eval,
        feature_story=feature_story,
        disagreement_frontier_row_audit=disagreement_row_audit,
        disagreement_frontier_pattern_audit=disagreement_pattern_audit,
        rescued_vs_unrecovered_contrast=rescued_vs_unrecovered_contrast,
        unrecovered_case_feature_audit=unrecovered_case_feature_audit,
        weighted_ablation_sweep=weighted_ablation_sweep,
        numeric_field_ablation_sweep=numeric_field_ablation_sweep,
        categorical_field_ablation_sweep=categorical_field_ablation_sweep,
        weighted_robustness_sweep=weighted_robustness_sweep,
    )
    (output_dir / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_dir / "v45_feature_rows.json").write_text(
        json.dumps(feature_rows, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_dir / "v45_trial_material_rows.json").write_text(
        json.dumps(trial_rows, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_dir / "disagreement_frontier_row_audit.json").write_text(
        json.dumps(disagreement_row_audit, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_dir / "disagreement_frontier_pattern_audit.json").write_text(
        json.dumps(disagreement_pattern_audit, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_dir / "rescued_vs_unrecovered_contrast.json").write_text(
        json.dumps(rescued_vs_unrecovered_contrast, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_dir / "unrecovered_case_feature_audit.json").write_text(
        json.dumps(unrecovered_case_feature_audit, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_dir / "weighted_ablation_sweep.json").write_text(
        json.dumps(weighted_ablation_sweep, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_dir / "numeric_field_ablation_sweep.json").write_text(
        json.dumps(numeric_field_ablation_sweep, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_dir / "categorical_field_ablation_sweep.json").write_text(
        json.dumps(categorical_field_ablation_sweep, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_dir / "weighted_robustness_sweep.json").write_text(
        json.dumps(weighted_robustness_sweep, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    dominant_pattern = dict(disagreement_pattern_audit[0]) if disagreement_pattern_audit else {}
    contrast_rescued = dict(rescued_vs_unrecovered_contrast.get("rescued_case", {}))
    contrast_unrecovered = dict(
        rescued_vs_unrecovered_contrast.get("unrecovered_case", {})
    )
    ablation_models = dict(weighted_ablation_sweep.get("models", {}))
    numeric_ablation_models = dict(numeric_field_ablation_sweep.get("models", {}))
    categorical_ablation_models = dict(
        categorical_field_ablation_sweep.get("models", {})
    )
    md_lines = [
        "# Late-Stage Selector Stage A",
        "",
        f"- fixture: `{summary['fixture_id']}`",
        f"- score-selected winner: `{summary['score_selected_winner_hash']}`",
        f"- oracle-best explored: `{summary['oracle_best_explored_hash']}`",
        f"- frontier key material complete: `{summary['frontier_key_material_complete']}`",
        f"- disagreement rows: `{dataset_summary['disagreement_row_count']}`",
        f"- distinct disagreement patterns: `{dataset_summary['distinct_pattern_count']}`",
        f"- broader lift status: `{data_realism['broader_lift_status']}`",
        "",
        "## Selector Evaluation",
        "",
        f"- legacy candidate: `{selector_eval['legacy_candidate_hash']}`",
        f"- weighted candidate: `{selector_eval['revised_candidate_hash']}`",
        f"- pairwise candidate: `{selector_eval['pairwise_candidate_hash']}`",
        f"- oracle best: `{selector_eval['oracle_best_candidate_hash']}`",
        f"- legacy truth: `{selector_eval['legacy_truth_match']}`",
        f"- weighted truth: `{selector_eval['revised_truth_match']}`",
        f"- pairwise truth: `{selector_eval['pairwise_truth_match']}`",
        f"- weighted rescued from legacy: `{selector_eval['rescued_from_legacy']}`",
        f"- pairwise rescued from legacy: `{selector_eval['pairwise_rescued_from_legacy']}`",
        "",
        "## Feature Story",
        "",
        f"- weighted score-only candidate: `{feature_story['model_ladder']['weighted_score_only_candidate_hash']}`",
        f"- weighted full candidate: `{feature_story['model_ladder']['weighted_full_candidate_hash']}`",
        f"- pairwise candidate: `{feature_story['model_ladder']['pairwise_candidate_hash']}`",
        f"- weighted dominant rescue group: `{feature_story['weighted_margin_explanation']['dominant_positive_group']}`",
        f"- pairwise dominant rescue group: `{feature_story['pairwise_margin_explanation']['dominant_positive_group']}`",
        "",
        "## Pattern Audit",
        "",
        f"- dominant audited pattern count: `{dominant_pattern.get('count', 0)}`",
        f"- dominant weighted rescue count: `{dominant_pattern.get('weighted_rescued_count', 0)}`",
        f"- dominant pairwise rescue count: `{dominant_pattern.get('pairwise_rescued_count', 0)}`",
        f"- dominant weighted group counts: `{dominant_pattern.get('weighted_dominant_group_counts', {})}`",
        f"- dominant pairwise group counts: `{dominant_pattern.get('pairwise_dominant_group_counts', {})}`",
        "",
        "## Rescued vs Unrecovered",
        "",
        f"- rescued challenger: `{contrast_rescued.get('challenger_candidate_hash', '')}`",
        f"- rescued challenger source rank: `{contrast_rescued.get('challenger_source_rank', 0)}`",
        f"- rescued challenger eligible novel: `{contrast_rescued.get('challenger_eligible_novel', 0)}`",
        f"- rescued weighted group totals: `{contrast_rescued.get('weighted_group_totals', {})}`",
        f"- unrecovered challenger: `{contrast_unrecovered.get('challenger_candidate_hash', '')}`",
        f"- unrecovered challenger source rank: `{contrast_unrecovered.get('challenger_source_rank', 0)}`",
        f"- unrecovered challenger eligible novel: `{contrast_unrecovered.get('challenger_eligible_novel', 0)}`",
        f"- unrecovered weighted group totals: `{contrast_unrecovered.get('weighted_group_totals', {})}`",
        "",
        "## Weighted Ablation Sweep",
        "",
        f"- score-only rescued rows/patterns: `{ablation_models.get('score_only', {}).get('rescued_row_count', 0)}` / `{ablation_models.get('score_only', {}).get('rescued_pattern_count', 0)}`",
        f"- score+novelty rescued rows/patterns: `{ablation_models.get('score_plus_novelty', {}).get('rescued_row_count', 0)}` / `{ablation_models.get('score_plus_novelty', {}).get('rescued_pattern_count', 0)}`",
        f"- score+lexical rescued rows/patterns: `{ablation_models.get('score_plus_lexical', {}).get('rescued_row_count', 0)}` / `{ablation_models.get('score_plus_lexical', {}).get('rescued_pattern_count', 0)}`",
        f"- score+novelty+lexical rescued rows/patterns: `{ablation_models.get('score_plus_novelty_plus_lexical', {}).get('rescued_row_count', 0)}` / `{ablation_models.get('score_plus_novelty_plus_lexical', {}).get('rescued_pattern_count', 0)}`",
        "",
        "## Numeric Field Ablation Sweep",
        "",
        f"- baseline score+novelty rescued rows/patterns: `{numeric_ablation_models.get('score_plus_novelty', {}).get('rescued_row_count', 0)}` / `{numeric_ablation_models.get('score_plus_novelty', {}).get('rescued_pattern_count', 0)}`",
        f"- + score_gap_to_winner rescued rows/patterns: `{numeric_ablation_models.get('score_plus_novelty_plus_score_gap_to_winner', {}).get('rescued_row_count', 0)}` / `{numeric_ablation_models.get('score_plus_novelty_plus_score_gap_to_winner', {}).get('rescued_pattern_count', 0)}`",
        f"- + score_gap_to_anchor rescued rows/patterns: `{numeric_ablation_models.get('score_plus_novelty_plus_score_gap_to_anchor', {}).get('rescued_row_count', 0)}` / `{numeric_ablation_models.get('score_plus_novelty_plus_score_gap_to_anchor', {}).get('rescued_pattern_count', 0)}`",
        f"- + init_score rescued rows/patterns: `{numeric_ablation_models.get('score_plus_novelty_plus_init_score', {}).get('rescued_row_count', 0)}` / `{numeric_ablation_models.get('score_plus_novelty_plus_init_score', {}).get('rescued_pattern_count', 0)}`",
        f"- + init_search_score rescued rows/patterns: `{numeric_ablation_models.get('score_plus_novelty_plus_init_search_score', {}).get('rescued_row_count', 0)}` / `{numeric_ablation_models.get('score_plus_novelty_plus_init_search_score', {}).get('rescued_pattern_count', 0)}`",
        "",
        "## Categorical Field Ablation Sweep",
        "",
        f"- baseline score+novelty rescued rows/patterns: `{categorical_ablation_models.get('score_plus_novelty', {}).get('rescued_row_count', 0)}` / `{categorical_ablation_models.get('score_plus_novelty', {}).get('rescued_pattern_count', 0)}`",
        f"- + phaseB_topk source penalty rescued rows/patterns: `{categorical_ablation_models.get('score_plus_novelty_plus_phaseb_topk_penalty', {}).get('rescued_row_count', 0)}` / `{categorical_ablation_models.get('score_plus_novelty_plus_phaseb_topk_penalty', {}).get('rescued_pattern_count', 0)}`",
        f"- + stage3_best_phaseB source penalty rescued rows/patterns: `{categorical_ablation_models.get('score_plus_novelty_plus_stage3_best_phaseb_penalty', {}).get('rescued_row_count', 0)}` / `{categorical_ablation_models.get('score_plus_novelty_plus_stage3_best_phaseb_penalty', {}).get('rescued_pattern_count', 0)}`",
        f"- + combined safe source penalties rescued rows/patterns: `{categorical_ablation_models.get('score_plus_novelty_plus_source_penalties', {}).get('rescued_row_count', 0)}` / `{categorical_ablation_models.get('score_plus_novelty_plus_source_penalties', {}).get('rescued_pattern_count', 0)}`",
        "",
        "## Robustness Sweep",
        "",
        f"- total configs checked: `{weighted_robustness_sweep.get('total_configs', 0)}`",
        f"- dominant `9002...` family rescued in all configs: `{weighted_robustness_sweep.get('dominant_pattern_all_configs_rescued', 0)}`",
        f"- unrecovered `e45...` class rescued in any config: `{weighted_robustness_sweep.get('unrecovered_class_any_config_rescued', 0)}`",
        "",
    ]
    (output_dir / "summary.md").write_text("\n".join(md_lines) + "\n", encoding="utf-8")
    note_lines = [
        "# Stage A Decision Note",
        "",
        "## Must-pass `v45`",
        "",
        f"- legacy winner: `{selector_eval['legacy_candidate_hash']}`",
        f"- weighted reranker: `{selector_eval['revised_candidate_hash']}`",
        f"- pairwise reranker: `{selector_eval['pairwise_candidate_hash']}`",
        f"- oracle-best explored: `{selector_eval['oracle_best_candidate_hash']}`",
        f"- weighted rescue: `{selector_eval['rescued_from_legacy']}`",
        f"- pairwise rescue: `{selector_eval['pairwise_rescued_from_legacy']}`",
        "",
        "## Feature-group reading",
        "",
        f"- weighted score-only candidate: `{feature_story['model_ladder']['weighted_score_only_candidate_hash']}`",
        f"- weighted dominant rescue group: `{feature_story['weighted_margin_explanation']['dominant_positive_group']}`",
        f"- pairwise dominant rescue group: `{feature_story['pairwise_margin_explanation']['dominant_positive_group']}`",
        "- current lexical feature group is inactive in this Stage A pass",
        "",
        "## Broader sanity",
        "",
        f"- disagreement rows: `{data_realism['row_count']}`",
        f"- distinct patterns: `{data_realism['distinct_pattern_count']}`",
        f"- dominant pattern count: `{data_realism['dominant_pattern_count']}`",
        f"- dominant pattern fraction: `{data_realism['dominant_pattern_fraction']:.3f}`",
        f"- broader lift status: `{data_realism['broader_lift_status']}`",
        f"- dominant audited pattern count: `{dominant_pattern.get('count', 0)}`",
        f"- dominant weighted group counts: `{dominant_pattern.get('weighted_dominant_group_counts', {})}`",
        f"- dominant pairwise group counts: `{dominant_pattern.get('pairwise_dominant_group_counts', {})}`",
        "",
        "## Plain-language contrast",
        "",
        f"- rescued challenger `{contrast_rescued.get('challenger_candidate_hash', '')}` is only slightly behind on score, but it is novel enough to earn structural bonuses:",
        f"  source rank `{contrast_rescued.get('challenger_source_rank', 0)}`, eligible novel `{contrast_rescued.get('challenger_eligible_novel', 0)}`, weighted groups `{contrast_rescued.get('weighted_group_totals', {})}`",
        f"- unrecovered challenger `{contrast_unrecovered.get('challenger_candidate_hash', '')}` is much further behind on score and gets no novelty rescue:",
        f"  source rank `{contrast_unrecovered.get('challenger_source_rank', 0)}`, eligible novel `{contrast_unrecovered.get('challenger_eligible_novel', 0)}`, weighted groups `{contrast_unrecovered.get('weighted_group_totals', {})}`",
        "",
        "## Feature-availability audit",
        "",
        f"- rescued present+used feature count: `{len(list(unrecovered_case_feature_audit.get('rescued_case', {}).get('present_and_used', []) or []))}`",
        f"- rescued present-but-unused feature count: `{len(list(unrecovered_case_feature_audit.get('rescued_case', {}).get('present_but_unused', []) or []))}`",
        f"- rescued absent-today feature count: `{len(list(unrecovered_case_feature_audit.get('rescued_case', {}).get('absent_today', []) or []))}`",
        f"- unrecovered present+used feature count: `{len(list(unrecovered_case_feature_audit.get('unrecovered_case', {}).get('present_and_used', []) or []))}`",
        f"- unrecovered present-but-unused feature count: `{len(list(unrecovered_case_feature_audit.get('unrecovered_case', {}).get('present_but_unused', []) or []))}`",
        f"- unrecovered absent-today feature count: `{len(list(unrecovered_case_feature_audit.get('unrecovered_case', {}).get('absent_today', []) or []))}`",
        "",
        "## Weighted ablation sweep",
        "",
        f"- score-only rescued rows/patterns: `{ablation_models.get('score_only', {}).get('rescued_row_count', 0)}` / `{ablation_models.get('score_only', {}).get('rescued_pattern_count', 0)}`",
        f"- score+novelty rescued rows/patterns: `{ablation_models.get('score_plus_novelty', {}).get('rescued_row_count', 0)}` / `{ablation_models.get('score_plus_novelty', {}).get('rescued_pattern_count', 0)}`",
        f"- score+lexical rescued rows/patterns: `{ablation_models.get('score_plus_lexical', {}).get('rescued_row_count', 0)}` / `{ablation_models.get('score_plus_lexical', {}).get('rescued_pattern_count', 0)}`",
        f"- score+novelty+lexical rescued rows/patterns: `{ablation_models.get('score_plus_novelty_plus_lexical', {}).get('rescued_row_count', 0)}` / `{ablation_models.get('score_plus_novelty_plus_lexical', {}).get('rescued_pattern_count', 0)}`",
        "",
        "## Numeric field ablation sweep",
        "",
        f"- baseline score+novelty rescued rows/patterns: `{numeric_ablation_models.get('score_plus_novelty', {}).get('rescued_row_count', 0)}` / `{numeric_ablation_models.get('score_plus_novelty', {}).get('rescued_pattern_count', 0)}`",
        f"- + score_gap_to_winner rescued rows/patterns: `{numeric_ablation_models.get('score_plus_novelty_plus_score_gap_to_winner', {}).get('rescued_row_count', 0)}` / `{numeric_ablation_models.get('score_plus_novelty_plus_score_gap_to_winner', {}).get('rescued_pattern_count', 0)}`",
        f"- + score_gap_to_anchor rescued rows/patterns: `{numeric_ablation_models.get('score_plus_novelty_plus_score_gap_to_anchor', {}).get('rescued_row_count', 0)}` / `{numeric_ablation_models.get('score_plus_novelty_plus_score_gap_to_anchor', {}).get('rescued_pattern_count', 0)}`",
        f"- + init_score rescued rows/patterns: `{numeric_ablation_models.get('score_plus_novelty_plus_init_score', {}).get('rescued_row_count', 0)}` / `{numeric_ablation_models.get('score_plus_novelty_plus_init_score', {}).get('rescued_pattern_count', 0)}`",
        f"- + init_search_score rescued rows/patterns: `{numeric_ablation_models.get('score_plus_novelty_plus_init_search_score', {}).get('rescued_row_count', 0)}` / `{numeric_ablation_models.get('score_plus_novelty_plus_init_search_score', {}).get('rescued_pattern_count', 0)}`",
        "",
        "## Categorical field ablation sweep",
        "",
        f"- baseline score+novelty rescued rows/patterns: `{categorical_ablation_models.get('score_plus_novelty', {}).get('rescued_row_count', 0)}` / `{categorical_ablation_models.get('score_plus_novelty', {}).get('rescued_pattern_count', 0)}`",
        f"- + phaseB_topk source penalty rescued rows/patterns: `{categorical_ablation_models.get('score_plus_novelty_plus_phaseb_topk_penalty', {}).get('rescued_row_count', 0)}` / `{categorical_ablation_models.get('score_plus_novelty_plus_phaseb_topk_penalty', {}).get('rescued_pattern_count', 0)}`",
        f"- + stage3_best_phaseB source penalty rescued rows/patterns: `{categorical_ablation_models.get('score_plus_novelty_plus_stage3_best_phaseb_penalty', {}).get('rescued_row_count', 0)}` / `{categorical_ablation_models.get('score_plus_novelty_plus_stage3_best_phaseb_penalty', {}).get('rescued_pattern_count', 0)}`",
        f"- + combined safe source penalties rescued rows/patterns: `{categorical_ablation_models.get('score_plus_novelty_plus_source_penalties', {}).get('rescued_row_count', 0)}` / `{categorical_ablation_models.get('score_plus_novelty_plus_source_penalties', {}).get('rescued_pattern_count', 0)}`",
        "",
        "## Robustness sweep",
        "",
        f"- total configs checked: `{weighted_robustness_sweep.get('total_configs', 0)}`",
        f"- dominant `9002...` family rescued in all configs: `{weighted_robustness_sweep.get('dominant_pattern_all_configs_rescued', 0)}`",
        f"- unrecovered `e45...` class rescued in any config: `{weighted_robustness_sweep.get('unrecovered_class_any_config_rescued', 0)}`",
        "",
        "Current reading:",
        "",
        "- the must-pass `v45` failure is clearly rescued by both benchmark-only rerankers",
        "- the rescue currently depends on structural / novelty signals more than on score-only features",
        "- the same structural / novelty story recurs across the dominant repeated disagreement pattern family in the current audited rows",
        "- current ablations test whether unrecovered cases are blocked by score gaps, novelty gaps, or simply missing lexical/semantic fields",
        "- current numeric-field ablations test whether present-but-unused live score fields help the unrecovered class before replay-ready semantic capture exists",
        "- current safe categorical-field ablations test whether stable source information adds anything beyond the novelty baseline",
        "- current robustness sweep checks whether the `9002...` rescue is stable under small weight changes or only a knife-edge result",
        "- broader evidence is still thin because the disagreement dataset is small and heavily concentrated in one repeated pattern family",
        "- this supports continuing Stage A while waiting for the replay-ready `v46` frontier rather than escalating to live integration",
        "",
    ]
    (output_dir / "decision_note.md").write_text(
        "\n".join(note_lines) + "\n",
        encoding="utf-8",
    )
    return summary
