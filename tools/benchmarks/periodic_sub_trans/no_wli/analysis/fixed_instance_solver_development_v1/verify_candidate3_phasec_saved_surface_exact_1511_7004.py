from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np


def _find_repo_root() -> Path:
    here = Path(__file__).resolve()
    for parent in [here] + list(here.parents):
        if (parent / "src").exists() and (parent / "tools").exists():
            return parent
    raise RuntimeError(
        "Could not locate repo root from "
        "verify_candidate3_phasec_saved_surface_exact_1511_7004.py"
    )


REPO_ROOT = _find_repo_root()
SRC_DIR = REPO_ROOT / "src"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if SRC_DIR.exists() and str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from tools.benchmarks.periodic_sub_trans.common.batch_eval import (
    decrypt_and_score_keys_chunked,
    score_plaintexts_chunked,
)
from tools.benchmarks.periodic_sub_trans.no_wli import (
    artifact_resume as resume_mod,
    replay_phasec_rescue_sweep as phasec_replay_mod,
)
from tools.benchmarks.periodic_sub_trans.no_wli.shadow_stop_v1 import (
    build_shadow_stop_v1_state,
    update_shadow_stop_v1_state,
)
from tools.benchmarks.periodic_sub_trans.no_wli.stage2_promotion import (
    is_better_stage3_candidate_preserving_solve,
)
from tools.benchmarks.periodic_sub_trans.no_wli.analysis.fixed_instance_solver_development_v1 import (
    verify_candidate3_phasec_anchor_swap_exact_replay_611_7004 as retained_mod,
    verify_candidate3_phasec_saved_surface_1511_7004 as saved_surface_mod,
)


SOURCE_ARTIFACT_REL_PATH = Path(
    "output/tools/benchmarks/periodic_sub_trans/no_wli/"
    "20260414T020217422155Z__bench_solve_pipeline_no_wli__9557c0f/"
    "final_instances/fixture_001__p9_c3_l1000__text0__seed1511__search7004.json"
)
RUN_LABEL = "candidate3_phasec_saved_surface_exact_1511_search7004_v1"
OUTPUT_BASE_DIR = (
    REPO_ROOT
    / "output"
    / "tools"
    / "benchmarks"
    / "periodic_sub_trans"
    / "no_wli"
    / "analysis"
    / "fixed_instance_solver_development_v1"
)

PHASEC_SHADOW_STOP_V1_PLATEAU_STEPS = 16
PHASEC_SHADOW_STOP_V1_HIGH_SCORE_FLOOR = 0.45
PHASEC_SHADOW_STOP_V1_HIGH_SCORE_STABLE_STEPS = 4
PHASEC_SHADOW_STOP_V1_SCORE_IMPROVE_EPS = 1.0e-6


def _utc_label() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _relative_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def _safe_str(value: Any) -> str:
    return str(value or "")


def _safe_int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _safe_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return float("nan")


def _truth_match_ratio(
    plaintext_idx: Sequence[int] | np.ndarray,
    target_plaintext_idx: Sequence[int] | np.ndarray,
) -> float:
    lhs = np.asarray(plaintext_idx, dtype=np.uint8).reshape(-1)
    rhs = np.asarray(target_plaintext_idx, dtype=np.uint8).reshape(-1)
    if int(lhs.size) == 0 or int(rhs.size) == 0 or int(lhs.size) != int(rhs.size):
        return float("nan")
    return float(np.mean(lhs == rhs))


def _phasec_cfg(run_config: Mapping[str, Any]) -> dict[str, Any]:
    stage3 = (run_config.get("stage3") or {}) if isinstance(run_config, Mapping) else {}
    two_phase = (stage3.get("two_phase") or {}) if isinstance(stage3, Mapping) else {}
    return dict((two_phase.get("phase_c") or {}))


def _resolve_phasec_seed(
    run_config: Mapping[str, Any],
    *,
    phasec_seed_override: int | None = None,
) -> int:
    if phasec_seed_override is not None:
        return int(phasec_seed_override)
    return int(phasec_replay_mod._phasec_seed(run_config))


def _require_saved_surface_supported(run_config: Mapping[str, Any]) -> None:
    phasec = _phasec_cfg(run_config)
    rescue_enabled = bool(phasec.get("rescue_enabled", False))
    cfg = dict(phasec.get("cfg") or {})
    if rescue_enabled or int(cfg.get("rescue_candidates", 0) or 0) > 0:
        raise NotImplementedError(
            "Saved-surface Phase-C exact replay currently supports rescue-disabled cases only"
        )


def _load_saved_start_rows(artifact: Mapping[str, Any]) -> list[dict[str, Any]]:
    diagnostics = dict(artifact.get("stage3_diagnostics", {}) or {})
    return [
        dict(row)
        for row in list(diagnostics.get("phaseC_start_summaries", []) or [])
        if isinstance(row, Mapping)
    ]


