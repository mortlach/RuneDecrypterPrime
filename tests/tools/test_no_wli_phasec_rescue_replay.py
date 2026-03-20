from __future__ import annotations

from pathlib import Path

import numpy as np

from tools.benchmarks.periodic_sub_trans.no_wli import (
    replay_phasec_rescue_sweep as replay_mod,
)


class _SliceBinaryCipher:
    def __init__(self, *, base_key: list[int], period: int, alphabet_size: int) -> None:
        self._base = np.asarray(base_key, dtype=np.int16).reshape(-1)
        self._period = int(period)
        self._alphabet_size = int(alphabet_size)

    def decrypt(self, *, ciphertext, key, interrupt_idx=None, interrupt_sym=None):
        _ = interrupt_idx, interrupt_sym
        ct = np.asarray(ciphertext, dtype=np.uint8).reshape(-1)
        key_arr = np.asarray(key, dtype=np.int16)
        if key_arr.ndim == 1:
            key_arr = key_arr[None, :]
        rows = []
        for row in key_arr:
            flags: list[int] = []
            for slice_idx in range(int(self._period)):
                lo = int(slice_idx * self._alphabet_size)
                hi = int(lo + self._alphabet_size)
                changed = int(
                    not np.array_equal(
                        np.asarray(row[lo:hi], dtype=np.int16),
                        self._base[lo:hi],
                    )
                )
                flags.append(changed)
            rows.append(np.asarray(flags[: int(ct.size)], dtype=np.uint8))
        return np.asarray(rows, dtype=np.uint8)


class _FullRewardScorer:
    def batch_score(self, plaintexts, _wli):
        arr = np.asarray(plaintexts, dtype=np.float64)
        if arr.ndim == 1:
            arr = arr[None, :]
        return (10.0 * arr[:, 1]) - arr[:, 0]


class _SearchPenaltyScorer:
    def batch_score(self, plaintexts, _wli):
        arr = np.asarray(plaintexts, dtype=np.float64)
        if arr.ndim == 1:
            arr = arr[None, :]
        return (-0.005 * arr[:, 1]) - (0.001 * arr[:, 0])


class _SlicePermutationCipher:
    def __init__(self, *, period: int, alphabet_size: int) -> None:
        self._period = int(period)
        self._alphabet_size = int(alphabet_size)

    def decrypt(self, *, ciphertext, key, interrupt_idx=None, interrupt_sym=None):
        _ = interrupt_idx, interrupt_sym
        ct = np.asarray(ciphertext, dtype=np.uint8).reshape(-1)
        key_arr = np.asarray(key, dtype=np.int16)
        if key_arr.ndim == 1:
            key_arr = key_arr[None, :]
        rows = []
        for row in key_arr:
            flat: list[int] = []
            for slice_idx in range(int(self._period)):
                lo = int(slice_idx * self._alphabet_size)
                hi = int(lo + self._alphabet_size)
                flat.extend(np.asarray(row[lo:hi], dtype=np.uint8).tolist())
            rows.append(np.asarray(flat[: int(ct.size)], dtype=np.uint8))
        return np.asarray(rows, dtype=np.uint8)


class _PositionalMatchScorer:
    def __init__(self, *, target: list[int]) -> None:
        self._target = np.asarray(target, dtype=np.uint8).reshape(-1)

    def batch_score(self, plaintexts, _wli):
        arr = np.asarray(plaintexts, dtype=np.uint8)
        if arr.ndim == 1:
            arr = arr[None, :]
        target = self._target.reshape(1, -1)
        same = np.sum(arr[:, : target.shape[1]] == target, axis=1)
        return same.astype(np.float64)


