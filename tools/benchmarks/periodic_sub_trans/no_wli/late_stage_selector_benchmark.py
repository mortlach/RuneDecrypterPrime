from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from statistics import mean
from typing import Any, Dict, Mapping, Sequence


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
    novelty_distance_weight: float = 0.0001
    eligible_novel_bonus: float = 0.005
    non_anchor_bonus: float = 0.015
    phasea_selected_bonus: float = 0.003
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


def score_weighted_frontier_candidate(
    feature_row: Mapping[str, Any],
    *,
    config: WeightedLateStageRerankerConfig,
) -> float:
    row = dict(feature_row or {})
    score = 0.0
    score += config.final_score_weight * _finite_or_zero(row.get("final_score"))
    score += config.score_gain_weight * _finite_or_zero(row.get("score_gain"))
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
    selector_eval = build_frontier_selector_evaluation(
        fixture_obj,
        config=weighted_config,
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
        selector_evaluation=selector_eval,
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
    md_lines = [
        "# Late-Stage Selector Stage A",
        "",
        f"- fixture: `{summary['fixture_id']}`",
        f"- score-selected winner: `{summary['score_selected_winner_hash']}`",
        f"- oracle-best explored: `{summary['oracle_best_explored_hash']}`",
        f"- frontier key material complete: `{summary['frontier_key_material_complete']}`",
        f"- disagreement rows: `{dataset_summary['disagreement_row_count']}`",
        f"- distinct disagreement patterns: `{dataset_summary['distinct_pattern_count']}`",
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
    ]
    (output_dir / "summary.md").write_text("\n".join(md_lines) + "\n", encoding="utf-8")
    return summary