def _phasec_lexical_rank_builder(
    *,
    scorer_word_ngram_report_runtime: Any | None,
    require_batch_scoring: bool,
    lexical_max_calls: int,
    lexical_stats: dict[str, int],
) -> Any:
    phasec_lexical_cache: dict[tuple[int, ...], tuple[float, float, float]] = {}
    phasec_default_lex = (-1.0, float("-inf"), float("-inf"))

    def _phasec_lexical_rank(
        *,
        key_vals: Sequence[int],
        plaintext_idx: np.ndarray,
        word_ngram_tiebreak: bool,
    ) -> tuple[float, float, float]:
        lexical_stats["requests"] = int(lexical_stats.get("requests", 0)) + 1
        if (not bool(word_ngram_tiebreak)) or scorer_word_ngram_report_runtime is None:
            return phasec_default_lex
        key_t = tuple(int(x) for x in key_vals)
        cached = phasec_lexical_cache.get(key_t, None)
        if cached is not None:
            lexical_stats["cache_hits"] = int(lexical_stats.get("cache_hits", 0)) + 1
            return cached
        if int(lexical_max_calls) > 0 and int(
            lexical_stats.get("cache_misses", 0)
        ) >= int(lexical_max_calls):
            lexical_stats["budget_skips"] = int(lexical_stats.get("budget_skips", 0)) + 1
            return phasec_default_lex
        lexical_stats["cache_misses"] = int(lexical_stats.get("cache_misses", 0)) + 1
        _scores, _stats = score_plaintexts_chunked(
            scorer=scorer_word_ngram_report_runtime,
            plaintexts=[np.asarray(plaintext_idx, dtype=np.uint8).reshape(-1)],
            wli=None,
            chunk_size=1,
            require_batch=bool(require_batch_scoring),
        )
        _ = _scores, _stats
        lex_rank = phasec_default_lex
        try:
            if hasattr(scorer_word_ngram_report_runtime, "last_stats") and callable(
                scorer_word_ngram_report_runtime.last_stats
            ):
                stats_obj = scorer_word_ngram_report_runtime.last_stats()
                if isinstance(stats_obj, dict):
                    active = (
                        1.0
                        if bool(stats_obj.get("word_ngram_judge_active", False))
                        else 0.0
                    )
                    trust = float(
                        stats_obj.get("word_ngram_judge_trust_score", float("-inf"))
                    )
                    if not np.isfinite(trust):
                        trust = float("-inf")
                    report_xent = float(
                        stats_obj.get("word_ngram_judge_report_xent", float("nan"))
                    )
                    report_xent_sort = (
                        float(-report_xent)
                        if np.isfinite(report_xent)
                        else float("-inf")
                    )
                    lex_rank = (active, trust, report_xent_sort)
        except Exception:
            lex_rank = phasec_default_lex
        phasec_lexical_cache[key_t] = tuple(lex_rank)
        return tuple(lex_rank)

    return _phasec_lexical_rank


def _phasec_is_better_builder(
    *,
    phasec_lexical_rank_fn: Any,
    oracle_assist_selection_effective: bool,
    lexical_match_tie_eps: float,
    lexical_score_tie_eps: float,
    lexical_min_match: float,
    solve_match_threshold: float,
    lexical_stats: dict[str, int],
    word_ngram_tiebreak: bool,
) -> Any:
    def _phasec_is_better(
        *,
        cand_score: float,
        cand_match: float,
        cand_key: Sequence[int],
        cand_pt: np.ndarray,
        best_score_v: float,
        best_match_v: float,
        best_key_v: Sequence[int],
        best_pt_v: np.ndarray,
    ) -> bool:
        cand_primary = bool(
            is_better_stage3_candidate_preserving_solve(
                cand_score=float(cand_score),
                cand_match=float(cand_match),
                best_score=float(best_score_v),
                best_match=float(best_match_v),
                solve_threshold=float(solve_match_threshold),
                score_first=(not bool(oracle_assist_selection_effective)),
            )
        )
        best_primary = bool(
            is_better_stage3_candidate_preserving_solve(
                cand_score=float(best_score_v),
                cand_match=float(best_match_v),
                best_score=float(cand_score),
                best_match=float(cand_match),
                solve_threshold=float(solve_match_threshold),
                score_first=(not bool(oracle_assist_selection_effective)),
            )
        )
        if cand_primary and (not best_primary):
            return True
        if best_primary and (not cand_primary):
            return False
        cand_match_f = float(cand_match)
        best_match_f = float(best_match_v)
        cand_score_f = float(cand_score)
        best_score_f = float(best_score_v)
        match_gap = (
            float(cand_match_f - best_match_f)
            if np.isfinite(cand_match_f) and np.isfinite(best_match_f)
            else float("nan")
        )
        score_gap = (
            float(cand_score_f - best_score_f)
            if np.isfinite(cand_score_f) and np.isfinite(best_score_f)
            else float("nan")
        )
        if np.isfinite(match_gap) and abs(match_gap) > float(lexical_match_tie_eps):
            return bool(match_gap > 0.0)
        if np.isfinite(score_gap) and abs(score_gap) > float(lexical_score_tie_eps):
            return bool(score_gap > 0.0)
        gate_match = max(
            cand_match_f if np.isfinite(cand_match_f) else float("-inf"),
            best_match_f if np.isfinite(best_match_f) else float("-inf"),
        )
        if gate_match < float(lexical_min_match):
            lexical_stats["threshold_skips"] = int(
                lexical_stats.get("threshold_skips", 0)
            ) + 1
            if np.isfinite(match_gap) and match_gap != 0.0:
                return bool(match_gap > 0.0)
            if np.isfinite(score_gap) and score_gap != 0.0:
                return bool(score_gap > 0.0)
            return False
        lexical_stats["tiebreak_decisions"] = int(
            lexical_stats.get("tiebreak_decisions", 0)
        ) + 1
        cand_lex = phasec_lexical_rank_fn(
            key_vals=cand_key,
            plaintext_idx=np.asarray(cand_pt, dtype=np.uint8).reshape(-1),
            word_ngram_tiebreak=bool(word_ngram_tiebreak),
        )
        best_lex = phasec_lexical_rank_fn(
            key_vals=best_key_v,
            plaintext_idx=np.asarray(best_pt_v, dtype=np.uint8).reshape(-1),
            word_ngram_tiebreak=bool(word_ngram_tiebreak),
        )
        return bool(cand_lex > best_lex)

    return _phasec_is_better