def test_select_guard_passing_row_selector_modes_can_diverge() -> None:
    rows = [
        {"key": [0, 1], "score": 10.0, "search_score": 0.0, "lexical_active": 0},
        {
            "key": [1, 0],
            "score": 10.0 - (0.5 * replay_mod.REPLAY_SELECTOR_TOP_SCORE_BAND_EPS),
            "search_score": 1.0,
            "lexical_active": 0,
        },
        {"key": [1, 2], "score": 9.7, "search_score": 0.8, "lexical_active": 0},
    ]

    baseline = replay_mod._select_guard_passing_row(
        passing_rows=rows,
        selector_mode="baseline",
        current_score=9.0,
        current_search_score=0.2,
    )
    top_search = replay_mod._select_guard_passing_row(
        passing_rows=rows,
        selector_mode="top_score_then_search",
        current_score=9.0,
        current_search_score=0.2,
    )
    rescue_shallow = replay_mod._select_guard_passing_row(
        passing_rows=rows,
        selector_mode="rescue_shallow_then_search",
        current_score=9.0,
        current_search_score=0.2,
    )
    lexical = replay_mod._select_guard_passing_row(
        passing_rows=rows,
        selector_mode="score_band_then_lexical_then_search",
        current_score=9.0,
        current_search_score=0.2,
    )
    gain_based = replay_mod._select_guard_passing_row(
        passing_rows=rows,
        selector_mode="gain_based",
        current_score=9.0,
        current_search_score=0.2,
    )
    pareto = replay_mod._select_guard_passing_row(
        passing_rows=rows,
        selector_mode="pareto_shortlist",
        current_score=9.0,
        current_search_score=0.2,
    )

    assert baseline is not None
    assert top_search is not None
    assert rescue_shallow is not None
    assert lexical is not None
    assert gain_based is not None
    assert pareto is not None
    assert list(baseline["key"]) == [0, 1]
    assert list(top_search["key"]) == [1, 0]
    assert list(rescue_shallow["key"]) == [1, 0]
    assert list(lexical["key"]) == [1, 0]
    assert list(gain_based["key"]) == [1, 0]
    assert list(pareto["key"]) == [1, 0]


def test_top_score_then_search_score_band_excludes_lower_score_rows() -> None:
    rows = [
        {"key": [0, 1], "score": 10.0, "search_score": 0.0, "lexical_active": 0},
        {
            "key": [1, 0],
            "score": 10.0 - (2.0 * replay_mod.REPLAY_SELECTOR_TOP_SCORE_BAND_EPS),
            "search_score": 5.0,
            "lexical_active": 1,
            "lexical_trust": 10.0,
        },
    ]

    top_search = replay_mod._select_guard_passing_row(
        passing_rows=rows,
        selector_mode="top_score_then_search",
        current_score=9.0,
        current_search_score=0.2,
    )

    assert top_search is not None
    assert list(top_search["key"]) == [0, 1]


def test_score_band_then_lexical_then_search_prefers_lexical_active_row() -> None:
    rows = [
        {
            "key": [0, 1],
            "score": 10.0,
            "search_score": 0.0,
            "lexical_active": 0,
            "lexical_trust": float("-inf"),
        },
        {
            "key": [1, 0],
            "score": 10.0 - (0.5 * replay_mod.REPLAY_SELECTOR_TOP_SCORE_BAND_EPS),
            "search_score": -0.5,
            "lexical_active": 1,
            "lexical_trust": 3.0,
        },
    ]

    lexical = replay_mod._select_guard_passing_row(
        passing_rows=rows,
        selector_mode="score_band_then_lexical_then_search",
        current_score=9.0,
        current_search_score=0.2,
    )

    assert lexical is not None
    assert list(lexical["key"]) == [1, 0]


def test_rescue_shallow_then_search_prefers_noncurrent_shallower_row() -> None:
    rows = [
        {
            "key": [0, 1],
            "score": 12.0,
            "search_score": 3.0,
            "landing_type": "current",
            "mini_search_step": 0,
        },
        {
            "key": [1, 0],
            "score": 13.0,
            "search_score": 2.5,
            "landing_type": "mini_search",
            "mini_search_step": 2,
        },
        {
            "key": [2, 0],
            "score": 11.5,
            "search_score": 2.0,
            "landing_type": "probe",
            "mini_search_step": 0,
        },
    ]

    selected = replay_mod._select_guard_passing_row(
        passing_rows=rows,
        selector_mode="rescue_shallow_then_search",
        current_score=10.0,
        current_search_score=1.0,
    )

    assert selected is not None
    assert list(selected["key"]) == [2, 0]


def test_build_miss_rows_filters_selector_and_miss_flag() -> None:
    rows = [
        {
            "selector_mode": "top_score_then_search",
            "selector_missed_better_truth": 1,
            "start_idx": 2,
        },
        {
            "selector_mode": "baseline",
            "selector_missed_better_truth": 1,
            "start_idx": 3,
        },
        {
            "selector_mode": "top_score_then_search",
            "selector_missed_better_truth": 0,
            "start_idx": 4,
        },
    ]

    all_misses = replay_mod.build_miss_rows(rows)
    top_search_misses = replay_mod.build_miss_rows(
        rows,
        selector_modes=("top_score_then_search",),
    )

    assert [int(row["start_idx"]) for row in all_misses] == [2, 3]
    assert [int(row["start_idx"]) for row in top_search_misses] == [2]


def test_build_replay_starts_extracts_anchor_and_phaseb_challengers() -> None:
    case = replay_mod.ArtifactCase(
        artifact_path=Path("output/tools/benchmarks/periodic_sub_trans/no_wli/example/final.json"),
        run_dir=Path("output/tools/benchmarks/periodic_sub_trans/no_wli/example"),
        run_config_path=Path("output/tools/benchmarks/periodic_sub_trans/no_wli/example/run_config.json"),
        artifact={
            "stage3_topk": [
                {"rank": 1, "source": "phaseB_topk", "end_hash": "h1", "key_idx": [0, 1, 2, 0, 1, 2, 0], "plaintext_idx": [0, 0]},
                {"rank": 2, "source": "phaseB_topk", "end_hash": "h2", "key_idx": [1, 0, 2, 0, 1, 2, 0], "plaintext_idx": [1, 0]},
                {"rank": 3, "source": "phaseB_topk", "end_hash": "h3", "key_idx": [0, 1, 2, 1, 2, 0, 0], "plaintext_idx": [0, 1]},
            ],
            "stage3_diagnostics": {
                "phaseC_start_summaries": [
                    {"start_idx": 1, "lane": "anchor", "source": "stage3_best_phaseB", "source_rank": 1, "candidate_hash": "h1", "init_match": 0.60, "init_score": 1.0, "init_search_score": 0.4},
                    {"start_idx": 2, "lane": "challenger", "source": "phaseB_topk", "source_rank": 2, "candidate_hash": "h2", "init_match": 0.50, "init_score": 0.8, "init_search_score": 0.3},
                    {"start_idx": 3, "lane": "challenger", "source": "phaseA_selected", "source_rank": 1, "candidate_hash": "ha", "init_match": 0.40, "init_score": 0.7, "init_search_score": 0.2},
                    {"start_idx": 4, "lane": "challenger", "source": "phaseB_topk", "source_rank": 3, "candidate_hash": "h3", "init_match": 0.55, "init_score": 0.9, "init_search_score": 0.25},
                ]
            },
        },
        run_config={},
    )

    out = replay_mod.build_replay_starts(case)

    anchor = out["anchor_start"]
    challengers = list(out["challenger_starts"])
    assert anchor is not None
    assert str(anchor.candidate_hash) == "h1"
    assert int(anchor.start_idx) == 1
    assert len(challengers) == 2
    assert [int(row.start_idx) for row in challengers] == [2, 4]
    assert [int(row.source_rank) for row in challengers] == [2, 3]
    assert [str(row.candidate_hash) for row in challengers] == ["h2", "h3"]