def _count_source_rows(rows: Sequence[Mapping[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        source = _safe_str(row.get("source"))
        if not source:
            continue
        counts[source] = int(counts.get(source, 0)) + 1
    return counts


def _ordered_start_identities(
    rows: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    identities: list[dict[str, Any]] = []
    for start_rank, row in enumerate(rows, start=1):
        identities.append(
            {
                "start_rank": int(start_rank),
                "lane": "anchor" if int(start_rank) == 1 else "challenger",
                "source": _safe_str(row.get("source")),
                "source_rank": _safe_int(row.get("source_rank")),
                "candidate_hash": _safe_str(row.get("candidate_hash")),
                "selection_bucket": _safe_str(row.get("selection_bucket")),
                "selected_by_phaseb_topk_anchor_policy": _safe_int(
                    row.get("selected_by_phaseb_topk_anchor_policy")
                ),
                "init_match": _safe_float(row.get("init_match")),
                "init_score": _safe_float(row.get("init_score")),
            }
        )
    return identities


def _prepare_saved_start_rows(
    rows: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    prepared: list[dict[str, Any]] = []
    for start_rank, row in enumerate(rows, start=1):
        prepared.append(
            dict(
                dict(row),
                lane="anchor" if int(start_rank) == 1 else "challenger",
                selection_bucket=_safe_str(
                    row.get(
                        "selection_bucket",
                        "anchor" if int(start_rank) == 1 else "legacy_fill",
                    )
                ),
                selected_by_phaseb_topk_anchor_policy=_safe_int(
                    row.get("selected_by_phaseb_topk_anchor_policy")
                ),
            )
        )
    return prepared


def _single_key_eval(
    *,
    key_vals: Sequence[int],
    artifact: Mapping[str, Any],
    full_cipher: Any,
    scorer_full_runtime: Any,
    batch_eval_chunk_size: int,
    require_batch_scoring: bool,
) -> tuple[np.ndarray, float]:
    pts, scores, _stats = decrypt_and_score_keys_chunked(
        cipher=full_cipher,
        ciphertext=np.asarray(artifact.get("ciphertext_idx", []), dtype=np.uint8),
        keys=[list(map(int, key_vals))],
        scorer=scorer_full_runtime,
        wli=None,
        chunk_size=1,
        require_batch=bool(require_batch_scoring),
    )
    _ = _stats
    pt = (
        np.asarray(pts[0], dtype=np.uint8).reshape(-1)
        if int(pts.shape[0]) > 0
        else np.asarray([], dtype=np.uint8)
    )
    score = float(scores[0]) if int(scores.size) > 0 else float("nan")
    return pt, score


def _single_search_score(
    *,
    plaintext_idx: Sequence[int] | np.ndarray,
    scorer_search_runtime: Any,
    batch_eval_chunk_size: int,
    require_batch_scoring: bool,
) -> float:
    if scorer_search_runtime is None:
        return float("nan")
    scores, _stats = score_plaintexts_chunked(
        scorer=scorer_search_runtime,
        plaintexts=[np.asarray(plaintext_idx, dtype=np.uint8).reshape(-1)],
        wli=None,
        chunk_size=int(max(1, int(batch_eval_chunk_size))),
        require_batch=bool(require_batch_scoring),
    )
    _ = _stats
    return float(scores[0]) if int(scores.size) > 0 else float("nan")


def run_saved_surface_phasec_replay(
    *,
    case: phasec_replay_mod.ArtifactCase,
    saved_rows: Sequence[Mapping[str, Any]],
    replay_label: str,
    phasec_seed_override: int | None = None,
) -> dict[str, Any]:
    _require_saved_surface_supported(case.run_config)
    start_rows = _prepare_saved_start_rows(saved_rows)
    if not start_rows:
        raise ValueError("No saved Phase-C start rows were found in the retained artifact")

    artifact = dict(case.artifact)
    run_config = dict(case.run_config)
    phasec = _phasec_cfg(run_config)
    phasec_cfg = dict(phasec.get("cfg") or {})
    steps = int(max(0, int(phasec_cfg.get("steps", 0) or 0)))
    proposals_per_step = int(
        max(1, int(phasec_cfg.get("proposals_per_step", 1) or 1))
    )
    three_cycle_prob = float(
        max(0.0, min(1.0, float(phasec_cfg.get("three_cycle_prob", 0.0) or 0.0)))
    )
    lexical_min_match = float(
        max(0.0, min(1.0, float(phasec_cfg.get("lexical_min_match", 0.72) or 0.0)))
    )
    lexical_match_tie_eps = float(
        max(0.0, float(phasec_cfg.get("lexical_match_tie_eps", 0.01) or 0.0))
    )
    lexical_score_tie_eps = float(
        max(0.0, float(phasec_cfg.get("lexical_score_tie_eps", 0.002) or 0.0))
    )
    lexical_max_calls = int(max(0, int(phasec_cfg.get("lexical_max_calls", 256) or 0)))
    word_ngram_tiebreak = bool(phasec.get("word_ngram_tiebreak", False))
    batch_eval_chunk_size = int(resume_mod.DEFAULT_BATCH_EVAL_CHUNK_SIZE)
    require_batch_scoring = bool(resume_mod.DEFAULT_REQUIRE_BATCH_SCORING)
    oracle_assist_selection_effective = bool(
        run_config.get("oracle_assist_selection_effective", False)
    )
    solve_match_threshold = float(run_config.get("threshold", 0.9) or 0.9)
    tier_period = int(artifact.get("period", 0) or 0)
    alphabet_size = int(artifact.get("alphabet_size", 0) or 0)
    target_plaintext_idx = np.asarray(
        artifact.get("target_plaintext_idx", []),
        dtype=np.uint8,
    ).reshape(-1)
    phasec_seed = _resolve_phasec_seed(
        run_config,
        phasec_seed_override=phasec_seed_override,
    )
    rng = np.random.default_rng(int(phasec_seed))

    full_cipher = phasec_replay_mod._build_cipher(artifact)
    scorer_full_runtime = phasec_replay_mod._build_stage3_scorer_runtime(
        artifact=artifact,
        run_config=run_config,
        scorer_key="scorer",
    )
    scorer_search_runtime = phasec_replay_mod._build_stage3_scorer_runtime(
        artifact=artifact,
        run_config=run_config,
        scorer_key="search_scorer",
    )
    scorer_word_ngram_report_runtime = (
        phasec_replay_mod._build_stage3_word_ngram_report_runtime(
            artifact=artifact,
            run_config=run_config,
        )
    )

    lexical_stats: dict[str, int] = {
        "requests": 0,
        "cache_hits": 0,
        "cache_misses": 0,
        "budget_skips": 0,
        "threshold_skips": 0,
        "tiebreak_decisions": 0,
    }
    phasec_lexical_rank = _phasec_lexical_rank_builder(
        scorer_word_ngram_report_runtime=scorer_word_ngram_report_runtime,
        require_batch_scoring=bool(require_batch_scoring),
        lexical_max_calls=int(lexical_max_calls),
        lexical_stats=lexical_stats,
    )
    phasec_is_better = _phasec_is_better_builder(
        phasec_lexical_rank_fn=phasec_lexical_rank,
        oracle_assist_selection_effective=bool(oracle_assist_selection_effective),
        lexical_match_tie_eps=float(lexical_match_tie_eps),
        lexical_score_tie_eps=float(lexical_score_tie_eps),
        lexical_min_match=float(lexical_min_match),
        solve_match_threshold=float(solve_match_threshold),
        lexical_stats=lexical_stats,
        word_ngram_tiebreak=bool(word_ngram_tiebreak),
    )

    pre_phasec_best_row = dict(start_rows[0])
    global_best_key = list(map(int, pre_phasec_best_row.get("init_key_idx", []) or []))
    global_best_pt = np.asarray(
        pre_phasec_best_row.get("init_plaintext_idx", []),
        dtype=np.uint8,
    ).reshape(-1)
    global_best_score = _safe_float(pre_phasec_best_row.get("init_score"))
    global_best_match = _safe_float(pre_phasec_best_row.get("init_match"))
    if int(global_best_pt.size) <= 0 or not np.isfinite(global_best_score):
        global_best_pt, global_best_score = _single_key_eval(
            key_vals=global_best_key,
            artifact=artifact,
            full_cipher=full_cipher,
            scorer_full_runtime=scorer_full_runtime,
            batch_eval_chunk_size=int(batch_eval_chunk_size),
            require_batch_scoring=bool(require_batch_scoring),
        )
        global_best_match = _truth_match_ratio(global_best_pt, target_plaintext_idx)

    global_best_search_score = _single_search_score(
        plaintext_idx=global_best_pt,
        scorer_search_runtime=scorer_search_runtime,
        batch_eval_chunk_size=int(batch_eval_chunk_size),
        require_batch_scoring=bool(require_batch_scoring),
    )

    phasec_evals = 0
    phasec_accepts = 0
    phasec_improves = 0
    start_summaries: list[dict[str, Any]] = []
    phasec_final_winner_lane = "anchor"
    phasec_final_winner_source = _safe_str(pre_phasec_best_row.get("source"))
    phasec_final_winner_source_rank = _safe_int(pre_phasec_best_row.get("source_rank"))
    phasec_final_winner_candidate_hash = _safe_str(
        pre_phasec_best_row.get("candidate_hash")
    )
    anchor_best_key = list(map(int, global_best_key))
    anchor_best_pt = np.asarray(global_best_pt, dtype=np.uint8).copy()
    anchor_best_score = float(global_best_score)
    anchor_best_match = float(global_best_match)
    anchor_best_established = False

    for start_rank, start_row in enumerate(start_rows, start=1):
        start_key = list(map(int, start_row.get("init_key_idx", []) or []))
        start_pt = np.asarray(
            start_row.get("init_plaintext_idx", []),
            dtype=np.uint8,
        ).reshape(-1)
        start_score = _safe_float(start_row.get("init_score"))
        start_match = _safe_float(start_row.get("init_match"))
        if int(start_pt.size) <= 0 or not np.isfinite(start_score):
            start_pt, start_score = _single_key_eval(
                key_vals=start_key,
                artifact=artifact,
                full_cipher=full_cipher,
                scorer_full_runtime=scorer_full_runtime,
                batch_eval_chunk_size=int(batch_eval_chunk_size),
                require_batch_scoring=bool(require_batch_scoring),
            )
            start_match = _truth_match_ratio(start_pt, target_plaintext_idx)
        init_search_score = _safe_float(start_row.get("init_search_score"))
        if not np.isfinite(init_search_score):
            init_search_score = _single_search_score(
                plaintext_idx=start_pt,
                scorer_search_runtime=scorer_search_runtime,
                batch_eval_chunk_size=int(batch_eval_chunk_size),
                require_batch_scoring=bool(require_batch_scoring),
            )

        cur_key = list(map(int, start_key))
        cur_pt = np.asarray(start_pt, dtype=np.uint8).copy()
        cur_score = float(start_score)
        cur_match = float(start_match)
        local_best_key = list(map(int, cur_key))
        local_best_pt = np.asarray(cur_pt, dtype=np.uint8).copy()
        local_best_score = float(cur_score)
        local_best_match = float(cur_match)
        start_accepts_before = int(phasec_accepts)
        start_improves_before = int(phasec_improves)
        start_evals_before = int(phasec_evals)
        lexical_before = dict(lexical_stats)
        shadow_state = build_shadow_stop_v1_state(
            phase_name="phaseC_saved_surface",
            plateau_work_units=int(PHASEC_SHADOW_STOP_V1_PLATEAU_STEPS),
            high_score_floor=float(PHASEC_SHADOW_STOP_V1_HIGH_SCORE_FLOOR),
            high_score_stable_work_units=int(
                PHASEC_SHADOW_STOP_V1_HIGH_SCORE_STABLE_STEPS
            ),
            score_improve_eps=float(PHASEC_SHADOW_STOP_V1_SCORE_IMPROVE_EPS),
            initial_score=float(local_best_score),
            initial_match=float(local_best_match),
        )

        for step_idx in range(int(steps)):
            proposal_keys: list[list[int]] = []
            for _proposal_idx in range(int(proposals_per_step)):
                cand = list(map(int, cur_key))
                phase_i = int(rng.integers(0, max(1, int(tier_period))))
                phase_base = int(phase_i * int(alphabet_size))
                if int(alphabet_size) >= 3 and float(rng.random()) < float(three_cycle_prob):
                    picks = np.asarray(
                        rng.choice(int(alphabet_size), size=3, replace=False),
                        dtype=np.int64,
                    )
                    i0 = int(phase_base + int(picks[0]))
                    i1 = int(phase_base + int(picks[1]))
                    i2 = int(phase_base + int(picks[2]))
                    v0, v1, v2 = cand[i0], cand[i1], cand[i2]
                    cand[i0], cand[i1], cand[i2] = int(v2), int(v0), int(v1)
                else:
                    a = int(rng.integers(0, int(alphabet_size)))
                    b = int(rng.integers(0, max(1, int(alphabet_size - 1))))
                    if b >= a:
                        b += 1
                    i1 = int(phase_base + int(a))
                    i2 = int(phase_base + int(b))
                    cand[i1], cand[i2] = int(cand[i2]), int(cand[i1])
                proposal_keys.append(cand)

            prop_pts, prop_scores, _prop_stats = decrypt_and_score_keys_chunked(
                cipher=full_cipher,
                ciphertext=np.asarray(artifact.get("ciphertext_idx", []), dtype=np.uint8),
                keys=proposal_keys,
                scorer=scorer_full_runtime,
                wli=None,
                chunk_size=int(min(int(batch_eval_chunk_size), len(proposal_keys))),
                require_batch=bool(require_batch_scoring),
            )
            _ = _prop_stats
            phasec_evals += int(len(proposal_keys))
            best_prop_key: list[int] | None = None
            best_prop_pt = np.asarray([], dtype=np.uint8)
            best_prop_score = float("nan")
            best_prop_match = float("nan")
            for cand_idx, cand_key in enumerate(proposal_keys):
                if cand_idx >= int(prop_pts.shape[0]):
                    continue
                cand_pt = np.asarray(prop_pts[cand_idx], dtype=np.uint8).reshape(-1)
                cand_score = (
                    float(prop_scores[cand_idx])
                    if cand_idx < int(prop_scores.size)
                    else float("nan")
                )
                cand_match = _truth_match_ratio(cand_pt, target_plaintext_idx)
                if not phasec_is_better(
                    cand_score=float(cand_score),
                    cand_match=float(cand_match),
                    cand_key=cand_key,
                    cand_pt=cand_pt,
                    best_score_v=float(cur_score),
                    best_match_v=float(cur_match),
                    best_key_v=cur_key,
                    best_pt_v=cur_pt,
                ):
                    continue
                if best_prop_key is None or phasec_is_better(
                    cand_score=float(cand_score),
                    cand_match=float(cand_match),
                    cand_key=cand_key,
                    cand_pt=cand_pt,
                    best_score_v=float(best_prop_score),
                    best_match_v=float(best_prop_match),
                    best_key_v=list(map(int, best_prop_key)),
                    best_pt_v=best_prop_pt,
                ):
                    best_prop_key = list(map(int, cand_key))
                    best_prop_pt = np.asarray(cand_pt, dtype=np.uint8).copy()
                    best_prop_score = float(cand_score)
                    best_prop_match = float(cand_match)

            if best_prop_key is not None:
                cur_key = list(map(int, best_prop_key))
                cur_pt = np.asarray(best_prop_pt, dtype=np.uint8).copy()
                cur_score = float(best_prop_score)
                cur_match = float(best_prop_match)
                phasec_accepts += 1
                if phasec_is_better(
                    cand_score=float(cur_score),
                    cand_match=float(cur_match),
                    cand_key=cur_key,
                    cand_pt=cur_pt,
                    best_score_v=float(local_best_score),
                    best_match_v=float(local_best_match),
                    best_key_v=local_best_key,
                    best_pt_v=local_best_pt,
                ):
                    local_best_key = list(map(int, cur_key))
                    local_best_pt = np.asarray(cur_pt, dtype=np.uint8).copy()
                    local_best_score = float(cur_score)
                    local_best_match = float(cur_match)
                    phasec_improves += 1

            shadow_state = update_shadow_stop_v1_state(
                shadow_state,
                work_unit=int(step_idx + 1),
                evals_done=int(int(phasec_evals) - int(start_evals_before)),
                best_score=float(local_best_score),
                best_match=float(local_best_match),
                progress_counter=int(int(phasec_improves) - int(start_improves_before)),
                novelty_counter=int(int(phasec_accepts) - int(start_accepts_before)),
            )

        if int(start_rank) == 1:
            anchor_best_key = list(map(int, local_best_key))
            anchor_best_pt = np.asarray(local_best_pt, dtype=np.uint8).copy()
            anchor_best_score = float(local_best_score)
            anchor_best_match = float(local_best_match)
            anchor_best_established = True
            overtook_anchor = 0
        else:
            overtook_anchor = int(
                1
                if bool(anchor_best_established)
                and phasec_is_better(
                    cand_score=float(local_best_score),
                    cand_match=float(local_best_match),
                    cand_key=local_best_key,
                    cand_pt=local_best_pt,
                    best_score_v=float(anchor_best_score),
                    best_match_v=float(anchor_best_match),
                    best_key_v=anchor_best_key,
                    best_pt_v=anchor_best_pt,
                )
                else 0
            )

        became_global_best = int(
            1
            if phasec_is_better(
                cand_score=float(local_best_score),
                cand_match=float(local_best_match),
                cand_key=local_best_key,
                cand_pt=local_best_pt,
                best_score_v=float(global_best_score),
                best_match_v=float(global_best_match),
                best_key_v=global_best_key,
                best_pt_v=global_best_pt,
            )
            else 0
        )
        if int(became_global_best) == 1:
            global_best_key = list(map(int, local_best_key))
            global_best_pt = np.asarray(local_best_pt, dtype=np.uint8).copy()
            global_best_score = float(local_best_score)
            global_best_match = float(local_best_match)
            global_best_search_score = _single_search_score(
                plaintext_idx=global_best_pt,
                scorer_search_runtime=scorer_search_runtime,
                batch_eval_chunk_size=int(batch_eval_chunk_size),
                require_batch_scoring=bool(require_batch_scoring),
            )
            phasec_final_winner_lane = "anchor" if int(start_rank) == 1 else "challenger"
            phasec_final_winner_source = _safe_str(start_row.get("source"))
            phasec_final_winner_source_rank = _safe_int(start_row.get("source_rank"))
            phasec_final_winner_candidate_hash = _safe_str(
                start_row.get("candidate_hash")
            )

        final_search_score = _single_search_score(
            plaintext_idx=local_best_pt,
            scorer_search_runtime=scorer_search_runtime,
            batch_eval_chunk_size=int(batch_eval_chunk_size),
            require_batch_scoring=bool(require_batch_scoring),
        )
        start_summaries.append(
            {
                "start_rank": int(start_rank),
                "lane": "anchor" if int(start_rank) == 1 else "challenger",
                "source": _safe_str(start_row.get("source")),
                "source_rank": _safe_int(start_row.get("source_rank")),
                "candidate_hash": _safe_str(start_row.get("candidate_hash")),
                "selection_bucket": _safe_str(start_row.get("selection_bucket")),
                "selected_by_phaseb_topk_anchor_policy": _safe_int(
                    start_row.get("selected_by_phaseb_topk_anchor_policy")
                ),
                "init_key_idx": list(map(int, start_key)),
                "init_plaintext_idx": list(map(int, start_pt.tolist())),
                "init_score": float(start_score),
                "init_match": float(start_match),
                "init_search_score": (
                    float(init_search_score) if np.isfinite(init_search_score) else None
                ),
                "final_key_idx": list(map(int, local_best_key)),
                "final_plaintext_idx": list(map(int, local_best_pt.tolist())),
                "final_score": float(local_best_score),
                "final_match": float(local_best_match),
                "final_search_score": (
                    float(final_search_score) if np.isfinite(final_search_score) else None
                ),
                "accepts_delta": int(int(phasec_accepts) - int(start_accepts_before)),
                "improves_delta": int(int(phasec_improves) - int(start_improves_before)),
                "evals_delta": int(int(phasec_evals) - int(start_evals_before)),
                "lexical_requests_delta": int(
                    int(lexical_stats.get("requests", 0))
                    - int(lexical_before.get("requests", 0))
                ),
                "lexical_cache_hits_delta": int(
                    int(lexical_stats.get("cache_hits", 0))
                    - int(lexical_before.get("cache_hits", 0))
                ),
                "lexical_cache_misses_delta": int(
                    int(lexical_stats.get("cache_misses", 0))
                    - int(lexical_before.get("cache_misses", 0))
                ),
                "lexical_budget_skips_delta": int(
                    int(lexical_stats.get("budget_skips", 0))
                    - int(lexical_before.get("budget_skips", 0))
                ),
                "lexical_threshold_skips_delta": int(
                    int(lexical_stats.get("threshold_skips", 0))
                    - int(lexical_before.get("threshold_skips", 0))
                ),
                "lexical_tiebreak_decisions_delta": int(
                    int(lexical_stats.get("tiebreak_decisions", 0))
                    - int(lexical_before.get("tiebreak_decisions", 0))
                ),
                "match_gain": (
                    float(local_best_match - start_match)
                    if np.isfinite(local_best_match) and np.isfinite(start_match)
                    else None
                ),
                "score_gain": (
                    float(local_best_score - start_score)
                    if np.isfinite(local_best_score) and np.isfinite(start_score)
                    else None
                ),
                "overtook_anchor": int(overtook_anchor),
                "became_global_best": int(became_global_best),
                "shadow_stop_v1": dict(shadow_state),
            }
        )

    return {
        "replay_label": str(replay_label),
        "fixture_seed": _safe_int(artifact.get("instance_source_key_seed")),
        "search_seed": _safe_int(artifact.get("search_seed")),
        "source_artifact_relpath": _relative_path(case.artifact_path),
        "phasec_seed": int(phasec_seed),
        "phasec_steps": int(steps),
        "phasec_proposals_per_step": int(proposals_per_step),
        "phasec_three_cycle_prob": float(three_cycle_prob),
        "phasec_word_ngram_tiebreak": int(1 if bool(word_ngram_tiebreak) else 0),
        "start_source_counts": _count_source_rows(start_rows),
        "start_identities": _ordered_start_identities(start_rows),
        "pre_phasec_best_candidate_hash": _safe_str(pre_phasec_best_row.get("candidate_hash")),
        "pre_phasec_best_source": _safe_str(pre_phasec_best_row.get("source")),
        "pre_phasec_best_source_rank": _safe_int(pre_phasec_best_row.get("source_rank")),
        "pre_phasec_best_score": float(_safe_float(pre_phasec_best_row.get("init_score"))),
        "pre_phasec_best_match": float(_safe_float(pre_phasec_best_row.get("init_match"))),
        "phasec_evals": int(phasec_evals),
        "phasec_accepts": int(phasec_accepts),
        "phasec_improves": int(phasec_improves),
        "phasec_lexical_requests": int(lexical_stats.get("requests", 0)),
        "phasec_lexical_cache_hits": int(lexical_stats.get("cache_hits", 0)),
        "phasec_lexical_cache_misses": int(lexical_stats.get("cache_misses", 0)),
        "phasec_lexical_budget_skips": int(lexical_stats.get("budget_skips", 0)),
        "phasec_lexical_threshold_skips": int(lexical_stats.get("threshold_skips", 0)),
        "phasec_lexical_tiebreak_decisions": int(
            lexical_stats.get("tiebreak_decisions", 0)
        ),
        "best_match_ratio": float(global_best_match),
        "best_score": float(global_best_score),
        "best_search_score": (
            float(global_best_search_score) if np.isfinite(global_best_search_score) else None
        ),
        "winner_lane": str(phasec_final_winner_lane),
        "winner_source": str(phasec_final_winner_source),
        "winner_source_rank": int(phasec_final_winner_source_rank),
        "winner_candidate_hash": str(phasec_final_winner_candidate_hash),
        "start_summaries": start_summaries,
    }


def build_comparison_summary(
    *,
    case: phasec_replay_mod.ArtifactCase,
    control_summary: Mapping[str, Any],
    candidate_summary: Mapping[str, Any],
) -> dict[str, Any]:
    retained_stage3_reference = retained_mod.extract_retained_stage3_reference(case.artifact)
    retained_stage3_match = _safe_float(retained_stage3_reference.get("match_ratio"))
    control_best_match = _safe_float(control_summary.get("best_match_ratio"))
    candidate_best_match = _safe_float(candidate_summary.get("best_match_ratio"))
    return {
        "run_label": str(RUN_LABEL),
        "source_artifact_relpath": _relative_path(case.artifact_path),
        "fixture_seed": _safe_int(case.artifact.get("instance_source_key_seed")),
        "search_seed": _safe_int(case.artifact.get("search_seed")),
        "retained_stage3_reference_match_ratio": float(retained_stage3_match),
        "retained_stage3_reference_source": _safe_str(
            retained_stage3_reference.get("source")
        ),
        "retained_stage3_reference_stage3_source": _safe_str(
            retained_stage3_reference.get("stage3_source")
        ),
        "retained_stage3_reference_candidate_hash": _safe_str(
            retained_stage3_reference.get("candidate_hash")
        ),
        "control_pre_phasec_best_match": float(
            _safe_float(control_summary.get("pre_phasec_best_match"))
        ),
        "control_best_match_ratio": float(control_best_match),
        "candidate_best_match_ratio": float(candidate_best_match),
        "control_delta_vs_retained_stage3_reference": float(
            control_best_match - retained_stage3_match
        ),
        "candidate_delta_vs_retained_stage3_reference": float(
            candidate_best_match - retained_stage3_match
        ),
        "candidate_minus_control_best_match_ratio": float(
            candidate_best_match - control_best_match
        ),
        "control_winner_lane": _safe_str(control_summary.get("winner_lane")),
        "control_winner_source": _safe_str(control_summary.get("winner_source")),
        "control_winner_source_rank": _safe_int(
            control_summary.get("winner_source_rank")
        ),
        "control_winner_candidate_hash": _safe_str(
            control_summary.get("winner_candidate_hash")
        ),
        "candidate_winner_lane": _safe_str(candidate_summary.get("winner_lane")),
        "candidate_winner_source": _safe_str(candidate_summary.get("winner_source")),
        "candidate_winner_source_rank": _safe_int(
            candidate_summary.get("winner_source_rank")
        ),
        "candidate_winner_candidate_hash": _safe_str(
            candidate_summary.get("winner_candidate_hash")
        ),
        "control_start_hashes": [
            _safe_str(row.get("candidate_hash"))
            for row in list(control_summary.get("start_identities", []) or [])
        ],
        "candidate_start_hashes": [
            _safe_str(row.get("candidate_hash"))
            for row in list(candidate_summary.get("start_identities", []) or [])
        ],
        "candidate_reordered_surface": int(
            list(control_summary.get("start_identities", []) or [])
            != list(candidate_summary.get("start_identities", []) or [])
        ),
        "control_phasec_evals": _safe_int(control_summary.get("phasec_evals")),
        "candidate_phasec_evals": _safe_int(candidate_summary.get("phasec_evals")),
    }


def write_markdown(
    output_dir: Path,
    *,
    comparison_summary: Mapping[str, Any],
    control_summary: Mapping[str, Any],
    candidate_summary: Mapping[str, Any],
) -> None:
    fixture_seed = _safe_int(comparison_summary.get("fixture_seed"))
    search_seed = _safe_int(comparison_summary.get("search_seed"))
    lines = [
        f"# Candidate 3 Saved-Surface Exact Replay: {fixture_seed} / search{search_seed}",
        "",
        "Question:",
        (
            f"- if Phase C starts from the exact retained saved start surface for "
            f"`{fixture_seed}/search{search_seed}`, does candidate3 improve on "
            "the saved-surface control without Phase-A/Phase-B replay drift in "
            "front of it?"
        ),
        "",
        "Top-line read:",
        f"- source artifact: `{comparison_summary.get('source_artifact_relpath')}`",
        (
            "- retained Stage-3 reference: "
            f"`{comparison_summary.get('retained_stage3_reference_source')}` / "
            f"`{comparison_summary.get('retained_stage3_reference_stage3_source')}` / "
            f"`{float(comparison_summary.get('retained_stage3_reference_match_ratio', float('nan'))):.3f}`"
        ),
        (
            "- saved-surface control best: "
            f"`{float(comparison_summary.get('control_best_match_ratio', float('nan'))):.3f}` "
            f"(delta `{float(comparison_summary.get('control_delta_vs_retained_stage3_reference', float('nan'))):.3f}`)"
        ),
        (
            "- saved-surface candidate best: "
            f"`{float(comparison_summary.get('candidate_best_match_ratio', float('nan'))):.3f}` "
            f"(delta `{float(comparison_summary.get('candidate_delta_vs_retained_stage3_reference', float('nan'))):.3f}`)"
        ),
        (
            "- candidate minus control: "
            f"`{float(comparison_summary.get('candidate_minus_control_best_match_ratio', float('nan'))):.3f}`"
        ),
        f"- reordered start surface: `{int(comparison_summary.get('candidate_reordered_surface', 0) or 0)}`",
        "",
        "Winner comparison:",
        f"- control winner: `{comparison_summary.get('control_winner_lane')}` / `{comparison_summary.get('control_winner_source')}` / rank `{comparison_summary.get('control_winner_source_rank')}` / `{comparison_summary.get('control_winner_candidate_hash')}`",
        f"- candidate winner: `{comparison_summary.get('candidate_winner_lane')}` / `{comparison_summary.get('candidate_winner_source')}` / rank `{comparison_summary.get('candidate_winner_source_rank')}` / `{comparison_summary.get('candidate_winner_candidate_hash')}`",
        "",
        "Control start ordering:",
        "",
        "| rank | lane | source | source_rank | candidate_hash | init_match | init_score |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in list(control_summary.get("start_identities", []) or []):
        lines.append(
            f"| {int(row.get('start_rank', 0) or 0)} | "
            f"{_safe_str(row.get('lane'))} | "
            f"{_safe_str(row.get('source'))} | "
            f"{_safe_int(row.get('source_rank'))} | "
            f"{_safe_str(row.get('candidate_hash'))} | "
            f"{_safe_float(row.get('init_match')):.3f} | "
            f"{_safe_float(row.get('init_score')):.6f} |"
        )
    lines.extend(
        [
            "",
            "Candidate start ordering:",
            "",
            "| rank | lane | source | source_rank | candidate_hash | phaseb_topk_anchor_policy | init_match | init_score |",
            "| --- | --- | --- | --- | --- | --- | --- | --- |",
        ]
    )
    for row in list(candidate_summary.get("start_identities", []) or []):
        lines.append(
            f"| {int(row.get('start_rank', 0) or 0)} | "
            f"{_safe_str(row.get('lane'))} | "
            f"{_safe_str(row.get('source'))} | "
            f"{_safe_int(row.get('source_rank'))} | "
            f"{_safe_str(row.get('candidate_hash'))} | "
            f"{_safe_int(row.get('selected_by_phaseb_topk_anchor_policy'))} | "
            f"{_safe_float(row.get('init_match')):.3f} | "
            f"{_safe_float(row.get('init_score')):.6f} |"
        )
    lines.extend(
        [
            "",
            "Interpretation:",
            "- this helper isolates candidate3 on the exact saved Phase-C starts, so any difference here is candidate ordering plus Phase-C search, not Phase-A/Phase-B reconstruction drift",
            "- if the saved-surface control is still far from the retained Stage-3 reference, then there is still replay drift inside the saved-surface Phase-C lane itself",
        ]
    )
    (output_dir / "candidate3_saved_surface_exact_readout.md").write_text(
        "\n".join(lines).rstrip() + "\n",
        encoding="utf-8",
    )


def run_verification() -> dict[str, Any]:
    output_dir = OUTPUT_BASE_DIR / f"{_utc_label()}__{RUN_LABEL}"
    output_dir.mkdir(parents=True, exist_ok=False)

    case = resume_mod.load_artifact_case(artifact_path=REPO_ROOT / SOURCE_ARTIFACT_REL_PATH)
    saved_rows = _load_saved_start_rows(case.artifact)
    control_rows = _prepare_saved_start_rows(saved_rows)
    candidate_rows = saved_surface_mod.build_candidate3_saved_surface_rows(saved_rows)

    _write_json(
        output_dir / "attempt_manifest.json",
        {
            "run_label": str(RUN_LABEL),
            "source_artifact_relpath": _relative_path(case.artifact_path),
            "source_run_dir_relpath": _relative_path(case.run_dir),
            "scope_note": (
                "saved-surface exact replay uses retained phaseC_start_summaries "
                "directly and supports rescue-disabled cases only"
            ),
            "start_surface_count": int(len(saved_rows)),
        },
    )

    control_summary = run_saved_surface_phasec_replay(
        case=case,
        saved_rows=control_rows,
        replay_label="saved_surface_control",
    )
    candidate_summary = run_saved_surface_phasec_replay(
        case=case,
        saved_rows=candidate_rows,
        replay_label="saved_surface_candidate3",
    )
    comparison_summary = build_comparison_summary(
        case=case,
        control_summary=control_summary,
        candidate_summary=candidate_summary,
    )

    _write_json(output_dir / "control_saved_surface_summary.json", control_summary)
    _write_json(output_dir / "candidate_saved_surface_summary.json", candidate_summary)
    _write_json(output_dir / "comparison_summary.json", comparison_summary)
    _write_json(
        output_dir / "control_saved_surface_start_rows.json",
        list(control_summary.get("start_summaries", []) or []),
    )
    _write_json(
        output_dir / "candidate_saved_surface_start_rows.json",
        list(candidate_summary.get("start_summaries", []) or []),
    )
    write_markdown(
        output_dir,
        comparison_summary=comparison_summary,
        control_summary=control_summary,
        candidate_summary=candidate_summary,
    )

    run_summary = {
        "output_dir": _relative_path(output_dir),
        "source_artifact_relpath": _relative_path(case.artifact_path),
        "fixture_seed": _safe_int(case.artifact.get("instance_source_key_seed")),
        "search_seed": _safe_int(case.artifact.get("search_seed")),
        "retained_stage3_reference_match_ratio": float(
            comparison_summary.get("retained_stage3_reference_match_ratio", float("nan"))
        ),
        "control_best_match_ratio": float(
            comparison_summary.get("control_best_match_ratio", float("nan"))
        ),
        "candidate_best_match_ratio": float(
            comparison_summary.get("candidate_best_match_ratio", float("nan"))
        ),
        "candidate_minus_control_best_match_ratio": float(
            comparison_summary.get("candidate_minus_control_best_match_ratio", float("nan"))
        ),
        "candidate_reordered_surface": _safe_int(
            comparison_summary.get("candidate_reordered_surface")
        ),
    }
    _write_json(output_dir / "run_summary.json", run_summary)
    return run_summary


def main() -> None:
    print(json.dumps(run_verification(), sort_keys=True))


if __name__ == "__main__":
    main()