def test_build_replay_starts_infers_anchor_without_lane_field() -> None:
    case = replay_mod.ArtifactCase(
        artifact_path=Path("output/tools/benchmarks/periodic_sub_trans/no_wli/example/final.json"),
        run_dir=Path("output/tools/benchmarks/periodic_sub_trans/no_wli/example"),
        run_config_path=Path("output/tools/benchmarks/periodic_sub_trans/no_wli/example/run_config.json"),
        artifact={
            "stage3_topk": [
                {"rank": 1, "source": "phaseB_topk", "end_hash": "h1", "key_idx": [0, 1, 2, 0, 1, 2, 0], "plaintext_idx": [0, 0]},
                {"rank": 2, "source": "phaseB_topk", "end_hash": "h2", "key_idx": [1, 0, 2, 0, 1, 2, 0], "plaintext_idx": [1, 0]},
            ],
            "stage3_diagnostics": {
                "phaseC_start_summaries": [
                    {"start_idx": 1, "source": "stage3_best_phaseB", "source_rank": 1, "candidate_hash": "h1", "init_match": 0.60, "init_score": 1.0},
                    {"start_idx": 2, "source": "phaseB_topk", "source_rank": 2, "candidate_hash": "h2", "init_match": 0.50, "init_score": 0.8},
                ]
            },
        },
        run_config={},
    )

    out = replay_mod.build_replay_starts(case)

    anchor = out["anchor_start"]
    warnings = list(out["warnings"])
    assert anchor is not None
    assert int(anchor.start_idx) == 1
    assert str(anchor.lane) == "anchor"
    assert any("inferred anchor summary" in warning for warning in warnings)


def test_replay_rescue_for_start_sweeps_guard_threshold() -> None:
    base_key = [0, 1, 2, 0, 1, 2, 0]
    start = replay_mod.ReplayStart(
        artifact_relpath="output/tools/benchmarks/periodic_sub_trans/no_wli/example/final.json",
        run_id="run_example",
        start_idx=2,
        lane="challenger",
        source="phaseB_topk",
        source_rank=2,
        candidate_hash="h2",
        key_idx=tuple(base_key),
        plaintext_idx=(0, 0),
        init_match=0.5,
        init_score=0.0,
        init_search_score=0.0,
        live_rescue_attempted=0,
        live_rescue_applied=0,
        live_rescue_guard_search_passed=0,
        live_rescue_target_slice=None,
        live_overtook_anchor=0,
        live_became_global_best=0,
    )
    anchor = replay_mod.ReplayStart(
        artifact_relpath="output/tools/benchmarks/periodic_sub_trans/no_wli/example/final.json",
        run_id="run_example",
        start_idx=1,
        lane="anchor",
        source="stage3_best_phaseB",
        source_rank=1,
        candidate_hash="h1",
        key_idx=tuple(base_key),
        plaintext_idx=(0, 0),
        init_match=0.5,
        init_score=0.0,
        init_search_score=0.0,
        live_rescue_attempted=0,
        live_rescue_applied=0,
        live_rescue_guard_search_passed=0,
        live_rescue_target_slice=None,
        live_overtook_anchor=0,
        live_became_global_best=0,
    )
    rows = replay_mod.replay_rescue_for_start(
        start=start,
        artifact={
            "period": 2,
            "alphabet_size": 3,
            "ciphertext_idx": [0, 0],
            "target_plaintext_idx": [0, 1],
            "best_match_ratio": 0.5,
            "best_score": 0.0,
        },
        phase_seed=2026,
        rescue_candidates=0,
        rescue_slip_swaps=1,
        guard_max_drop_values=[0.0, 0.01],
        scorer_full=_FullRewardScorer(),
        scorer_search=_SearchPenaltyScorer(),
        scorer_word_ngram_report=None,
        cipher=_SliceBinaryCipher(base_key=base_key, period=2, alphabet_size=3),
        chunk_size=8,
        require_batch=True,
        anchor_start=anchor,
    )

    assert len(rows) == 2 * len(replay_mod.REPLAY_SELECTOR_MODES)
    rows_by_mode_guard = {
        (str(row["selector_mode"]), float(row["guard_max_drop"])): row for row in rows
    }
    strict_row = rows_by_mode_guard[("baseline", 0.0)]
    loose_row = rows_by_mode_guard[("baseline", 0.01)]

    assert int(strict_row["guard_pass_start"]) == 0
    assert int(strict_row["rescue_applied"]) == 0
    assert int(strict_row["truth_match_improved"]) == 0
    assert int(strict_row["guard_reject_candidate_count"]) >= 1
    assert float(strict_row["guard_threshold_needed_for_any_pass"]) >= 0.005

    assert int(loose_row["guard_pass_start"]) == 1
    assert int(loose_row["rescue_applied"]) == 1
    assert int(loose_row["truth_match_improved"]) == 1
    assert int(loose_row["overtook_anchor_init"]) == 1
    assert float(loose_row["search_score_gain"]) < 0.0
    assert float(loose_row["probe_search_score_gain"]) <= -0.005
    assert str(loose_row["landing_type"]) in {"probe", "mini_search"}

    summary_rows = replay_mod.summarize_replay_rows(rows)
    summary_by_mode_guard = {
        (str(row["selector_mode"]), float(row["guard_max_drop"])): row
        for row in summary_rows
    }
    assert int(summary_by_mode_guard[("baseline", 0.0)]["rescue_applied_count"]) == 0
    assert int(summary_by_mode_guard[("baseline", 0.01)]["rescue_applied_count"]) == 1
    assert int(
        summary_by_mode_guard[("baseline", 0.01)]["truth_match_improved_count"]
    ) == 1


def test_replay_rescue_for_start_without_anchor_does_not_report_overtake() -> None:
    base_key = [0, 1, 2, 0, 1, 2, 0]
    start = replay_mod.ReplayStart(
        artifact_relpath="output/tools/benchmarks/periodic_sub_trans/no_wli/example/final.json",
        run_id="run_example",
        start_idx=2,
        lane="challenger",
        source="phaseB_topk",
        source_rank=2,
        candidate_hash="h2",
        key_idx=tuple(base_key),
        plaintext_idx=(0, 0),
        init_match=0.5,
        init_score=0.0,
        init_search_score=0.0,
        live_rescue_attempted=0,
        live_rescue_applied=0,
        live_rescue_guard_search_passed=0,
        live_rescue_target_slice=None,
        live_overtook_anchor=0,
        live_became_global_best=0,
    )

    rows = replay_mod.replay_rescue_for_start(
        start=start,
        artifact={
            "period": 2,
            "alphabet_size": 3,
            "ciphertext_idx": [0, 0],
            "target_plaintext_idx": [0, 1],
            "best_match_ratio": 0.5,
            "best_score": 0.0,
        },
        phase_seed=2026,
        rescue_candidates=0,
        rescue_slip_swaps=1,
        guard_max_drop_values=[0.01],
        scorer_full=_FullRewardScorer(),
        scorer_search=_SearchPenaltyScorer(),
        scorer_word_ngram_report=None,
        cipher=_SliceBinaryCipher(base_key=base_key, period=2, alphabet_size=3),
        chunk_size=8,
        require_batch=True,
        anchor_start=None,
    )

    assert len(rows) == len(replay_mod.REPLAY_SELECTOR_MODES)
    for row in rows:
        assert int(row["anchor_available"]) == 0
        assert int(row["overtook_anchor_init"]) == 0

    summary_rows = replay_mod.summarize_replay_rows(rows)
    assert len(summary_rows) == len(replay_mod.REPLAY_SELECTOR_MODES)
    for row in summary_rows:
        assert int(row["anchor_available_start_count"]) == 0
        assert int(row["overtook_anchor_init_count"]) == 0


def test_replay_rescue_mini_search_can_find_two_swap_slice_repair() -> None:
    current_key = [0, 1, 2, 3, 0, 1, 2, 3]
    target_pt = [0, 1, 2, 3, 2, 0, 1, 3]
    start = replay_mod.ReplayStart(
        artifact_relpath="output/tools/benchmarks/periodic_sub_trans/no_wli/example/final.json",
        run_id="run_example",
        start_idx=2,
        lane="challenger",
        source="phaseB_topk",
        source_rank=2,
        candidate_hash="h2",
        key_idx=tuple(current_key),
        plaintext_idx=tuple(current_key),
        init_match=5.0 / 8.0,
        init_score=5.0,
        init_search_score=5.0,
        live_rescue_attempted=0,
        live_rescue_applied=0,
        live_rescue_guard_search_passed=0,
        live_rescue_target_slice=None,
        live_overtook_anchor=0,
        live_became_global_best=0,
    )
    anchor = replay_mod.ReplayStart(
        artifact_relpath="output/tools/benchmarks/periodic_sub_trans/no_wli/example/final.json",
        run_id="run_example",
        start_idx=1,
        lane="anchor",
        source="stage3_best_phaseB",
        source_rank=1,
        candidate_hash="h1",
        key_idx=tuple(current_key),
        plaintext_idx=tuple(current_key),
        init_match=5.0 / 8.0,
        init_score=5.0,
        init_search_score=5.0,
        live_rescue_attempted=0,
        live_rescue_applied=0,
        live_rescue_guard_search_passed=0,
        live_rescue_target_slice=None,
        live_overtook_anchor=0,
        live_became_global_best=0,
    )

    rows = replay_mod.replay_rescue_for_start(
        start=start,
        artifact={
            "period": 2,
            "alphabet_size": 4,
            "ciphertext_idx": [0, 1, 2, 3, 0, 1, 2, 3],
            "target_plaintext_idx": target_pt,
            "best_match_ratio": 5.0 / 8.0,
            "best_score": 5.0,
        },
        phase_seed=2026,
        rescue_candidates=0,
        rescue_slip_swaps=1,
        guard_max_drop_values=[0.0],
        scorer_full=_PositionalMatchScorer(target=target_pt),
        scorer_search=_PositionalMatchScorer(target=target_pt),
        scorer_word_ngram_report=None,
        cipher=_SlicePermutationCipher(period=2, alphabet_size=4),
        chunk_size=32,
        require_batch=True,
        anchor_start=anchor,
    )

    assert len(rows) == len(replay_mod.REPLAY_SELECTOR_MODES)
    for row in rows:
        assert int(row["guard_pass_start"]) == 1
        assert int(row["rescue_applied"]) == 1
        assert int(row["truth_match_improved"]) == 1
        if str(row["selector_mode"]) == "rescue_shallow_then_search":
            assert str(row["landing_type"]) == "probe"
            assert int(row["landing_mini_search_step"]) == 0
            assert float(row["landing_match"]) == 0.75
            assert float(row["landing_score"]) == 6.0
            assert int(row["landing_matches_mini_search_truth_best"]) == 0
            assert int(row["landing_matches_best_guard_truth"]) == 0
            assert int(row["selector_missed_better_truth"]) == 1
            assert float(row["selector_truth_regret"]) == 0.25
        else:
            assert str(row["landing_type"]) == "mini_search"
            assert int(row["landing_matches_mini_search_truth_best"]) == 1
            assert int(row["landing_matches_best_guard_truth"]) == 1
            assert int(row["selector_missed_better_truth"]) == 0
            assert float(row["selector_truth_regret"]) == 0.0
            assert int(row["landing_mini_search_step"]) == 1
            assert str(row["landing_mini_search_parent_type"]) == "probe_seed"
            assert int(row["landing_mini_search_swap_a"]) in {0, 1, 2}
            assert int(row["landing_mini_search_swap_b"]) in {1, 2, 3}
            assert float(row["landing_match"]) == 1.0
            assert float(row["landing_score"]) == 8.0
        assert float(row["mini_search_truth_best_match"]) == 1.0
        assert float(row["mini_search_truth_best_gain"]) == 3.0 / 8.0
        assert int(row["best_guard_truth_available"]) == 1
        assert float(row["best_guard_truth_match_gain"]) == 3.0 / 8.0
        assert float(row["best_guard_truth_score_gain"]) == 3.0
        assert float(row["best_guard_truth_search_score_gain"]) == 3.0
        assert str(row["best_guard_truth_landing_type"]) == "mini_search"
        assert int(row["best_guard_truth_mini_search_step"]) == 1
        assert str(row["best_guard_truth_mini_search_parent_type"]) == "probe_seed"
        assert int(row["mini_search_pool_row_count"]) >= 1
        assert int(row["overtook_anchor_init"]) == 1
