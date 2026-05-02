from __future__ import annotations

import json
from types import SimpleNamespace

import numpy as np
import pytest

from tools.benchmarks.periodic_sub_trans.no_wli import runner as no_wli_runner
from tools.benchmarks.periodic_sub_trans.no_wli import stage3_two_phase as phase2_mod


pytestmark = pytest.mark.tier_a


def test_build_phasea_gate_snapshot_summarizes_rank1_and_family_state() -> None:
    snapshot = phase2_mod.build_phasea_gate_snapshot(
        tier_name="fixture_fixture_001_p9_c3_l1000",
        text_id=0,
        key_seed=7004,
        phaseA_rows=[
            {"end_hash": "h0"},
            {"end_hash": "h1"},
            {"end_hash": "h2"},
        ],
        phaseA_selected_rows=[
            {
                "source": "phaseA_selected",
                "source_rank": 1,
                "end_hash": "h1",
                "init_match": 0.415,
                "final_match": 0.432,
                "score_gain": 0.012,
                "shadow_stop_v1": {"plateau_would_stop": 0},
            },
            {
                "source": "phaseA_selected",
                "source_rank": 2,
                "end_hash": "h2",
                "init_match": 0.490,
                "final_match": 0.476,
                "score_gain": 0.008,
                "shadow_stop_v1": {"plateau_would_stop": 1},
            },
        ],
        gate_delta=0.003,
        gate_end_gain=0.001,
        phaseB_ran=1,
        phaseB_ready_reason="passed",
        phaseB_top_n_used=2,
        phaseB_selected_unique_end_hash=2,
        phaseB_family_preservation_policy="selected_family_low_edge_eps_0p016_v1",
        phaseB_family_view_id="prefix_hamming_le_24",
        phaseB_family_reserved_slots=1,
        phaseB_family_count_in_top_band=2,
        phaseB_family_preserved_count=1,
        phaseB_family_reservation_applied=1,
        phaseB_downstream_selected_count=3,
        phaseB_downstream_selected_unique_end_hash=3,
    )

    assert snapshot["tier_name"] == "fixture_fixture_001_p9_c3_l1000"
    assert int(snapshot["phaseA_rows_scored"]) == 3
    assert int(snapshot["phaseA_selected_count"]) == 2
    assert float(snapshot["phaseA_rank1_init_match"]) == pytest.approx(0.415)
    assert float(snapshot["phaseA_rank1_final_match"]) == pytest.approx(0.432)
    assert int(snapshot["phaseA_rank1_plateau_would_stop"]) == 0
    assert float(snapshot["phaseA_best_init_match"]) == pytest.approx(0.490)
    assert int(snapshot["phaseA_best_init_source_rank"]) == 2
    assert float(snapshot["phaseA_best_final_match"]) == pytest.approx(0.476)
    assert int(snapshot["phaseA_best_final_source_rank"]) == 2
    assert str(snapshot["phaseB_ready_reason"]) == "passed"
    assert int(snapshot["phaseB_family_reservation_applied"]) == 1
    assert int(snapshot["phaseB_downstream_selected_count"]) == 3


def test_build_phasea_gate_snapshot_backfills_from_phasea_row_schema() -> None:
    snapshot = phase2_mod.build_phasea_gate_snapshot(
        tier_name="fixture_fixture_001_p9_c3_l1000",
        text_id=0,
        key_seed=7004,
        phaseA_rows=[
            {"end_hash": "h0"},
            {"end_hash": "h1"},
        ],
        phaseA_selected_rows=[
            {
                "phaseb_rank": 1,
                "selection_bucket": "legacy_fill",
                "candidate_hash": "h1",
                "end_match": 0.415,
                "best_delta_pct": 0.005,
                "shadow_stop_v1": {"plateau_would_stop": 1},
            },
            {
                "phaseb_rank": 2,
                "candidate_hash": "h2",
                "end_match": 0.490,
                "best_delta_pct": 0.003,
                "shadow_stop_v1": {"plateau_would_stop": 0},
            },
        ],
        gate_delta=0.003,
        gate_end_gain=0.001,
        phaseB_ran=1,
        phaseB_ready_reason="passed",
        phaseB_top_n_used=2,
        phaseB_selected_unique_end_hash=2,
        phaseB_family_preservation_policy="off",
        phaseB_family_view_id="prefix_hamming_le_24",
        phaseB_family_reserved_slots=0,
        phaseB_family_count_in_top_band=2,
        phaseB_family_preserved_count=2,
        phaseB_family_reservation_applied=0,
        phaseB_downstream_selected_count=2,
        phaseB_downstream_selected_unique_end_hash=2,
    )

    assert str(snapshot["phaseA_rank1_source"]) == "legacy_fill"
    assert int(snapshot["phaseA_rank1_source_rank"]) == 1
    assert float(snapshot["phaseA_rank1_init_match"]) == pytest.approx(0.415)
    assert float(snapshot["phaseA_rank1_final_match"]) == pytest.approx(0.415)
    assert float(snapshot["phaseA_rank1_score_gain"]) == pytest.approx(0.005)
    assert int(snapshot["phaseA_rank1_plateau_would_stop"]) == 1
    assert float(snapshot["phaseA_best_init_match"]) == pytest.approx(0.490)
    assert float(snapshot["phaseA_best_final_match"]) == pytest.approx(0.490)
    assert int(snapshot["phaseA_best_init_source_rank"]) == 2
    assert int(snapshot["phaseA_best_final_source_rank"]) == 2


def test_build_phasea_provisional_gate_snapshot_emits_checkpoint_fields() -> None:
    snapshot = phase2_mod.build_phasea_provisional_gate_snapshot(
        tier_name="fixture_fixture_001_p9_c3_l1000",
        text_id=0,
        key_seed=7002,
        key_len=4,
        phaseA_rows=[
            {
                "restart_idx": 0,
                "start_hash": "s0",
                "end_hash": "h0",
                "end_key": [0, 1, 2, 3],
                "end_score_pct": 0.289,
                "best_delta_pct": 0.004,
                "end_score_raw": 0.1,
                "end_match": 0.289,
            },
            {
                "restart_idx": 1,
                "start_hash": "s1",
                "end_hash": "h1",
                "end_key": [3, 2, 1, 0],
                "end_score_pct": 0.309,
                "best_delta_pct": 0.003,
                "end_score_raw": 0.09,
                "end_match": 0.309,
            },
        ],
        phaseA_checkpoint_restart_count=16,
        phaseA_checkpoint_restart_total=64,
        phaseA_checkpoint_elapsed_seconds=320.0,
        stage3_phaseB_top_n=1,
        stage3_span_basin_judge_tie_eps=0.0,
        stage3_span_basin_judge_tie_max_seeds=1,
        stage3_word_ngram_decision_influence=False,
        phaseB_family_preservation_policy="off",
        phaseB_family_view_id="prefix_hamming_le_24",
        phaseB_family_reserved_slots=0,
        gate_delta=0.003,
        gate_end_gain=0.001,
    )

    assert str(snapshot["event"]) == "stage3_phasea_provisional_gate_snapshot"
    assert int(snapshot["phaseA_checkpoint_restart_count"]) == 16
    assert int(snapshot["phaseA_checkpoint_restart_total"]) == 64
    assert float(snapshot["phaseA_checkpoint_fraction"]) == pytest.approx(0.25)
    assert float(snapshot["phaseA_checkpoint_elapsed_seconds"]) == pytest.approx(320.0)
    assert float(snapshot["phaseA_rank1_init_match"]) == pytest.approx(0.309)
    assert float(snapshot["phaseA_best_final_match"]) == pytest.approx(0.309)


def test_no_wli_run_config_includes_stage3_phasec_block() -> None:
    state = dict(no_wli_runner.__dict__)
    state["STAGE3_PHASEC_ENABLED"] = True
    state["STAGE3_PHASEC_CFG"] = {"steps": 21, "proposals_per_step": 11, "three_cycle_prob": 0.2}
    state["STAGE3_PHASEC_START_KEYS"] = 9
    state["STAGE3_PHASEC_SEED_OFFSET"] = 12345
    state["STAGE3_PHASEC_WORD_NGRAM_TIEBREAK"] = True
    state["STAGE3_PHASEC_START_POLICY"] = "balanced_sources_v1"
    state["STAGE35_ENABLED"] = True
    state["STAGE35_CFG"] = {
        "seed_keep": 4,
        "beam_width": 4,
        "archive_keep": 16,
        "rounds": 3,
        "mini_search_steps": 2,
        "mini_search_beam_width": 3,
        "mini_search_top_symbols": 10,
        "mini_search_final_keep": 2,
    }

    cfg = no_wli_runner._build_run_config_external(
        state=state,
        mode_canonical="adaptive_focus_v1",
        mode_raw="adaptive_focus_v1",
        mode_intent="focus",
        stage3_can_skip=False,
        scoring_experiment_meta={"profile": "off", "enabled": False},
        root=no_wli_runner._repo_root(),
        direction=no_wli_runner.Direction.LTR,
        autoskip_effective=False,
        proven_known=0,
        oracle_mode="off",
        oracle_decision_paths_enabled=False,
        oracle_assist_selection_effective=False,
        is_adaptive_focus_mode_fn=no_wli_runner._is_adaptive_focus_mode,
        scorer_cfg_for_output_fn=no_wli_runner._scorer_cfg_for_output,
        stage3_search_cfg_fn=no_wli_runner._stage3_char4_avg_fulltext_search_cfg,
        scoring_meta_for_output_fn=no_wli_runner._scoring_meta_for_output,
        build_no_wli_order_dispatch_payload_fn=no_wli_runner._build_no_wli_order_dispatch_payload,
    )

    phase_c = cfg["stage3"]["two_phase"]["phase_c"]
    stage35 = cfg["stage3"]["stage35"]
    artifacts_cfg = cfg["artifacts"]
    assert phase_c["enabled"] is True
    assert int(phase_c["start_keys"]) == 9
    assert int(phase_c["seed_offset"]) == 12345
    assert bool(phase_c["word_ngram_tiebreak"]) is True
    assert str(phase_c["start_policy"]) == "balanced_sources_v1"
    assert dict(phase_c["cfg"]) == {
        "steps": 21,
        "proposals_per_step": 11,
        "three_cycle_prob": 0.2,
    }
    assert bool(stage35["enabled"]) is True
    assert dict(stage35["cfg"]) == {
        "seed_keep": 4,
        "beam_width": 4,
        "archive_keep": 16,
        "rounds": 3,
        "mini_search_steps": 2,
        "mini_search_beam_width": 3,
        "mini_search_top_symbols": 10,
        "mini_search_final_keep": 2,
    }
    assert bool(artifacts_cfg["resume_handoffs_enabled"]) is True


class _DummyCipher:
    def decrypt(
        self,
        *,
        ciphertext: np.ndarray,
        key: np.ndarray,
        interrupt_idx=None,
        interrupt_sym=None,
    ) -> np.ndarray:
        _ = ciphertext, interrupt_idx, interrupt_sym
        key_arr = np.asarray(key, dtype=np.int16)
        if key_arr.ndim == 1:
            key_arr = key_arr[None, :]
        rows = []
        for row in key_arr:
            rows.append(np.asarray([row[0], row[1], row[2], row[3]], dtype=np.uint8))
        return np.asarray(rows, dtype=np.uint8)

    def decrypt_idx(self, ciphertext, key):
        _ = ciphertext
        row = np.asarray(key, dtype=np.int16).reshape(-1)
        return [int(row[0]), int(row[1]), int(row[2]), int(row[3])]


class _InterleavedSliceCipher:
    def __init__(self, *, period: int, alphabet_size: int, plaintext_len: int) -> None:
        self._period = int(period)
        self._alphabet_size = int(alphabet_size)
        self._plaintext_len = int(plaintext_len)

    def decrypt(
        self,
        *,
        ciphertext: np.ndarray,
        key: np.ndarray,
        interrupt_idx=None,
        interrupt_sym=None,
    ) -> np.ndarray:
        _ = ciphertext, interrupt_idx, interrupt_sym
        key_arr = np.asarray(key, dtype=np.int16)
        if key_arr.ndim == 1:
            key_arr = key_arr[None, :]
        rows = []
        for row in key_arr:
            pt = []
            for pos in range(int(self._plaintext_len)):
                phase_i = int(pos % int(self._period))
                within_i = int(pos // int(self._period))
                key_idx = int(phase_i * int(self._alphabet_size) + within_i)
                pt.append(int(row[key_idx]))
            rows.append(np.asarray(pt, dtype=np.uint8))
        return np.asarray(rows, dtype=np.uint8)

    def decrypt_idx(self, ciphertext, key):
        _ = ciphertext
        row = np.asarray(key, dtype=np.int16).reshape(-1)
        pt = []
        for pos in range(int(self._plaintext_len)):
            phase_i = int(pos % int(self._period))
            within_i = int(pos // int(self._period))
            key_idx = int(phase_i * int(self._alphabet_size) + within_i)
            pt.append(int(row[key_idx]))
        return pt


class _SliceChangeCipher:
    def __init__(
        self,
        *,
        base_key: list[int],
        period: int,
        alphabet_size: int,
    ) -> None:
        self._base = list(map(int, base_key))
        self._period = int(period)
        self._alphabet_size = int(alphabet_size)

    def decrypt(
        self,
        *,
        ciphertext: np.ndarray,
        key: np.ndarray,
        interrupt_idx=None,
        interrupt_sym=None,
    ) -> np.ndarray:
        _ = ciphertext, interrupt_idx, interrupt_sym
        key_arr = np.asarray(key, dtype=np.int16)
        if key_arr.ndim == 1:
            key_arr = key_arr[None, :]
        rows = []
        for row in key_arr:
            pt = []
            for slice_idx in range(int(self._period)):
                lo = int(slice_idx * int(self._alphabet_size))
                hi = int(lo + int(self._alphabet_size))
                changed = int(
                    tuple(map(int, row[lo:hi])) != tuple(self._base[lo:hi])
                )
                pt.append(changed)
            rows.append(np.asarray(pt, dtype=np.uint8))
        return np.asarray(rows, dtype=np.uint8)

    def decrypt_idx(self, ciphertext, key):
        _ = ciphertext
        row = np.asarray(key, dtype=np.int16).reshape(-1)
        pt = []
        for slice_idx in range(int(self._period)):
            lo = int(slice_idx * int(self._alphabet_size))
            hi = int(lo + int(self._alphabet_size))
            changed = int(
                tuple(map(int, row[lo:hi])) != tuple(self._base[lo:hi])
            )
            pt.append(changed)
        return pt


class _TargetScorer:
    def __init__(self, target: list[int]) -> None:
        self._target = np.asarray(target, dtype=np.float64).reshape(1, -1)

    def batch_score(self, plaintexts: np.ndarray, wli) -> np.ndarray:
        _ = wli
        arr = np.asarray(plaintexts, dtype=np.float64)
        return -np.sum(np.abs(arr - self._target), axis=1)


class _ConstantScorer:
    def batch_score(self, plaintexts: np.ndarray, wli) -> np.ndarray:
        _ = wli
        arr = np.asarray(plaintexts, dtype=np.float64)
        if arr.ndim == 1:
            arr = arr[None, :]
        return np.zeros((arr.shape[0],), dtype=np.float64)


class _MeanPenaltyScorer:
    def batch_score(self, plaintexts: np.ndarray, wli) -> np.ndarray:
        _ = wli
        arr = np.asarray(plaintexts, dtype=np.float64)
        if arr.ndim == 1:
            arr = arr[None, :]
        return -np.mean(arr, axis=1)


class _SlicePreferenceScorer:
    def batch_score(self, plaintexts: np.ndarray, wli) -> np.ndarray:
        _ = wli
        arr = np.asarray(plaintexts, dtype=np.float64)
        if arr.ndim == 1:
            arr = arr[None, :]
        # Reward changes in slice 1 much more than slice 0.
        return (10.0 * arr[:, 1]) - (1.0 * arr[:, 0])


class _LexicalReportScorer:
    def __init__(self) -> None:
        self.calls = 0
        self._last_stats = {
            "word_ngram_judge_active": False,
            "word_ngram_judge_trust_score": float("-inf"),
            "word_ngram_judge_report_xent": float("nan"),
        }

    def batch_score(self, plaintexts: np.ndarray, wli) -> np.ndarray:
        _ = wli
        arr = np.asarray(plaintexts, dtype=np.uint8)
        if arr.ndim == 1:
            arr = arr[None, :]
        self.calls += int(arr.shape[0])
        probe = arr[0]
        trust = float(int(probe[0]))
        self._last_stats = {
            "word_ngram_judge_active": True,
            "word_ngram_judge_trust_score": trust,
            "word_ngram_judge_report_xent": float(10.0 - trust),
        }
        return np.zeros((arr.shape[0],), dtype=np.float64)

    def last_stats(self) -> dict[str, float | bool]:
        return dict(self._last_stats)


def _match_ratio(lhs: list[int], rhs: list[int]) -> float:
    if not rhs:
        return float("nan")
    same = sum(1 for a, b in zip(lhs, rhs) if int(a) == int(b))
    return float(same) / float(len(rhs))


def _is_better(
    cand_score: float,
    cand_match: float,
    best_score: float,
    best_match: float,
    *,
    score_first: bool,
) -> bool:
    if np.isfinite(cand_match) and np.isfinite(best_match):
        if float(cand_match) != float(best_match):
            return float(cand_match) > float(best_match)
    if np.isfinite(cand_score) and np.isfinite(best_score):
        if float(cand_score) != float(best_score):
            return float(cand_score) > float(best_score)
    if score_first and np.isfinite(cand_score) and (not np.isfinite(best_score)):
        return True
    return False


def _append_jsonl_test(path, row) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(dict(row), sort_keys=True, ensure_ascii=True) + "\n")


def test_stage3_phasec_can_repair_near_solution(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def _fake_run(**kwargs):
        init_keys = list(kwargs.get("initial_keys", []))
        key = list(map(int, init_keys[0])) if init_keys else [1, 0, 2, 0, 1, 2, 0]
        pt = [int(key[0]), int(key[1]), int(key[2]), int(key[3])]
        return SimpleNamespace(
            plaintext_idx=pt,
            key=key,
            score=0.0,
            meta={"work": {"evals": 0}, "telemetry": {"kaeding": {}}},
        )

    monkeypatch.setattr(phase2_mod, "run", _fake_run)

    target_pt = np.asarray([0, 1, 2, 0], dtype=np.uint8)
    bad_key = [1, 0, 2, 0, 1, 2, 0]
    bad_pt = [1, 0, 2, 0]
    empty_metrics = {
        "slip_count": 0,
        "slip_accept_count": 0,
        "slip_accept_rate": float("nan"),
        "accept_rate": float("nan"),
        "phase_attempts_total": 0,
        "phase_improves_total": 0,
        "phase_best_delta_max": float("nan"),
    }
    phasea_rows = [
        dict(
            start_hash="s0",
            end_hash="e0",
            restart_idx=0,
            start_key=list(bad_key),
            end_key=list(bad_key),
            start_plaintext=list(bad_pt),
            end_plaintext=list(bad_pt),
            end_match=_match_ratio(list(bad_pt), target_pt.tolist()),
            end_score_raw=-10.0,
            metrics=dict(
                slip_count=0,
                slip_accept_count=0,
                slip_accept_rate=float("nan"),
                accept_rate=float("nan"),
                phase_attempts_total=0,
                phase_improves_total=0,
                phase_best_delta_max=float("nan"),
            ),
        )
    ]
    stage_rows: list[dict[str, object]] = []
    scorer = _TargetScorer([0, 1, 2, 0])

    out = phase2_mod.run_stage3_two_phase_followup(
        tier_name="fixture_fixture_001_p2_c1_l4",
        tier_period=2,
        tier_columns=1,
        text_id=0,
        key_seed=511,
        key_len=7,
        ct_idx=np.asarray([0, 0, 0, 0], dtype=np.uint8),
        pt_idx=target_pt,
        order="col_then_sub",
        alphabet_size=3,
        direction=None,
        solve_match_threshold=0.9,
        oracle_assist_selection_effective=False,
        stage3_phaseA_experiment="a_baseline",
        stage3_phaseB_experiment="c_min_late",
        stage3_phaseB_char_pct_min_dynamic=0.4,
        stage3_phaseB_char_pct_min_source="test",
        phaseA_rows=phasea_rows,
        stage_rows=stage_rows,
        scorer_stage3_search_runtime=scorer,
        scorer_basin_judge_runtime=scorer,
        scorer_word_ngram_report_runtime=None,
        scorer_full_runtime=scorer,
        scorer_stage3_phaseB={},
        solver_stage3_cfg={"steps": 8, "restarts": 1, "col_batch": 4, "inner_batch": 8},
        stage3_phaseB_cfg={"steps": 8, "inner_batch": 8, "col_every": 0, "col_batch": 0},
        stage3_phaseB_top_n=1,
        stage3_phaseB_gate_delta=-1.0,
        stage3_phaseB_gate_end_gain=-1.0,
        stage3_scan_phaseA_only=False,
        stage3_span_basin_judge_k_cfg=1,
        stage3_span_basin_judge_require_span_active=False,
        stage3_span_basin_judge_dedupe_by_end_hash=True,
        stage3_span_basin_judge_tie_eps=0.0,
        stage3_span_basin_judge_tie_max_seeds=4,
        stage3_word_ngram_decision_influence=False,
        stage3_phasec_enabled=True,
        stage3_phasec_cfg={"steps": 16, "proposals_per_step": 16, "three_cycle_prob": 0.0},
        stage3_phasec_start_keys=1,
        stage3_phasec_seed_offset=0,
        stage3_phasec_word_ngram_tiebreak=False,
        batch_eval_chunk_size=32,
        require_batch_scoring=True,
        base_seed=2026,
        ev3_base=0,
        stage3_heartbeat_seconds=30.0,
        stage3_heartbeat_min_step=50,
        stage3_heartbeat_min_elapsed_seconds=5.0,
        stage3_hb_state={"last_emit_ts": float("-inf")},
        stage3_topk_payload=[],
        full_cipher=_DummyCipher(),
        append_stage3_topk_from_phasea_fn=lambda **kwargs: None,
        append_stage3_topk_from_kaeding_fn=lambda **kwargs: None,
        is_better_stage3_candidate_preserving_solve_fn=_is_better,
        match_ratio_fn=_match_ratio,
        extract_kaeding_metrics_fn=lambda _obj: dict(
            slip_count=0,
            slip_accept_count=0,
            slip_accept_rate=float("nan"),
            accept_rate=float("nan"),
            phase_attempts_total=0,
            phase_improves_total=0,
            phase_best_delta_max=float("nan"),
        ),
        solution_span_counter_summary_fn=lambda _obj: dict(
            total=0.0,
            active=0.0,
            skipped=0.0,
            seconds_total=0.0,
            seconds_active=0.0,
        ),
        scorer_span_counter_summary_fn=lambda _obj: dict(
            total=0.0,
            active=0.0,
            skipped=0.0,
            seconds_total=0.0,
            seconds_active=0.0,
        ),
        span_counter_delta_fn=lambda **kwargs: dict(total=0.0, active=0.0, seconds_total=0.0),
        stage3_progress_logging_fn=lambda **kwargs: {},
        fmt_finite_float_fn=lambda v, digits=3: f"{float(v):.{int(digits)}f}"
        if np.isfinite(v)
        else "nan",
    )

    assert int(out["phaseC_ran"]) == 1
    assert int(out["phaseC_evals"]) > 0
    assert float(out["best3_match"]) == pytest.approx(1.0)
    assert len(list(out.get("phaseC_start_summaries", []))) == 1
    assert int(out["phaseC_start_summaries"][0]["start_idx"]) == 1
    assert any(str(row.get("stage")) == "stage3_phaseC" for row in out["stage_rows"])
    text = capsys.readouterr().out
    assert "stage3-phaseC-plan" in text
    assert "stage3-phaseC-start" in text
    assert "stage3-phaseC tier=" in text


def test_stage3_phaseb_plan_and_finish_logging(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def _fake_run(**kwargs):
        init_keys = list(kwargs.get("initial_keys", []))
        key = list(map(int, init_keys[0])) if init_keys else [1, 0, 2, 0, 1, 2, 0]
        pt = [int(key[0]), int(key[1]), int(key[2]), int(key[3])]
        return SimpleNamespace(
            plaintext_idx=pt,
            key=key,
            score=-5.0,
            meta={"work": {"evals": 123}, "telemetry": {"kaeding": {}}},
        )

    monkeypatch.setattr(phase2_mod, "run", _fake_run)

    target_pt = np.asarray([1, 2, 2, 0], dtype=np.uint8)
    seed_key = [1, 0, 2, 0, 1, 2, 0]
    phasea_rows = [
        dict(
            start_hash="s0",
            end_hash="e0",
            restart_idx=0,
            start_key=list(seed_key),
            end_key=list(seed_key),
            start_plaintext=target_pt.astype(int).tolist(),
            end_plaintext=target_pt.astype(int).tolist(),
            end_match=_match_ratio(target_pt.astype(int).tolist(), [1, 0, 2, 0]),
            end_score_raw=-5.0,
            metrics=dict(
                slip_count=0,
                slip_accept_count=0,
                slip_accept_rate=float("nan"),
                accept_rate=float("nan"),
                phase_attempts_total=0,
                phase_improves_total=0,
                phase_best_delta_max=float("nan"),
            ),
        )
    ]

    _ = phase2_mod.run_stage3_two_phase_followup(
        tier_name="fixture_fixture_001_p2_c1_l4",
        tier_period=2,
        tier_columns=1,
        text_id=0,
        key_seed=511,
        key_len=7,
        ct_idx=np.asarray([0, 0, 0, 0], dtype=np.uint8),
        pt_idx=target_pt,
        order="col_then_sub",
        alphabet_size=3,
        direction=None,
        solve_match_threshold=0.9,
        oracle_assist_selection_effective=False,
        stage3_phaseA_experiment="a_baseline",
        stage3_phaseB_experiment="c_min_late",
        stage3_phaseB_char_pct_min_dynamic=0.4,
        stage3_phaseB_char_pct_min_source="test",
        phaseA_rows=phasea_rows,
        stage_rows=[],
        scorer_stage3_search_runtime=_TargetScorer([1, 0, 2, 0]),
        scorer_basin_judge_runtime=_TargetScorer([1, 0, 2, 0]),
        scorer_word_ngram_report_runtime=None,
        scorer_full_runtime=_TargetScorer([1, 0, 2, 0]),
        scorer_stage3_phaseB={},
        solver_stage3_cfg={"steps": 8, "restarts": 1, "col_batch": 4, "inner_batch": 8},
        stage3_phaseB_cfg={"steps": 10, "inner_batch": 8, "col_every": 2, "col_batch": 6},
        stage3_phaseB_top_n=1,
        stage3_phaseB_gate_delta=-1.0,
        stage3_phaseB_gate_end_gain=-1.0,
        stage3_scan_phaseA_only=False,
        stage3_span_basin_judge_k_cfg=1,
        stage3_span_basin_judge_require_span_active=False,
        stage3_span_basin_judge_dedupe_by_end_hash=True,
        stage3_span_basin_judge_tie_eps=0.0,
        stage3_span_basin_judge_tie_max_seeds=4,
        stage3_word_ngram_decision_influence=False,
        stage3_phasec_enabled=False,
        stage3_phasec_cfg={"steps": 0, "proposals_per_step": 1, "three_cycle_prob": 0.0},
        stage3_phasec_start_keys=0,
        stage3_phasec_seed_offset=0,
        stage3_phasec_word_ngram_tiebreak=False,
        batch_eval_chunk_size=32,
        require_batch_scoring=True,
        base_seed=2026,
        ev3_base=0,
        stage3_heartbeat_seconds=30.0,
        stage3_heartbeat_min_step=50,
        stage3_heartbeat_min_elapsed_seconds=5.0,
        stage3_hb_state={"last_emit_ts": float("-inf")},
        stage3_topk_payload=[],
        full_cipher=_DummyCipher(),
        append_stage3_topk_from_phasea_fn=lambda **kwargs: None,
        append_stage3_topk_from_kaeding_fn=lambda **kwargs: None,
        is_better_stage3_candidate_preserving_solve_fn=_is_better,
        match_ratio_fn=_match_ratio,
        extract_kaeding_metrics_fn=lambda _obj: dict(
            slip_count=0,
            slip_accept_count=0,
            slip_accept_rate=float("nan"),
            accept_rate=float("nan"),
            phase_attempts_total=0,
            phase_improves_total=0,
            phase_best_delta_max=float("nan"),
        ),
        solution_span_counter_summary_fn=lambda _obj: dict(
            total=0.0,
            active=0.0,
            skipped=0.0,
            seconds_total=0.0,
            seconds_active=0.0,
        ),
        scorer_span_counter_summary_fn=lambda _obj: dict(
            total=0.0,
            active=0.0,
            skipped=0.0,
            seconds_total=0.0,
            seconds_active=0.0,
        ),
        span_counter_delta_fn=lambda **kwargs: dict(total=0.0, active=0.0, seconds_total=0.0),
        stage3_progress_logging_fn=lambda **kwargs: {},
        fmt_finite_float_fn=lambda v, digits=3: f"{float(v):.{int(digits)}f}"
        if np.isfinite(v)
        else "nan",
    )

    out = capsys.readouterr().out
    assert "stage3-phaseB-plan" in out
    assert "total_steps=10" in out
    assert "approx_evals_per_step=11.0" in out
    assert "approx_eval_budget=110" in out
    assert "stage3-phaseB-finish" in out
    assert "evals=123" in out


def test_stage3_two_phase_skips_phasec_after_solved_phasea_when_continue_disabled(
    capsys: pytest.CaptureFixture[str],
) -> None:
    target_pt = np.asarray([0, 1, 2, 0], dtype=np.uint8)
    solved_key = [0, 1, 2, 0, 1, 2, 0]
    phasea_rows = [
        dict(
            start_hash="s0",
            end_hash="e0",
            restart_idx=0,
            start_key=list(solved_key),
            end_key=list(solved_key),
            start_plaintext=target_pt.astype(int).tolist(),
            end_plaintext=target_pt.astype(int).tolist(),
            end_match=1.0,
            end_score_pct=4.0,
            end_score_raw=4.0,
            best_delta_pct=0.0,
            metrics=dict(
                slip_count=0,
                slip_accept_count=0,
                slip_accept_rate=float("nan"),
                accept_rate=float("nan"),
                phase_attempts_total=0,
                phase_improves_total=0,
                phase_best_delta_max=float("nan"),
            ),
        )
    ]

    out = phase2_mod.run_stage3_two_phase_followup(
        tier_name="fixture_fixture_001_p2_c1_l4",
        tier_period=2,
        tier_columns=1,
        text_id=0,
        key_seed=411,
        key_len=7,
        ct_idx=np.asarray([0, 0, 0, 0], dtype=np.uint8),
        pt_idx=target_pt,
        order="col_then_sub",
        alphabet_size=3,
        direction=None,
        solve_match_threshold=0.9,
        stage3_continue_after_solve=False,
        oracle_assist_selection_effective=False,
        stage3_phaseA_experiment="a_baseline",
        stage3_phaseB_experiment="c_min_late",
        stage3_phaseB_char_pct_min_dynamic=0.4,
        stage3_phaseB_char_pct_min_source="test",
        phaseA_rows=phasea_rows,
        stage_rows=[],
        scorer_stage3_search_runtime=_ConstantScorer(),
        scorer_basin_judge_runtime=_ConstantScorer(),
        scorer_word_ngram_report_runtime=None,
        scorer_full_runtime=_ConstantScorer(),
        scorer_stage3_phaseB={},
        solver_stage3_cfg={"steps": 8, "restarts": 1, "col_batch": 4, "inner_batch": 8},
        stage3_phaseB_cfg={"steps": 8, "inner_batch": 8, "col_every": 0, "col_batch": 0},
        stage3_phaseB_top_n=1,
        stage3_phaseB_gate_delta=-1.0,
        stage3_phaseB_gate_end_gain=-1.0,
        stage3_scan_phaseA_only=False,
        stage3_span_basin_judge_k_cfg=1,
        stage3_span_basin_judge_require_span_active=False,
        stage3_span_basin_judge_dedupe_by_end_hash=True,
        stage3_span_basin_judge_tie_eps=0.0,
        stage3_span_basin_judge_tie_max_seeds=4,
        stage3_word_ngram_decision_influence=False,
        stage3_phasec_enabled=True,
        stage3_phasec_cfg={"steps": 16, "proposals_per_step": 16, "three_cycle_prob": 0.0},
        stage3_phasec_start_keys=1,
        stage3_phasec_seed_offset=0,
        stage3_phasec_word_ngram_tiebreak=False,
        batch_eval_chunk_size=32,
        require_batch_scoring=True,
        base_seed=2026,
        ev3_base=0,
        stage3_heartbeat_seconds=30.0,
        stage3_heartbeat_min_step=50,
        stage3_heartbeat_min_elapsed_seconds=5.0,
        stage3_hb_state={"last_emit_ts": float("-inf")},
        stage3_topk_payload=[],
        full_cipher=_DummyCipher(),
        append_stage3_topk_from_phasea_fn=lambda **kwargs: None,
        append_stage3_topk_from_kaeding_fn=lambda **kwargs: None,
        is_better_stage3_candidate_preserving_solve_fn=_is_better,
        match_ratio_fn=_match_ratio,
        extract_kaeding_metrics_fn=lambda _obj: dict(
            slip_count=0,
            slip_accept_count=0,
            slip_accept_rate=float("nan"),
            accept_rate=float("nan"),
            phase_attempts_total=0,
            phase_improves_total=0,
            phase_best_delta_max=float("nan"),
        ),
        solution_span_counter_summary_fn=lambda _obj: dict(
            total=0.0,
            active=0.0,
            skipped=0.0,
            seconds_total=0.0,
            seconds_active=0.0,
        ),
        scorer_span_counter_summary_fn=lambda _obj: dict(
            total=0.0,
            active=0.0,
            skipped=0.0,
            seconds_total=0.0,
            seconds_active=0.0,
        ),
        span_counter_delta_fn=lambda **kwargs: dict(total=0.0, active=0.0, seconds_total=0.0),
        stage3_progress_logging_fn=lambda **kwargs: {},
        fmt_finite_float_fn=lambda v, digits=3: f"{float(v):.{int(digits)}f}"
        if np.isfinite(v)
        else "nan",
    )

    assert int(out["phaseB_skipped"]) == 1
    assert str(out["phaseB_skip_reason"]) == "phaseA_solved"
    assert int(out["phaseC_enabled_effective"]) == 0
    assert int(out["phaseC_ran"]) == 0
    assert str(out["stop_reason_update"]) == "solved_stage3"
    assert float(out["best3_match"]) == pytest.approx(1.0)
    text = capsys.readouterr().out
    assert "stage3-phaseB-gate" in text
    assert "reason=phaseA_solved" in text


def test_stage3_phasec_lexical_budget_cap(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def _fake_run(**kwargs):
        init_keys = list(kwargs.get("initial_keys", []))
        key = list(map(int, init_keys[0])) if init_keys else [1, 0, 2, 0, 1, 2, 0]
        pt = [int(key[0]), int(key[1]), int(key[2]), int(key[3])]
        return SimpleNamespace(
            plaintext_idx=pt,
            key=key,
            score=0.0,
            meta={"work": {"evals": 7}, "telemetry": {"kaeding": {}}},
        )

    def _constant_match(_lhs: list[int], _rhs: list[int]) -> float:
        return 0.8

    monkeypatch.setattr(phase2_mod, "run", _fake_run)

    target_pt = np.asarray([1, 0, 2, 0], dtype=np.uint8)
    seed_key = [1, 0, 2, 0, 1, 2, 0]
    phasea_rows = [
        dict(
            start_hash="s0",
            end_hash="e0",
            restart_idx=0,
            start_key=list(seed_key),
            end_key=list(seed_key),
            start_plaintext=target_pt.astype(int).tolist(),
            end_plaintext=target_pt.astype(int).tolist(),
            end_match=0.8,
            end_score_raw=0.0,
            metrics=dict(
                slip_count=0,
                slip_accept_count=0,
                slip_accept_rate=float("nan"),
                accept_rate=float("nan"),
                phase_attempts_total=0,
                phase_improves_total=0,
                phase_best_delta_max=float("nan"),
            ),
        )
    ]
    lexical_scorer = _LexicalReportScorer()

    out = phase2_mod.run_stage3_two_phase_followup(
        tier_name="fixture_fixture_001_p2_c1_l4",
        tier_period=2,
        tier_columns=1,
        text_id=0,
        key_seed=511,
        key_len=7,
        ct_idx=np.asarray([0, 0, 0, 0], dtype=np.uint8),
        pt_idx=target_pt,
        order="col_then_sub",
        alphabet_size=3,
        direction=None,
        solve_match_threshold=0.9,
        oracle_assist_selection_effective=False,
        stage3_phaseA_experiment="a_baseline",
        stage3_phaseB_experiment="c_min_late",
        stage3_phaseB_char_pct_min_dynamic=0.4,
        stage3_phaseB_char_pct_min_source="test",
        phaseA_rows=phasea_rows,
        stage_rows=[],
        scorer_stage3_search_runtime=_ConstantScorer(),
        scorer_basin_judge_runtime=_ConstantScorer(),
        scorer_word_ngram_report_runtime=lexical_scorer,
        scorer_full_runtime=_ConstantScorer(),
        scorer_stage3_phaseB={},
        solver_stage3_cfg={"steps": 8, "restarts": 1, "col_batch": 4, "inner_batch": 8},
        stage3_phaseB_cfg={"steps": 8, "inner_batch": 8, "col_every": 0, "col_batch": 0},
        stage3_phaseB_top_n=1,
        stage3_phaseB_gate_delta=-1.0,
        stage3_phaseB_gate_end_gain=-1.0,
        stage3_scan_phaseA_only=False,
        stage3_span_basin_judge_k_cfg=1,
        stage3_span_basin_judge_require_span_active=False,
        stage3_span_basin_judge_dedupe_by_end_hash=True,
        stage3_span_basin_judge_tie_eps=0.0,
        stage3_span_basin_judge_tie_max_seeds=4,
        stage3_word_ngram_decision_influence=False,
        stage3_phasec_enabled=True,
        stage3_phasec_cfg={
            "steps": 8,
            "proposals_per_step": 4,
            "three_cycle_prob": 0.0,
            "lexical_min_match": 0.0,
            "lexical_match_tie_eps": 0.0,
            "lexical_score_tie_eps": 0.0,
            "lexical_max_calls": 1,
        },
        stage3_phasec_start_keys=1,
        stage3_phasec_seed_offset=0,
        stage3_phasec_word_ngram_tiebreak=True,
        batch_eval_chunk_size=32,
        require_batch_scoring=True,
        base_seed=2026,
        ev3_base=0,
        stage3_heartbeat_seconds=30.0,
        stage3_heartbeat_min_step=50,
        stage3_heartbeat_min_elapsed_seconds=5.0,
        stage3_hb_state={"last_emit_ts": float("-inf")},
        stage3_topk_payload=[],
        full_cipher=_DummyCipher(),
        append_stage3_topk_from_phasea_fn=lambda **kwargs: None,
        append_stage3_topk_from_kaeding_fn=lambda **kwargs: None,
        is_better_stage3_candidate_preserving_solve_fn=_is_better,
        match_ratio_fn=_constant_match,
        extract_kaeding_metrics_fn=lambda _obj: dict(
            slip_count=0,
            slip_accept_count=0,
            slip_accept_rate=float("nan"),
            accept_rate=float("nan"),
            phase_attempts_total=0,
            phase_improves_total=0,
            phase_best_delta_max=float("nan"),
        ),
        solution_span_counter_summary_fn=lambda _obj: dict(
            total=0.0,
            active=0.0,
            skipped=0.0,
            seconds_total=0.0,
            seconds_active=0.0,
        ),
        scorer_span_counter_summary_fn=lambda _obj: dict(
            total=0.0,
            active=0.0,
            skipped=0.0,
            seconds_total=0.0,
            seconds_active=0.0,
        ),
        span_counter_delta_fn=lambda **kwargs: dict(total=0.0, active=0.0, seconds_total=0.0),
        stage3_progress_logging_fn=lambda **kwargs: {},
        fmt_finite_float_fn=lambda v, digits=3: f"{float(v):.{int(digits)}f}"
        if np.isfinite(v)
        else "nan",
    )

    assert int(out["phaseC_ran"]) == 1
    assert int(out["phaseC_lexical_cache_misses"]) == 1
    assert int(out["phaseC_lexical_budget_skips"]) >= 1
    assert int(lexical_scorer.calls) == 1
    text = capsys.readouterr().out
    assert "lexical_max_calls=1" in text
    assert "lex_miss=1" in text
    assert "lex_budget_skip=" in text


def test_stage3_phasec_rescue_targets_slice_by_probe_score_rule(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def _fake_run(**kwargs):
        init_keys = list(kwargs.get("initial_keys", []))
        key = list(map(int, init_keys[0])) if init_keys else [0, 0, 0, 2, 1, 0, 0]
        return SimpleNamespace(
            plaintext_idx=[0, 2, 0, 1],
            key=key,
            score=0.0,
            meta={"work": {"evals": 5}, "telemetry": {"kaeding": {}}},
        )

    monkeypatch.setattr(phase2_mod, "run", _fake_run)

    def _constant_match(_lhs: list[int], _rhs: list[int]) -> float:
        return 0.0

    target_pt = np.asarray([0, 0], dtype=np.uint8)
    seed_key = [0, 1, 2, 0, 1, 2, 0]
    phasea_rows = [
        dict(
            start_hash="s0",
            end_hash="e0",
            restart_idx=0,
            start_key=list(seed_key),
            end_key=list(seed_key),
            start_plaintext=[0, 0],
            end_plaintext=[0, 0],
            end_match=0.0,
            end_score_raw=0.0,
            metrics=dict(
                slip_count=0,
                slip_accept_count=0,
                slip_accept_rate=float("nan"),
                accept_rate=float("nan"),
                phase_attempts_total=0,
                phase_improves_total=0,
                phase_best_delta_max=float("nan"),
            ),
        )
    ]

    out = phase2_mod.run_stage3_two_phase_followup(
        tier_name="fixture_fixture_001_p2_c1_l4",
        tier_period=2,
        tier_columns=1,
        text_id=0,
        key_seed=511,
        key_len=7,
        ct_idx=np.asarray([0, 0, 0, 0], dtype=np.uint8),
        pt_idx=target_pt,
        order="col_then_sub",
        alphabet_size=3,
        direction=None,
        solve_match_threshold=0.9,
        oracle_assist_selection_effective=False,
        stage3_phaseA_experiment="a_baseline",
        stage3_phaseB_experiment="c_min_late",
        stage3_phaseB_char_pct_min_dynamic=0.4,
        stage3_phaseB_char_pct_min_source="test",
        phaseA_rows=phasea_rows,
        stage_rows=[],
        scorer_stage3_search_runtime=_SlicePreferenceScorer(),
        scorer_basin_judge_runtime=_SlicePreferenceScorer(),
        scorer_word_ngram_report_runtime=None,
        scorer_full_runtime=_SlicePreferenceScorer(),
        scorer_stage3_phaseB={},
        solver_stage3_cfg={"steps": 4, "restarts": 1, "col_batch": 4, "inner_batch": 8},
        stage3_phaseB_cfg={"steps": 4, "inner_batch": 8, "col_every": 0, "col_batch": 0},
        stage3_phaseB_top_n=1,
        stage3_phaseB_gate_delta=-1.0,
        stage3_phaseB_gate_end_gain=-1.0,
        stage3_scan_phaseA_only=False,
        stage3_span_basin_judge_k_cfg=1,
        stage3_span_basin_judge_require_span_active=False,
        stage3_span_basin_judge_dedupe_by_end_hash=True,
        stage3_span_basin_judge_tie_eps=0.0,
        stage3_span_basin_judge_tie_max_seeds=4,
        stage3_word_ngram_decision_influence=False,
        stage3_phasec_enabled=True,
        stage3_phasec_cfg={
            "steps": 2,
            "proposals_per_step": 2,
            "three_cycle_prob": 0.0,
            "rescue_enabled": True,
            "rescue_anchor_enabled": True,
            "rescue_max_starts": 1,
            "rescue_target_mode": "slice_probe",
            "rescue_selector_mode": "rescue_shallow_then_search",
            "rescue_candidates": 4,
            "rescue_slip_swaps": 1,
            "rescue_mini_search_steps": 2,
            "rescue_mini_search_beam_width": 4,
            "rescue_mini_search_top_symbols": 6,
            "rescue_mini_search_keep_all_rows": True,
            "rescue_polish_steps": 2,
        },
        stage3_phasec_start_keys=1,
        stage3_phasec_seed_offset=0,
        stage3_phasec_word_ngram_tiebreak=False,
        batch_eval_chunk_size=32,
        require_batch_scoring=True,
        base_seed=2026,
        ev3_base=0,
        stage3_heartbeat_seconds=30.0,
        stage3_heartbeat_min_step=50,
        stage3_heartbeat_min_elapsed_seconds=5.0,
        stage3_hb_state={"last_emit_ts": float("-inf")},
        stage3_topk_payload=[],
        full_cipher=_SliceChangeCipher(base_key=seed_key, period=2, alphabet_size=3),
        append_stage3_topk_from_phasea_fn=lambda **kwargs: None,
        append_stage3_topk_from_kaeding_fn=lambda **kwargs: None,
        is_better_stage3_candidate_preserving_solve_fn=_is_better,
        match_ratio_fn=_constant_match,
        extract_kaeding_metrics_fn=lambda _obj: dict(
            slip_count=0,
            slip_accept_count=0,
            slip_accept_rate=float("nan"),
            accept_rate=float("nan"),
            phase_attempts_total=0,
            phase_improves_total=0,
            phase_best_delta_max=float("nan"),
        ),
        solution_span_counter_summary_fn=lambda _obj: dict(
            total=0.0,
            active=0.0,
            skipped=0.0,
            seconds_total=0.0,
            seconds_active=0.0,
        ),
        scorer_span_counter_summary_fn=lambda _obj: dict(
            total=0.0,
            active=0.0,
            skipped=0.0,
            seconds_total=0.0,
            seconds_active=0.0,
        ),
        span_counter_delta_fn=lambda **kwargs: dict(total=0.0, active=0.0, seconds_total=0.0),
        stage3_progress_logging_fn=lambda **kwargs: {},
        fmt_finite_float_fn=lambda v, digits=3: f"{float(v):.{int(digits)}f}"
        if np.isfinite(v)
        else "nan",
    )

    assert int(out["phaseC_rescue_enabled_cfg"]) == 1
    assert int(out["phaseC_rescue_ran"]) == 1
    assert int(out["phaseC_rescue_starts_attempted"]) == 1
    assert int(out["phaseC_rescue_applied_starts"]) == 1
    assert str(out["phaseC_rescue_target_mode_cfg"]) == "slice_probe"
    assert str(out["phaseC_rescue_selector_mode_cfg"]) == "rescue_shallow_then_search"
    assert int(out["phaseC_rescue_candidates_cfg"]) == 4
    assert int(out["phaseC_rescue_slip_swaps_cfg"]) == 1
    assert int(out["phaseC_rescue_mini_search_steps_cfg"]) == 2
    assert int(out["phaseC_rescue_mini_search_beam_width_cfg"]) == 4
    assert int(out["phaseC_rescue_mini_search_top_symbols_cfg"]) == 6
    assert int(out["phaseC_rescue_mini_search_keep_all_rows_cfg"]) == 1
    assert int(out["phaseC_rescue_polish_steps_cfg"]) == 2
    assert int(out["phaseC_rescue_probe_evals"]) > 0
    assert int(out["phaseC_rescue_evals"]) > 0
    assert int(out["phaseC_rescue_mini_search_evals"]) > 0
    assert int(out["phaseC_rescue_guard_search_passes"]) == 1
    assert int(out["phaseC_rescue_anchor_enabled_cfg"]) == 1
    assert int(out["phaseC_rescue_max_starts_cfg"]) == 1
    summaries = list(out["phaseC_start_summaries"])
    assert len(summaries) == 1
    assert str(summaries[0]["lane"]) == "anchor"
    assert int(summaries[0]["rescue_eligible"]) == 1
    assert int(summaries[0]["rescue_attempted"]) == 1
    assert int(summaries[0]["rescue_applied"]) == 1
    assert str(summaries[0]["rescue_target_mode"]) == "slice_probe"
    assert str(summaries[0]["rescue_selector_mode"]) == "rescue_shallow_then_search"
    assert int(summaries[0]["rescue_target_slice"]) == 1
    assert str(summaries[0]["rescue_slice_reason"]) == "slice_probe_best_score_gain"
    assert float(summaries[0]["rescue_probe_score_gain"]) > 0.0
    assert str(summaries[0]["rescue_landing_type"]) in {"probe_seed", "mini_search"}
    assert int(summaries[0]["rescue_mini_search_pool_rows"]) > 0
    assert int(summaries[0]["rescue_polish_steps_used"]) == 2
    assert float(summaries[0]["rescue_guard_search_best_score"]) > float(
        summaries[0]["rescue_guard_search_base_score"]
    )
    assert int(summaries[0]["rescue_guard_search_passed"]) == 1
    assert summaries[0]["rescue_post_score"] is not None
    assert float(summaries[0]["rescue_post_score"]) > float(summaries[0]["init_score"])
    assert "rescue_score_gain" in summaries[0]
    text = capsys.readouterr().out
    assert "stage3-phaseC-rescue-start" in text
    assert "stage3-phaseC-rescue-finish-start" in text
    assert "target_slice=1" in text
    assert "slice_reason=slice_probe_best_score_gain" in text
    assert "target_mode=slice_probe" in text


def test_stage3_phasec_challenger_rescue_can_overtake_anchor(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path,
) -> None:
    def _fake_run(**kwargs):
        init_keys = list(kwargs.get("initial_keys", []))
        key = list(map(int, init_keys[0])) if init_keys else [1, 1, 2, 0, 1, 2, 0]
        return SimpleNamespace(
            plaintext_idx=[1, 0],
            key=key,
            score=0.0,
            meta={"work": {"evals": 3}, "telemetry": {"kaeding": {}}},
        )

    monkeypatch.setattr(phase2_mod, "run", _fake_run)

    def _constant_match(_lhs: list[int], _rhs: list[int]) -> float:
        return 0.0

    base_key = [0, 1, 2, 0, 1, 2, 0]
    anchor_key = [1, 1, 2, 0, 1, 2, 0]
    target_pt = np.asarray([0, 0], dtype=np.uint8)
    phasea_rows = [
        dict(
            start_hash="sa",
            end_hash="ha",
            restart_idx=0,
            start_key=list(anchor_key),
            end_key=list(anchor_key),
            start_plaintext=[1, 0],
            end_plaintext=[1, 0],
            end_match=0.0,
            end_score_raw=-1.0,
            metrics=dict(
                slip_count=0,
                slip_accept_count=0,
                slip_accept_rate=float("nan"),
                accept_rate=float("nan"),
                phase_attempts_total=0,
                phase_improves_total=0,
                phase_best_delta_max=float("nan"),
            ),
        )
    ]

    def _append_phaseb_topk(**kwargs) -> None:
        kwargs["payload"].append(
            dict(
                rank=2,
                key_idx=list(base_key),
                plaintext_idx=[0, 0],
                end_hash="hc2",
                source="phaseB_topk",
            )
        )

    checkpoint_path = tmp_path / "phasec_start_checkpoints.jsonl"
    out = phase2_mod.run_stage3_two_phase_followup(
        tier_name="fixture_fixture_001_p2_c1_l4",
        tier_period=2,
        tier_columns=1,
        text_id=0,
        key_seed=511,
        key_len=7,
        ct_idx=np.asarray([0, 0, 0, 0], dtype=np.uint8),
        pt_idx=target_pt,
        order="col_then_sub",
        alphabet_size=3,
        direction=None,
        solve_match_threshold=0.9,
        oracle_assist_selection_effective=False,
        stage3_phaseA_experiment="a_baseline",
        stage3_phaseB_experiment="c_min_late",
        stage3_phaseB_char_pct_min_dynamic=0.4,
        stage3_phaseB_char_pct_min_source="test",
        phaseA_rows=phasea_rows,
        stage_rows=[],
        scorer_stage3_search_runtime=_SlicePreferenceScorer(),
        scorer_basin_judge_runtime=_SlicePreferenceScorer(),
        scorer_word_ngram_report_runtime=None,
        scorer_full_runtime=_SlicePreferenceScorer(),
        scorer_stage3_phaseB={},
        solver_stage3_cfg={"steps": 4, "restarts": 1, "col_batch": 4, "inner_batch": 8},
        stage3_phaseB_cfg={"steps": 4, "inner_batch": 8, "col_every": 0, "col_batch": 0},
        stage3_phaseB_top_n=1,
        stage3_phaseB_gate_delta=-1.0,
        stage3_phaseB_gate_end_gain=-1.0,
        stage3_scan_phaseA_only=False,
        stage3_span_basin_judge_k_cfg=1,
        stage3_span_basin_judge_require_span_active=False,
        stage3_span_basin_judge_dedupe_by_end_hash=True,
        stage3_span_basin_judge_tie_eps=0.0,
        stage3_span_basin_judge_tie_max_seeds=4,
        stage3_word_ngram_decision_influence=False,
        stage3_phasec_enabled=True,
        stage3_phasec_cfg={
            "steps": 1,
            "proposals_per_step": 1,
            "three_cycle_prob": 0.0,
            "rescue_enabled": True,
            "rescue_target_mode": "slice_probe",
            "rescue_selector_mode": "rescue_shallow_then_search",
            "rescue_candidates": 3,
            "rescue_slip_swaps": 1,
            "rescue_phaseb_topk_min_rank": 2,
            "rescue_max_starts": 1,
            "rescue_search_score_max_drop": 0.0,
            "rescue_mini_search_steps": 2,
            "rescue_mini_search_beam_width": 4,
            "rescue_mini_search_top_symbols": 6,
            "rescue_mini_search_keep_all_rows": True,
            "rescue_polish_steps": 5,
        },
        stage3_phasec_start_keys=2,
        stage3_phasec_seed_offset=0,
        stage3_phasec_word_ngram_tiebreak=False,
        batch_eval_chunk_size=32,
        require_batch_scoring=True,
        base_seed=2026,
        ev3_base=0,
        stage3_heartbeat_seconds=30.0,
        stage3_heartbeat_min_step=50,
        stage3_heartbeat_min_elapsed_seconds=5.0,
        stage3_hb_state={"last_emit_ts": float("-inf")},
        stage3_topk_payload=[],
        full_cipher=_SliceChangeCipher(base_key=base_key, period=2, alphabet_size=3),
        append_stage3_topk_from_phasea_fn=lambda **kwargs: None,
        append_stage3_topk_from_kaeding_fn=_append_phaseb_topk,
        is_better_stage3_candidate_preserving_solve_fn=_is_better,
        match_ratio_fn=_constant_match,
        extract_kaeding_metrics_fn=lambda _obj: dict(
            slip_count=0,
            slip_accept_count=0,
            slip_accept_rate=float("nan"),
            accept_rate=float("nan"),
            phase_attempts_total=0,
            phase_improves_total=0,
            phase_best_delta_max=float("nan"),
        ),
        solution_span_counter_summary_fn=lambda _obj: dict(
            total=0.0,
            active=0.0,
            skipped=0.0,
            seconds_total=0.0,
            seconds_active=0.0,
        ),
        scorer_span_counter_summary_fn=lambda _obj: dict(
            total=0.0,
            active=0.0,
            skipped=0.0,
            seconds_total=0.0,
            seconds_active=0.0,
        ),
        span_counter_delta_fn=lambda **kwargs: dict(total=0.0, active=0.0, seconds_total=0.0),
        stage3_progress_logging_fn=lambda **kwargs: {},
        fmt_finite_float_fn=lambda v, digits=3: f"{float(v):.{int(digits)}f}"
        if np.isfinite(v)
        else "nan",
        phasec_start_checkpoint_path=checkpoint_path,
        append_jsonl_row_fn=_append_jsonl_test,
    )

    assert int(out["phaseC_rescue_ran"]) == 1
    assert int(out["phaseC_rescue_starts_attempted"]) == 1
    assert int(out["phaseC_rescue_applied_starts"]) == 1
    assert int(out["phaseC_rescue_guard_search_passes"]) == 1
    assert int(out["phaseC_anchor_lane_starts"]) == 1
    assert int(out["phaseC_challenger_lane_starts"]) == 1
    assert int(out["phaseC_challenger_overtook_anchor_count"]) == 1
    assert str(out["phaseC_final_winner_lane"]) == "challenger"
    assert str(out["phaseC_final_winner_source"]) == "phaseB_topk"
    assert str(out["phaseC_checkpoint_jsonl_name"]) == "phasec_start_checkpoints.jsonl"
    assert int(out["phaseC_checkpoint_rows_written"]) == 2
    summaries = list(out["phaseC_start_summaries"])
    assert len(summaries) == 2
    assert str(summaries[0]["lane"]) == "anchor"
    assert list(summaries[0]["init_key_idx"]) != []
    assert list(summaries[0]["init_plaintext_idx"]) != []
    assert list(summaries[0]["final_key_idx"]) != []
    assert list(summaries[0]["final_plaintext_idx"]) != []
    assert int(summaries[0]["rescue_attempted"]) == 0
    assert str(summaries[0]["rescue_skip_reason"]) == "anchor_polish_only"
    assert str(summaries[1]["lane"]) == "challenger"
    assert str(summaries[1]["source"]) == "phaseB_topk"
    assert int(summaries[1]["source_rank"]) == 2
    assert list(summaries[1]["init_key_idx"]) != []
    assert list(summaries[1]["init_plaintext_idx"]) != []
    assert list(summaries[1]["final_key_idx"]) != []
    assert list(summaries[1]["final_plaintext_idx"]) != []
    assert int(summaries[1]["rescue_eligible"]) == 1
    assert int(summaries[1]["rescue_attempted"]) == 1
    assert str(summaries[1]["rescue_selector_mode"]) == "rescue_shallow_then_search"
    assert int(summaries[1]["rescue_mini_search_pool_rows"]) > 0
    assert int(summaries[1]["rescue_polish_steps_used"]) == 5
    assert int(summaries[1]["overtook_anchor"]) == 1
    assert int(summaries[1]["became_global_best"]) == 1
    rows = [
        json.loads(line)
        for line in checkpoint_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert len(rows) == 2
    assert [int(row["start_idx"]) for row in rows] == [1, 2]
    assert str(rows[0]["lane"]) == "anchor"
    assert str(rows[1]["lane"]) == "challenger"
    assert str(rows[1]["source"]) == "phaseB_topk"
    assert list(rows[0]["final_key_idx"]) != []
    assert list(rows[1]["final_key_idx"]) != []
    assert list(rows[0]["final_plaintext_idx"]) != []
    assert list(rows[1]["final_plaintext_idx"]) != []
    assert int(rows[1]["rescue_applied"]) == 1
    assert int(rows[1]["overtook_anchor"]) == 1
    assert float(rows[1]["match_init"]) == pytest.approx(float(rows[1]["init_match"]))
    assert float(rows[1]["match_final"]) == pytest.approx(float(rows[1]["final_match"]))
    assert float(rows[1]["score_init"]) == pytest.approx(float(rows[1]["init_score"]))
    assert float(rows[1]["score_final"]) == pytest.approx(float(rows[1]["final_score"]))
    text = capsys.readouterr().out
    assert "lane=anchor rescue_eligible=0" in text
    assert "lane=challenger rescue_eligible=1" in text
    assert "step=5/5" in text
    assert "final_winner_lane=challenger" in text


def test_stage3_phasec_rescue_budget_reaches_later_phaseb_topk_challengers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _fake_run(**kwargs):
        init_keys = list(kwargs.get("initial_keys", []))
        key = list(map(int, init_keys[0])) if init_keys else [1, 1, 2, 0, 1, 2, 0]
        return SimpleNamespace(
            plaintext_idx=[1, 0],
            key=key,
            score=0.0,
            meta={"work": {"evals": 3}, "telemetry": {"kaeding": {}}},
        )

    monkeypatch.setattr(phase2_mod, "run", _fake_run)

    def _constant_match(_lhs: list[int], _rhs: list[int]) -> float:
        return 0.0

    base_key = [0, 1, 2, 0, 1, 2, 0]
    anchor_key = [1, 1, 2, 0, 1, 2, 0]
    target_pt = np.asarray([0, 0], dtype=np.uint8)
    phasea_rows = [
        dict(
            start_hash="sa",
            end_hash="ha",
            restart_idx=0,
            start_key=list(anchor_key),
            end_key=list(anchor_key),
            start_plaintext=[1, 0],
            end_plaintext=[1, 0],
            end_match=0.0,
            end_score_raw=-1.0,
            metrics=dict(
                slip_count=0,
                slip_accept_count=0,
                slip_accept_rate=float("nan"),
                accept_rate=float("nan"),
                phase_attempts_total=0,
                phase_improves_total=0,
                phase_best_delta_max=float("nan"),
            ),
        )
    ]

    topk_rows = [
        dict(rank=2, key_idx=list(base_key), plaintext_idx=[0, 0], end_hash="hc2", source="phaseB_topk"),
        dict(rank=3, key_idx=[0, 1, 2, 1, 1, 2, 0], plaintext_idx=[0, 1], end_hash="hc3", source="phaseB_topk"),
        dict(rank=4, key_idx=[0, 2, 1, 0, 1, 2, 0], plaintext_idx=[1, 0], end_hash="hc4", source="phaseB_topk"),
        dict(rank=5, key_idx=[0, 1, 2, 0, 2, 1, 0], plaintext_idx=[0, 1], end_hash="hc5", source="phaseB_topk"),
    ]

    def _append_phaseb_topk(**kwargs) -> None:
        kwargs["payload"].extend(dict(row) for row in topk_rows)

    out = phase2_mod.run_stage3_two_phase_followup(
        tier_name="fixture_fixture_001_p2_c1_l4",
        tier_period=2,
        tier_columns=1,
        text_id=0,
        key_seed=511,
        key_len=7,
        ct_idx=np.asarray([0, 0, 0, 0], dtype=np.uint8),
        pt_idx=target_pt,
        order="col_then_sub",
        alphabet_size=3,
        direction=None,
        solve_match_threshold=0.9,
        oracle_assist_selection_effective=False,
        stage3_phaseA_experiment="a_baseline",
        stage3_phaseB_experiment="c_min_late",
        stage3_phaseB_char_pct_min_dynamic=0.4,
        stage3_phaseB_char_pct_min_source="test",
        phaseA_rows=phasea_rows,
        stage_rows=[],
        scorer_stage3_search_runtime=_SlicePreferenceScorer(),
        scorer_basin_judge_runtime=_SlicePreferenceScorer(),
        scorer_word_ngram_report_runtime=None,
        scorer_full_runtime=_SlicePreferenceScorer(),
        scorer_stage3_phaseB={},
        solver_stage3_cfg={"steps": 4, "restarts": 1, "col_batch": 4, "inner_batch": 8},
        stage3_phaseB_cfg={"steps": 4, "inner_batch": 8, "col_every": 0, "col_batch": 0},
        stage3_phaseB_top_n=1,
        stage3_phaseB_gate_delta=-1.0,
        stage3_phaseB_gate_end_gain=-1.0,
        stage3_scan_phaseA_only=False,
        stage3_span_basin_judge_k_cfg=1,
        stage3_span_basin_judge_require_span_active=False,
        stage3_span_basin_judge_dedupe_by_end_hash=True,
        stage3_span_basin_judge_tie_eps=0.0,
        stage3_span_basin_judge_tie_max_seeds=4,
        stage3_word_ngram_decision_influence=False,
        stage3_phasec_enabled=True,
        stage3_phasec_cfg={
            "steps": 1,
            "proposals_per_step": 1,
            "three_cycle_prob": 0.0,
            "rescue_enabled": True,
            "rescue_target_mode": "slice_probe",
            "rescue_selector_mode": "rescue_shallow_then_search",
            "rescue_candidates": 4,
            "rescue_slip_swaps": 1,
            "rescue_phaseb_topk_min_rank": 2,
            "rescue_max_starts": 4,
            "rescue_search_score_max_drop": 0.35,
            "rescue_mini_search_steps": 2,
            "rescue_mini_search_beam_width": 4,
            "rescue_mini_search_top_symbols": 6,
            "rescue_mini_search_keep_all_rows": True,
            "rescue_polish_steps": 1,
        },
        stage3_phasec_start_keys=6,
        stage3_phasec_seed_offset=0,
        stage3_phasec_word_ngram_tiebreak=False,
        batch_eval_chunk_size=32,
        require_batch_scoring=True,
        base_seed=2026,
        ev3_base=0,
        stage3_heartbeat_seconds=30.0,
        stage3_heartbeat_min_step=50,
        stage3_heartbeat_min_elapsed_seconds=5.0,
        stage3_hb_state={"last_emit_ts": float("-inf")},
        stage3_topk_payload=[],
        full_cipher=_SliceChangeCipher(base_key=base_key, period=2, alphabet_size=3),
        append_stage3_topk_from_phasea_fn=lambda **kwargs: None,
        append_stage3_topk_from_kaeding_fn=_append_phaseb_topk,
        is_better_stage3_candidate_preserving_solve_fn=_is_better,
        match_ratio_fn=_constant_match,
        extract_kaeding_metrics_fn=lambda _obj: dict(
            slip_count=0,
            slip_accept_count=0,
            slip_accept_rate=float("nan"),
            accept_rate=float("nan"),
            phase_attempts_total=0,
            phase_improves_total=0,
            phase_best_delta_max=float("nan"),
        ),
        solution_span_counter_summary_fn=lambda _obj: dict(
            total=0.0,
            active=0.0,
            skipped=0.0,
            seconds_total=0.0,
            seconds_active=0.0,
        ),
        scorer_span_counter_summary_fn=lambda _obj: dict(
            total=0.0,
            active=0.0,
            skipped=0.0,
            seconds_total=0.0,
            seconds_active=0.0,
        ),
        span_counter_delta_fn=lambda **kwargs: dict(total=0.0, active=0.0, seconds_total=0.0),
        stage3_progress_logging_fn=lambda **kwargs: {},
        fmt_finite_float_fn=lambda v, digits=3: f"{float(v):.{int(digits)}f}"
        if np.isfinite(v)
        else "nan",
    )

    assert int(out["phaseC_rescue_eligible_starts"]) == 4
    assert int(out["phaseC_rescue_starts_attempted"]) == 4
    summaries = [dict(row) for row in out["phaseC_start_summaries"]]
    by_rank = {
        int(row["source_rank"]): row
        for row in summaries
        if str(row["source"]) == "phaseB_topk"
    }
    assert int(by_rank[4]["rescue_eligible"]) == 1
    assert int(by_rank[4]["rescue_attempted"]) == 1
    assert str(by_rank[4]["rescue_skip_reason"]) == ""
    assert int(by_rank[5]["rescue_eligible"]) == 1
    assert int(by_rank[5]["rescue_attempted"]) == 1
    assert str(by_rank[5]["rescue_skip_reason"]) == ""


def test_stage3_phasec_start_order_prioritizes_phaseb_topk_before_phasea_selected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _fake_run(**kwargs):
        init_keys = list(kwargs.get("initial_keys", []))
        key = list(map(int, init_keys[0])) if init_keys else [0, 1, 2, 0, 1, 2, 0]
        return SimpleNamespace(
            plaintext_idx=[0, 0],
            key=key,
            score=0.0,
            meta={"work": {"evals": 3}, "telemetry": {"kaeding": {}}},
        )

    monkeypatch.setattr(phase2_mod, "run", _fake_run)

    def _constant_match(_lhs: list[int], _rhs: list[int]) -> float:
        return 0.0

    target_pt = np.asarray([0, 0], dtype=np.uint8)
    phasea_rows = [
        dict(
            start_hash=f"s{idx}",
            end_hash=f"ha{idx}",
            restart_idx=idx,
            start_key=[idx % 3, (idx + 1) % 3, (idx + 2) % 3, 0, 1, 2, 0],
            end_key=[idx % 3, (idx + 1) % 3, (idx + 2) % 3, 0, 1, 2, 0],
            start_plaintext=[0, 0],
            end_plaintext=[0, 0],
            end_match=0.0,
            end_score_raw=float(-idx),
            metrics=dict(
                slip_count=0,
                slip_accept_count=0,
                slip_accept_rate=float("nan"),
                accept_rate=float("nan"),
                phase_attempts_total=0,
                phase_improves_total=0,
                phase_best_delta_max=float("nan"),
            ),
        )
        for idx in range(1, 4)
    ]

    topk_rows = [
        dict(rank=2, key_idx=[0, 1, 2, 0, 1, 2, 1], plaintext_idx=[0, 0], end_hash="hc2", source="phaseB_topk"),
        dict(rank=3, key_idx=[0, 1, 2, 1, 1, 2, 0], plaintext_idx=[0, 0], end_hash="hc3", source="phaseB_topk"),
        dict(rank=4, key_idx=[0, 2, 1, 0, 1, 2, 0], plaintext_idx=[0, 0], end_hash="hc4", source="phaseB_topk"),
        dict(rank=5, key_idx=[0, 1, 2, 0, 2, 1, 0], plaintext_idx=[0, 0], end_hash="hc5", source="phaseB_topk"),
    ]

    def _append_phaseb_topk(**kwargs) -> None:
        kwargs["payload"].extend(dict(row) for row in topk_rows)

    out = phase2_mod.run_stage3_two_phase_followup(
        tier_name="fixture_fixture_001_p2_c1_l4",
        tier_period=2,
        tier_columns=1,
        text_id=0,
        key_seed=511,
        key_len=7,
        ct_idx=np.asarray([0, 0, 0, 0], dtype=np.uint8),
        pt_idx=target_pt,
        order="col_then_sub",
        alphabet_size=3,
        direction=None,
        solve_match_threshold=0.9,
        oracle_assist_selection_effective=False,
        stage3_phaseA_experiment="a_baseline",
        stage3_phaseB_experiment="c_min_late",
        stage3_phaseB_char_pct_min_dynamic=0.4,
        stage3_phaseB_char_pct_min_source="test",
        phaseA_rows=phasea_rows,
        stage_rows=[],
        scorer_stage3_search_runtime=_SlicePreferenceScorer(),
        scorer_basin_judge_runtime=_SlicePreferenceScorer(),
        scorer_word_ngram_report_runtime=None,
        scorer_full_runtime=_SlicePreferenceScorer(),
        scorer_stage3_phaseB={},
        solver_stage3_cfg={"steps": 4, "restarts": 1, "col_batch": 4, "inner_batch": 8},
        stage3_phaseB_cfg={"steps": 4, "inner_batch": 8, "col_every": 0, "col_batch": 0},
        stage3_phaseB_top_n=4,
        stage3_phaseB_gate_delta=-1.0,
        stage3_phaseB_gate_end_gain=-1.0,
        stage3_scan_phaseA_only=False,
        stage3_span_basin_judge_k_cfg=4,
        stage3_span_basin_judge_require_span_active=False,
        stage3_span_basin_judge_dedupe_by_end_hash=True,
        stage3_span_basin_judge_tie_eps=0.0,
        stage3_span_basin_judge_tie_max_seeds=8,
        stage3_word_ngram_decision_influence=False,
        stage3_phasec_enabled=True,
        stage3_phasec_cfg={
            "steps": 1,
            "proposals_per_step": 1,
            "three_cycle_prob": 0.0,
            "rescue_enabled": False,
        },
        stage3_phasec_start_keys=5,
        stage3_phasec_seed_offset=0,
        stage3_phasec_word_ngram_tiebreak=False,
        batch_eval_chunk_size=32,
        require_batch_scoring=True,
        base_seed=2026,
        ev3_base=0,
        stage3_heartbeat_seconds=30.0,
        stage3_heartbeat_min_step=50,
        stage3_heartbeat_min_elapsed_seconds=5.0,
        stage3_hb_state={"last_emit_ts": float("-inf")},
        stage3_topk_payload=[],
        full_cipher=_SliceChangeCipher(base_key=[0, 1, 2, 0, 1, 2, 0], period=2, alphabet_size=3),
        append_stage3_topk_from_phasea_fn=lambda **kwargs: None,
        append_stage3_topk_from_kaeding_fn=_append_phaseb_topk,
        is_better_stage3_candidate_preserving_solve_fn=_is_better,
        match_ratio_fn=_constant_match,
        extract_kaeding_metrics_fn=lambda _obj: dict(
            slip_count=0,
            slip_accept_count=0,
            slip_accept_rate=float("nan"),
            accept_rate=float("nan"),
            phase_attempts_total=0,
            phase_improves_total=0,
            phase_best_delta_max=float("nan"),
        ),
        solution_span_counter_summary_fn=lambda _obj: dict(
            total=0.0,
            active=0.0,
            skipped=0.0,
            seconds_total=0.0,
            seconds_active=0.0,
        ),
        scorer_span_counter_summary_fn=lambda _obj: dict(
            total=0.0,
            active=0.0,
            skipped=0.0,
            seconds_total=0.0,
            seconds_active=0.0,
        ),
        span_counter_delta_fn=lambda **kwargs: dict(total=0.0, active=0.0, seconds_total=0.0),
        stage3_progress_logging_fn=lambda **kwargs: {},
        fmt_finite_float_fn=lambda v, digits=3: f"{float(v):.{int(digits)}f}"
        if np.isfinite(v)
        else "nan",
    )

    summaries = [dict(row) for row in out["phaseC_start_summaries"]]
    assert [str(row["source"]) for row in summaries] == [
        "stage3_best_phaseB",
        "phaseB_topk",
        "phaseB_topk",
        "phaseB_topk",
        "phaseB_topk",
    ]


def test_stage3_phaseb_tie_band_can_preserve_more_phasea_seeds(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def _fake_run(**kwargs):
        init_keys = list(kwargs.get("initial_keys", []))
        key = list(map(int, init_keys[0])) if init_keys else [0, 1, 2, 0]
        return SimpleNamespace(
            plaintext_idx=[0, 1, 2, 0],
            key=key,
            score=0.0,
            meta={"work": {"evals": 5}, "telemetry": {"kaeding": {}}},
        )

    monkeypatch.setattr(phase2_mod, "run", _fake_run)

    phasea_rows = [
        dict(
            start_hash=f"s{idx}",
            end_hash=f"h{idx}",
            restart_idx=idx,
            start_key=[0, 1, 2, 0],
            end_key=[idx % 3, (idx + 1) % 3, (idx + 2) % 3, 0],
            start_plaintext=[0, 1, 2, 0],
            end_plaintext=[0, 1, 2, 0],
            start_score_pct=0.890,
            end_score_pct=end_score,
            best_delta_pct=end_score - 0.890,
            end_score_raw=end_score,
            end_match=0.0,
            metrics=dict(
                slip_count=0,
                slip_accept_count=0,
                slip_accept_rate=float("nan"),
                accept_rate=float("nan"),
                phase_attempts_total=0,
                phase_improves_total=0,
                phase_best_delta_max=float("nan"),
            ),
        )
        for idx, end_score in enumerate((0.900, 0.897, 0.896, 0.880), start=1)
    ]

    out = phase2_mod.run_stage3_two_phase_followup(
        tier_name="fixture_fixture_001_p2_c1_l4",
        tier_period=2,
        tier_columns=1,
        text_id=0,
        key_seed=511,
        key_len=4,
        ct_idx=np.asarray([0, 0, 0, 0], dtype=np.uint8),
        pt_idx=np.asarray([0, 1, 2, 0], dtype=np.uint8),
        order="col_then_sub",
        alphabet_size=3,
        direction=None,
        solve_match_threshold=0.9,
        oracle_assist_selection_effective=False,
        stage3_phaseA_experiment="a_baseline",
        stage3_phaseB_experiment="c_min_late",
        stage3_phaseB_char_pct_min_dynamic=0.4,
        stage3_phaseB_char_pct_min_source="test",
        phaseA_rows=phasea_rows,
        stage_rows=[],
        scorer_stage3_search_runtime=_TargetScorer([0, 1, 2, 0]),
        scorer_basin_judge_runtime=_TargetScorer([0, 1, 2, 0]),
        scorer_word_ngram_report_runtime=None,
        scorer_full_runtime=_TargetScorer([0, 1, 2, 0]),
        scorer_stage3_phaseB={},
        solver_stage3_cfg={"steps": 4, "restarts": 1, "col_batch": 4, "inner_batch": 8},
        stage3_phaseB_cfg={"steps": 4, "inner_batch": 8, "col_every": 0, "col_batch": 0},
        stage3_phaseB_top_n=2,
        stage3_phaseB_gate_delta=-1.0,
        stage3_phaseB_gate_end_gain=-1.0,
        stage3_scan_phaseA_only=False,
        stage3_span_basin_judge_k_cfg=4,
        stage3_span_basin_judge_require_span_active=False,
        stage3_span_basin_judge_dedupe_by_end_hash=True,
        stage3_span_basin_judge_tie_eps=0.005,
        stage3_span_basin_judge_tie_max_seeds=4,
        stage3_word_ngram_decision_influence=False,
        stage3_phasec_enabled=False,
        stage3_phasec_cfg={},
        stage3_phasec_start_keys=0,
        stage3_phasec_seed_offset=0,
        stage3_phasec_word_ngram_tiebreak=False,
        batch_eval_chunk_size=32,
        require_batch_scoring=True,
        base_seed=2026,
        ev3_base=0,
        stage3_heartbeat_seconds=30.0,
        stage3_heartbeat_min_step=50,
        stage3_heartbeat_min_elapsed_seconds=5.0,
        stage3_hb_state={"last_emit_ts": float("-inf")},
        stage3_topk_payload=[],
        full_cipher=_DummyCipher(),
        append_stage3_topk_from_phasea_fn=lambda **kwargs: None,
        append_stage3_topk_from_kaeding_fn=lambda **kwargs: None,
        is_better_stage3_candidate_preserving_solve_fn=_is_better,
        match_ratio_fn=lambda _lhs, _rhs: 0.0,
        extract_kaeding_metrics_fn=lambda _obj: dict(
            slip_count=0,
            slip_accept_count=0,
            slip_accept_rate=float("nan"),
            accept_rate=float("nan"),
            phase_attempts_total=0,
            phase_improves_total=0,
            phase_best_delta_max=float("nan"),
        ),
        solution_span_counter_summary_fn=lambda _obj: dict(
            total=0.0,
            active=0.0,
            skipped=0.0,
            seconds_total=0.0,
            seconds_active=0.0,
        ),
        scorer_span_counter_summary_fn=lambda _obj: dict(
            total=0.0,
            active=0.0,
            skipped=0.0,
            seconds_total=0.0,
            seconds_active=0.0,
        ),
        span_counter_delta_fn=lambda **kwargs: dict(total=0.0, active=0.0, seconds_total=0.0),
        stage3_progress_logging_fn=lambda **kwargs: {},
        fmt_finite_float_fn=lambda v, digits=3: f"{float(v):.{int(digits)}f}"
        if np.isfinite(v)
        else "nan",
        key_hash_fn=lambda key_vals: f"h-{','.join(str(int(v)) for v in key_vals)}",
    )

    assert int(out["phaseB_top_n_used"]) == 4
    assert int(out["phaseB_selected_unique_end_hash"]) == 4
    text = capsys.readouterr().out
    assert "tie_band_eps=0.0050_n=4_cap=4" in text
    assert "selected_final=4" in text


def test_stage3_phasec_rescue_guard_can_reject_landing(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def _fake_run(**kwargs):
        init_keys = list(kwargs.get("initial_keys", []))
        key = list(map(int, init_keys[0])) if init_keys else [0, 1, 2, 0, 1, 2, 0]
        return SimpleNamespace(
            plaintext_idx=[0, 0],
            key=key,
            score=0.0,
            meta={"work": {"evals": 3}, "telemetry": {"kaeding": {}}},
        )

    class _GuardRejectSearchScorer:
        def batch_score(self, plaintexts: np.ndarray, wli) -> np.ndarray:
            _ = wli
            arr = np.asarray(plaintexts, dtype=np.float64)
            if arr.ndim == 1:
                arr = arr[None, :]
            return -(10.0 * arr[:, 1]) - arr[:, 0]

    monkeypatch.setattr(phase2_mod, "run", _fake_run)

    def _constant_match(_lhs: list[int], _rhs: list[int]) -> float:
        return 0.0

    base_key = [0, 1, 2, 0, 1, 2, 0]
    target_pt = np.asarray([0, 0], dtype=np.uint8)
    phasea_rows = [
        dict(
            start_hash="s0",
            end_hash="e0",
            restart_idx=0,
            start_key=list(base_key),
            end_key=list(base_key),
            start_plaintext=[0, 0],
            end_plaintext=[0, 0],
            end_match=0.0,
            end_score_raw=0.0,
            metrics=dict(
                slip_count=0,
                slip_accept_count=0,
                slip_accept_rate=float("nan"),
                accept_rate=float("nan"),
                phase_attempts_total=0,
                phase_improves_total=0,
                phase_best_delta_max=float("nan"),
            ),
        )
    ]

    out = phase2_mod.run_stage3_two_phase_followup(
        tier_name="fixture_fixture_001_p2_c1_l4",
        tier_period=2,
        tier_columns=1,
        text_id=0,
        key_seed=511,
        key_len=7,
        ct_idx=np.asarray([0, 0, 0, 0], dtype=np.uint8),
        pt_idx=target_pt,
        order="col_then_sub",
        alphabet_size=3,
        direction=None,
        solve_match_threshold=0.9,
        oracle_assist_selection_effective=False,
        stage3_phaseA_experiment="a_baseline",
        stage3_phaseB_experiment="c_min_late",
        stage3_phaseB_char_pct_min_dynamic=0.4,
        stage3_phaseB_char_pct_min_source="test",
        phaseA_rows=phasea_rows,
        stage_rows=[],
        scorer_stage3_search_runtime=_GuardRejectSearchScorer(),
        scorer_basin_judge_runtime=_SlicePreferenceScorer(),
        scorer_word_ngram_report_runtime=None,
        scorer_full_runtime=_SlicePreferenceScorer(),
        scorer_stage3_phaseB={},
        solver_stage3_cfg={"steps": 4, "restarts": 1, "col_batch": 4, "inner_batch": 8},
        stage3_phaseB_cfg={"steps": 4, "inner_batch": 8, "col_every": 0, "col_batch": 0},
        stage3_phaseB_top_n=1,
        stage3_phaseB_gate_delta=-1.0,
        stage3_phaseB_gate_end_gain=-1.0,
        stage3_scan_phaseA_only=False,
        stage3_span_basin_judge_k_cfg=1,
        stage3_span_basin_judge_require_span_active=False,
        stage3_span_basin_judge_dedupe_by_end_hash=True,
        stage3_span_basin_judge_tie_eps=0.0,
        stage3_span_basin_judge_tie_max_seeds=4,
        stage3_word_ngram_decision_influence=False,
        stage3_phasec_enabled=True,
        stage3_phasec_cfg={
            "steps": 1,
            "proposals_per_step": 1,
            "three_cycle_prob": 0.0,
            "rescue_enabled": True,
            "rescue_anchor_enabled": True,
            "rescue_max_starts": 1,
            "rescue_target_mode": "slice_probe",
            "rescue_candidates": 2,
            "rescue_slip_swaps": 1,
            "rescue_search_score_max_drop": 0.0,
        },
        stage3_phasec_start_keys=1,
        stage3_phasec_seed_offset=0,
        stage3_phasec_word_ngram_tiebreak=False,
        batch_eval_chunk_size=32,
        require_batch_scoring=True,
        base_seed=2026,
        ev3_base=0,
        stage3_heartbeat_seconds=30.0,
        stage3_heartbeat_min_step=50,
        stage3_heartbeat_min_elapsed_seconds=5.0,
        stage3_hb_state={"last_emit_ts": float("-inf")},
        stage3_topk_payload=[],
        full_cipher=_SliceChangeCipher(base_key=base_key, period=2, alphabet_size=3),
        append_stage3_topk_from_phasea_fn=lambda **kwargs: None,
        append_stage3_topk_from_kaeding_fn=lambda **kwargs: None,
        is_better_stage3_candidate_preserving_solve_fn=_is_better,
        match_ratio_fn=_constant_match,
        extract_kaeding_metrics_fn=lambda _obj: dict(
            slip_count=0,
            slip_accept_count=0,
            slip_accept_rate=float("nan"),
            accept_rate=float("nan"),
            phase_attempts_total=0,
            phase_improves_total=0,
            phase_best_delta_max=float("nan"),
        ),
        solution_span_counter_summary_fn=lambda _obj: dict(
            total=0.0,
            active=0.0,
            skipped=0.0,
            seconds_total=0.0,
            seconds_active=0.0,
        ),
        scorer_span_counter_summary_fn=lambda _obj: dict(
            total=0.0,
            active=0.0,
            skipped=0.0,
            seconds_total=0.0,
            seconds_active=0.0,
        ),
        span_counter_delta_fn=lambda **kwargs: dict(total=0.0, active=0.0, seconds_total=0.0),
        stage3_progress_logging_fn=lambda **kwargs: {},
        fmt_finite_float_fn=lambda v, digits=3: f"{float(v):.{int(digits)}f}"
        if np.isfinite(v)
        else "nan",
    )

    assert int(out["phaseC_rescue_ran"]) == 1
    assert int(out["phaseC_rescue_starts_attempted"]) == 1
    assert int(out["phaseC_rescue_applied_starts"]) == 0
    assert int(out["phaseC_rescue_guard_search_evals"]) > 0
    assert int(out["phaseC_rescue_guard_search_passes"]) == 0
    assert int(out["phaseC_rescue_guard_search_rejects"]) > 0
    summaries = list(out["phaseC_start_summaries"])
    assert len(summaries) == 1
    assert int(summaries[0]["rescue_attempted"]) == 1
    assert int(summaries[0]["rescue_applied"]) == 0
    assert summaries[0]["rescue_guard_search_best_score"] is None
    assert int(summaries[0]["rescue_guard_search_passed"]) == 0
    text = capsys.readouterr().out
    assert "guard_search_passed=0" in text


def test_stage3_phasec_mixes_best_topk_and_phasea_sources(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def _fake_run(**kwargs):
        _ = kwargs
        key = [0, 1, 2, 0, 1, 2, 0]
        pt = [0, 1, 2, 0]
        return SimpleNamespace(
            plaintext_idx=pt,
            key=key,
            score=0.0,
            meta={"work": {"evals": 9}, "telemetry": {"kaeding": {}}},
        )

    monkeypatch.setattr(phase2_mod, "run", _fake_run)

    target_pt = np.asarray([0, 1, 2, 0], dtype=np.uint8)
    phasea_rows = [
        dict(
            start_hash="sa",
            end_hash="ha",
            restart_idx=0,
            start_key=[1, 0, 2, 0, 1, 2, 0],
            end_key=[1, 0, 2, 0, 1, 2, 0],
            start_plaintext=[1, 0, 2, 0],
            end_plaintext=[1, 0, 2, 0],
            end_match=0.50,
            end_score_raw=-5.0,
            metrics=dict(
                slip_count=0,
                slip_accept_count=0,
                slip_accept_rate=float("nan"),
                accept_rate=float("nan"),
                phase_attempts_total=0,
                phase_improves_total=0,
                phase_best_delta_max=float("nan"),
            ),
        ),
        dict(
            start_hash="sb",
            end_hash="hb",
            restart_idx=1,
            start_key=[0, 2, 2, 0, 1, 2, 0],
            end_key=[0, 2, 2, 0, 1, 2, 0],
            start_plaintext=[0, 2, 2, 0],
            end_plaintext=[0, 2, 2, 0],
            end_match=0.75,
            end_score_raw=-2.0,
            metrics=dict(
                slip_count=0,
                slip_accept_count=0,
                slip_accept_rate=float("nan"),
                accept_rate=float("nan"),
                phase_attempts_total=0,
                phase_improves_total=0,
                phase_best_delta_max=float("nan"),
            ),
        ),
    ]
    injected_topk = [
        dict(
            rank=1,
            key_idx=[0, 1, 1, 0, 1, 2, 0],
            plaintext_idx=[0, 1, 1, 0],
            end_hash="hc",
            source="phaseB_topk",
        ),
        dict(
            rank=2,
            key_idx=[0, 1, 2, 1, 1, 2, 0],
            plaintext_idx=[0, 1, 2, 1],
            end_hash="hd",
            source="phaseB_topk",
        ),
    ]

    def _append_phaseb_topk(**kwargs) -> None:
        payload = kwargs["payload"]
        for row in injected_topk:
            payload.append(dict(row))

    out = phase2_mod.run_stage3_two_phase_followup(
        tier_name="fixture_fixture_001_p2_c1_l4",
        tier_period=2,
        tier_columns=1,
        text_id=0,
        key_seed=511,
        key_len=7,
        ct_idx=np.asarray([0, 0, 0, 0], dtype=np.uint8),
        pt_idx=target_pt,
        order="col_then_sub",
        alphabet_size=3,
        direction=None,
        solve_match_threshold=0.9,
        oracle_assist_selection_effective=False,
        stage3_phaseA_experiment="a_baseline",
        stage3_phaseB_experiment="c_min_late",
        stage3_phaseB_char_pct_min_dynamic=0.4,
        stage3_phaseB_char_pct_min_source="test",
        phaseA_rows=phasea_rows,
        stage_rows=[],
        scorer_stage3_search_runtime=_TargetScorer([0, 1, 2, 0]),
        scorer_basin_judge_runtime=_TargetScorer([0, 1, 2, 0]),
        scorer_word_ngram_report_runtime=None,
        scorer_full_runtime=_TargetScorer([0, 1, 2, 0]),
        scorer_stage3_phaseB={},
        solver_stage3_cfg={"steps": 4, "restarts": 1, "col_batch": 4, "inner_batch": 8},
        stage3_phaseB_cfg={"steps": 4, "inner_batch": 8, "col_every": 0, "col_batch": 0},
        stage3_phaseB_top_n=2,
        stage3_phaseB_gate_delta=-1.0,
        stage3_phaseB_gate_end_gain=-1.0,
        stage3_scan_phaseA_only=False,
        stage3_span_basin_judge_k_cfg=2,
        stage3_span_basin_judge_require_span_active=False,
        stage3_span_basin_judge_dedupe_by_end_hash=True,
        stage3_span_basin_judge_tie_eps=0.0,
        stage3_span_basin_judge_tie_max_seeds=4,
        stage3_word_ngram_decision_influence=False,
        stage3_phasec_enabled=True,
        stage3_phasec_cfg={"steps": 2, "proposals_per_step": 2, "three_cycle_prob": 0.0},
        stage3_phasec_start_keys=4,
        stage3_phasec_seed_offset=0,
        stage3_phasec_word_ngram_tiebreak=False,
        batch_eval_chunk_size=32,
        require_batch_scoring=True,
        base_seed=2026,
        ev3_base=0,
        stage3_heartbeat_seconds=30.0,
        stage3_heartbeat_min_step=50,
        stage3_heartbeat_min_elapsed_seconds=5.0,
        stage3_hb_state={"last_emit_ts": float("-inf")},
        stage3_topk_payload=[],
        full_cipher=_DummyCipher(),
        append_stage3_topk_from_phasea_fn=lambda **kwargs: None,
        append_stage3_topk_from_kaeding_fn=_append_phaseb_topk,
        is_better_stage3_candidate_preserving_solve_fn=_is_better,
        match_ratio_fn=_match_ratio,
        extract_kaeding_metrics_fn=lambda _obj: dict(
            slip_count=0,
            slip_accept_count=0,
            slip_accept_rate=float("nan"),
            accept_rate=float("nan"),
            phase_attempts_total=0,
            phase_improves_total=0,
            phase_best_delta_max=float("nan"),
        ),
        solution_span_counter_summary_fn=lambda _obj: dict(
            total=0.0,
            active=0.0,
            skipped=0.0,
            seconds_total=0.0,
            seconds_active=0.0,
        ),
        scorer_span_counter_summary_fn=lambda _obj: dict(
            total=0.0,
            active=0.0,
            skipped=0.0,
            seconds_total=0.0,
            seconds_active=0.0,
        ),
        span_counter_delta_fn=lambda **kwargs: dict(total=0.0, active=0.0, seconds_total=0.0),
        stage3_progress_logging_fn=lambda **kwargs: {},
        fmt_finite_float_fn=lambda v, digits=3: f"{float(v):.{int(digits)}f}"
        if np.isfinite(v)
        else "nan",
        key_hash_fn=lambda key_vals: f"h-{','.join(str(int(v)) for v in key_vals[:4])}",
    )

    assert int(out["phaseB_selected_unique_end_hash"]) == 2
    assert int(out["phaseB_topk_saved_count"]) == 2
    assert int(out["phaseC_candidate_pool_count"]) == 5
    assert int(out["phaseC_candidate_pool_unique_keys"]) == 5
    assert int(out["phaseC_rescue_ran"]) == 0
    assert int(out["phaseC_rescue_starts_attempted"]) == 0
    assert dict(out["phaseC_start_source_counts"]) == {
        "stage3_best_phaseB": 1,
        "phaseB_topk": 2,
        "phaseA_selected": 1,
    }
    summaries = list(out["phaseC_start_summaries"])
    assert len(summaries) == 4
    assert [str(row["source"]) for row in summaries] == [
        "stage3_best_phaseB",
        "phaseB_topk",
        "phaseB_topk",
        "phaseA_selected",
    ]
    assert all(int(row["rescue_attempted"]) == 0 for row in summaries)
    assert all("match_gain" in row for row in summaries)
    assert all("score_gain" in row for row in summaries)
    text = capsys.readouterr().out
    assert "candidate_pool=5" in text
    assert "start_sources={'stage3_best_phaseB': 1, 'phaseB_topk': 2, 'phaseA_selected': 1}" in text
    assert "source=stage3_best_phaseB" in text
    assert "source=phaseB_topk" in text
    assert "source=phaseA_selected" in text
    assert "stage3-phaseC-finish-start" in text


def test_stage3_phasec_balanced_start_policy_round_robins_sources(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def _fake_run(**kwargs):
        _ = kwargs
        key = [0, 1, 2, 0, 1, 2, 0]
        pt = [0, 1, 2, 0]
        return SimpleNamespace(
            plaintext_idx=pt,
            key=key,
            score=0.0,
            meta={"work": {"evals": 9}, "telemetry": {"kaeding": {}}},
        )

    monkeypatch.setattr(phase2_mod, "run", _fake_run)

    target_pt = np.asarray([0, 1, 2, 0], dtype=np.uint8)
    phasea_rows = [
        dict(
            start_hash="sa",
            end_hash="ha",
            restart_idx=0,
            start_key=[1, 0, 2, 0, 1, 2, 0],
            end_key=[1, 0, 2, 0, 1, 2, 0],
            start_plaintext=[1, 0, 2, 0],
            end_plaintext=[1, 0, 2, 0],
            end_match=0.50,
            end_score_raw=-5.0,
            metrics=dict(
                slip_count=0,
                slip_accept_count=0,
                slip_accept_rate=float("nan"),
                accept_rate=float("nan"),
                phase_attempts_total=0,
                phase_improves_total=0,
                phase_best_delta_max=float("nan"),
            ),
        ),
        dict(
            start_hash="sb",
            end_hash="hb",
            restart_idx=1,
            start_key=[0, 2, 2, 0, 1, 2, 0],
            end_key=[0, 2, 2, 0, 1, 2, 0],
            start_plaintext=[0, 2, 2, 0],
            end_plaintext=[0, 2, 2, 0],
            end_match=0.75,
            end_score_raw=-2.0,
            metrics=dict(
                slip_count=0,
                slip_accept_count=0,
                slip_accept_rate=float("nan"),
                accept_rate=float("nan"),
                phase_attempts_total=0,
                phase_improves_total=0,
                phase_best_delta_max=float("nan"),
            ),
        ),
    ]
    injected_topk = [
        dict(
            rank=1,
            key_idx=[0, 1, 1, 0, 1, 2, 0],
            plaintext_idx=[0, 1, 1, 0],
            end_hash="hc",
            source="phaseB_topk",
        ),
        dict(
            rank=2,
            key_idx=[0, 1, 2, 1, 1, 2, 0],
            plaintext_idx=[0, 1, 2, 1],
            end_hash="hd",
            source="phaseB_topk",
        ),
    ]

    def _append_phaseb_topk(**kwargs) -> None:
        payload = kwargs["payload"]
        for row in injected_topk:
            payload.append(dict(row))

    out = phase2_mod.run_stage3_two_phase_followup(
        tier_name="fixture_fixture_001_p2_c1_l4",
        tier_period=2,
        tier_columns=1,
        text_id=0,
        key_seed=511,
        key_len=7,
        ct_idx=np.asarray([0, 0, 0, 0], dtype=np.uint8),
        pt_idx=target_pt,
        order="col_then_sub",
        alphabet_size=3,
        direction=None,
        solve_match_threshold=0.9,
        oracle_assist_selection_effective=False,
        stage3_phaseA_experiment="a_baseline",
        stage3_phaseB_experiment="c_min_late",
        stage3_phaseB_char_pct_min_dynamic=0.4,
        stage3_phaseB_char_pct_min_source="test",
        phaseA_rows=phasea_rows,
        stage_rows=[],
        scorer_stage3_search_runtime=_TargetScorer([0, 1, 2, 0]),
        scorer_basin_judge_runtime=_TargetScorer([0, 1, 2, 0]),
        scorer_word_ngram_report_runtime=None,
        scorer_full_runtime=_TargetScorer([0, 1, 2, 0]),
        scorer_stage3_phaseB={},
        solver_stage3_cfg={"steps": 4, "restarts": 1, "col_batch": 4, "inner_batch": 8},
        stage3_phaseB_cfg={"steps": 4, "inner_batch": 8, "col_every": 0, "col_batch": 0},
        stage3_phaseB_top_n=2,
        stage3_phaseB_gate_delta=-1.0,
        stage3_phaseB_gate_end_gain=-1.0,
        stage3_scan_phaseA_only=False,
        stage3_span_basin_judge_k_cfg=2,
        stage3_span_basin_judge_require_span_active=False,
        stage3_span_basin_judge_dedupe_by_end_hash=True,
        stage3_span_basin_judge_tie_eps=0.0,
        stage3_span_basin_judge_tie_max_seeds=4,
        stage3_word_ngram_decision_influence=False,
        stage3_phasec_enabled=True,
        stage3_phasec_cfg={"steps": 2, "proposals_per_step": 2, "three_cycle_prob": 0.0},
        stage3_phasec_start_keys=4,
        stage3_phasec_seed_offset=0,
        stage3_phasec_word_ngram_tiebreak=False,
        stage3_phasec_start_policy="balanced_sources_v1",
        batch_eval_chunk_size=32,
        require_batch_scoring=True,
        base_seed=2026,
        ev3_base=0,
        stage3_heartbeat_seconds=30.0,
        stage3_heartbeat_min_step=50,
        stage3_heartbeat_min_elapsed_seconds=5.0,
        stage3_hb_state={"last_emit_ts": float("-inf")},
        stage3_topk_payload=[],
        full_cipher=_DummyCipher(),
        append_stage3_topk_from_phasea_fn=lambda **kwargs: None,
        append_stage3_topk_from_kaeding_fn=_append_phaseb_topk,
        is_better_stage3_candidate_preserving_solve_fn=_is_better,
        match_ratio_fn=_match_ratio,
        extract_kaeding_metrics_fn=lambda _obj: dict(
            slip_count=0,
            slip_accept_count=0,
            slip_accept_rate=float("nan"),
            accept_rate=float("nan"),
            phase_attempts_total=0,
            phase_improves_total=0,
            phase_best_delta_max=float("nan"),
        ),
        solution_span_counter_summary_fn=lambda _obj: dict(
            total=0.0,
            active=0.0,
            skipped=0.0,
            seconds_total=0.0,
            seconds_active=0.0,
        ),
        scorer_span_counter_summary_fn=lambda _obj: dict(
            total=0.0,
            active=0.0,
            skipped=0.0,
            seconds_total=0.0,
            seconds_active=0.0,
        ),
        span_counter_delta_fn=lambda **kwargs: dict(total=0.0, active=0.0, seconds_total=0.0),
        stage3_progress_logging_fn=lambda **kwargs: {},
        fmt_finite_float_fn=lambda v, digits=3: f"{float(v):.{int(digits)}f}"
        if np.isfinite(v)
        else "nan",
        key_hash_fn=lambda key_vals: f"h-{','.join(str(int(v)) for v in key_vals[:4])}",
    )

    assert str(out["phaseC_start_policy"]) == "balanced_sources_v1"
    assert dict(out["phaseC_start_source_counts"]) == {
        "stage3_best_phaseB": 1,
        "phaseB_topk": 2,
        "phaseA_selected": 1,
    }
    summaries = list(out["phaseC_start_summaries"])
    assert len(summaries) == 4
    assert [str(row["source"]) for row in summaries] == [
        "stage3_best_phaseB",
        "phaseB_topk",
        "phaseA_selected",
        "phaseB_topk",
    ]
    text = capsys.readouterr().out
    assert "start_policy=balanced_sources_v1" in text


def test_stage3_phasec_novel_challenger_policy_forces_distinct_challengers_from_widened_pool(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def _fake_run(**kwargs):
        init_keys = list(kwargs.get("initial_keys", []))
        key = list(map(int, init_keys[0])) if init_keys else ([0] * 30)
        return SimpleNamespace(
            plaintext_idx=[0, 0, 0],
            key=key,
            score=0.0,
            meta={"work": {"evals": 4}, "telemetry": {"kaeding": {}}},
        )

    monkeypatch.setattr(phase2_mod, "run", _fake_run)

    empty_metrics = {
        "slip_count": 0,
        "slip_accept_count": 0,
        "slip_accept_rate": float("nan"),
        "accept_rate": float("nan"),
        "phase_attempts_total": 0,
        "phase_improves_total": 0,
        "phase_best_delta_max": float("nan"),
    }
    key_anchor = [0] * 30
    key_tail_1 = ([0] * 27) + [1, 0, 0]
    key_tail_2 = ([0] * 27) + [2, 0, 0]
    key_novel_1 = [1] * 30
    key_novel_2 = [2] * 30
    phasea_rows = [
        dict(
            start_hash="sa",
            end_hash="anchor",
            end_key=list(key_anchor),
            end_plaintext=[0, 1, 2, 0],
            start_score_pct=0.10,
            end_score_pct=0.95,
            end_match=0.10,
            best_delta_pct=0.85,
            end_score_raw=0.11,
            restart_idx=0,
            metrics=dict(empty_metrics),
        ),
        dict(
            start_hash="sb",
            end_hash="novel1",
            end_key=list(key_novel_1),
            end_plaintext=[0, 1, 2, 0],
            start_score_pct=0.10,
            end_score_pct=0.94,
            end_match=0.10,
            best_delta_pct=0.84,
            end_score_raw=0.10,
            restart_idx=1,
            metrics=dict(empty_metrics),
        ),
        dict(
            start_hash="sc",
            end_hash="novel2",
            end_key=list(key_novel_2),
            end_plaintext=[0, 1, 2, 0],
            start_score_pct=0.10,
            end_score_pct=0.93,
            end_match=0.10,
            best_delta_pct=0.83,
            end_score_raw=0.09,
            restart_idx=2,
            metrics=dict(empty_metrics),
        ),
    ]
    injected_topk = [
        dict(
            rank=1,
            key_idx=list(key_tail_1),
            plaintext_idx=[0, 1, 2, 0],
            end_hash="tail1",
            source="phaseB_topk",
        ),
        dict(
            rank=2,
            key_idx=list(key_tail_2),
            plaintext_idx=[0, 1, 2, 0],
            end_hash="tail2",
            source="phaseB_topk",
        ),
    ]

    def _append_phaseb_topk(**kwargs) -> None:
        payload = kwargs["payload"]
        for row in injected_topk:
            payload.append(dict(row))

    common_kwargs = dict(
        tier_name="fixture_fixture_001_p3_c1_l3",
        tier_period=3,
        tier_columns=1,
        text_id=0,
        key_seed=411,
        key_len=30,
        ct_idx=np.asarray([0, 0, 0], dtype=np.uint8),
        pt_idx=np.asarray([0, 0, 0], dtype=np.uint8),
        order="col_then_sub",
        alphabet_size=10,
        direction=no_wli_runner.Direction.LTR,
        solve_match_threshold=0.9,
        oracle_assist_selection_effective=False,
        stage3_phaseA_experiment="a_baseline",
        stage3_phaseB_experiment="c_min_late",
        stage3_phaseB_char_pct_min_dynamic=0.4,
        stage3_phaseB_char_pct_min_source="test",
        phaseA_rows=phasea_rows,
        stage_rows=[],
        scorer_stage3_search_runtime=_ConstantScorer(),
        scorer_basin_judge_runtime=_ConstantScorer(),
        scorer_word_ngram_report_runtime=None,
        scorer_full_runtime=_ConstantScorer(),
        scorer_stage3_phaseB={},
        solver_stage3_cfg={"steps": 4, "restarts": 1, "col_batch": 4, "inner_batch": 8},
        stage3_phaseB_cfg={"steps": 4, "inner_batch": 8, "col_every": 0, "col_batch": 0},
        stage3_phaseB_top_n=32,
        stage3_phaseB_gate_delta=-1.0,
        stage3_phaseB_gate_end_gain=-1.0,
        stage3_scan_phaseA_only=False,
        stage3_span_basin_judge_k_cfg=3,
        stage3_span_basin_judge_require_span_active=False,
        stage3_span_basin_judge_dedupe_by_end_hash=True,
        stage3_span_basin_judge_tie_eps=0.0,
        stage3_span_basin_judge_tie_max_seeds=8,
        stage3_word_ngram_decision_influence=False,
        stage3_phasec_enabled=True,
        stage3_phasec_cfg={"steps": 2, "proposals_per_step": 2, "three_cycle_prob": 0.0},
        stage3_phasec_start_keys=4,
        stage3_phasec_seed_offset=0,
        stage3_phasec_word_ngram_tiebreak=False,
        batch_eval_chunk_size=32,
        require_batch_scoring=True,
        base_seed=2026,
        ev3_base=0,
        stage3_heartbeat_seconds=30.0,
        stage3_heartbeat_min_step=50,
        stage3_heartbeat_min_elapsed_seconds=5.0,
        stage3_hb_state={"last_emit_ts": float("-inf")},
        stage3_topk_payload=[],
        full_cipher=_SliceChangeCipher(
            base_key=list(key_anchor),
            period=3,
            alphabet_size=10,
        ),
        append_stage3_topk_from_phasea_fn=lambda **kwargs: None,
        append_stage3_topk_from_kaeding_fn=_append_phaseb_topk,
        is_better_stage3_candidate_preserving_solve_fn=_is_better,
        match_ratio_fn=_match_ratio,
        extract_kaeding_metrics_fn=lambda _obj: dict(empty_metrics),
        solution_span_counter_summary_fn=lambda _obj: dict(
            total=0.0,
            active=0.0,
            skipped=0.0,
            seconds_total=0.0,
            seconds_active=0.0,
        ),
        scorer_span_counter_summary_fn=lambda _obj: dict(
            total=0.0,
            active=0.0,
            skipped=0.0,
            seconds_total=0.0,
            seconds_active=0.0,
        ),
        span_counter_delta_fn=lambda **kwargs: dict(total=0.0, active=0.0, seconds_total=0.0),
        stage3_progress_logging_fn=lambda **kwargs: {},
        fmt_finite_float_fn=lambda v, digits=3: f"{float(v):.{int(digits)}f}"
        if np.isfinite(v)
        else "nan",
        key_hash_fn=lambda key_vals: f"h-{','.join(str(int(v)) for v in key_vals[:6])}",
    )

    control = phase2_mod.run_stage3_two_phase_followup(
        **common_kwargs,
        stage3_phasec_start_policy="source_order",
        stage3_phaseb_family_preservation_policy="off",
        stage3_phaseb_family_view_id="prefix_hamming_le_24",
        stage3_phaseb_family_reserved_slots=0,
    )
    candidate = phase2_mod.run_stage3_two_phase_followup(
        **common_kwargs,
        stage3_phasec_start_policy="novel_challenger_v1",
        stage3_phaseb_family_preservation_policy="off",
        stage3_phaseb_family_view_id="prefix_hamming_le_24",
        stage3_phaseb_family_reserved_slots=0,
    )

    assert str(control["phaseC_start_policy"]) == "source_order"
    assert str(candidate["phaseC_start_policy"]) == "novel_challenger_v1"
    assert int(control["phaseC_candidate_pool_count"]) == int(
        candidate["phaseC_candidate_pool_count"]
    )
    assert dict(control["phaseC_candidate_pool_source_counts"]) == dict(
        candidate["phaseC_candidate_pool_source_counts"]
    )
    assert str(candidate["phaseC_novel_view_id"]) == "prefix_hamming_le_24"
    assert str(candidate["phaseC_anchor_candidate_hash"]) != ""
    assert int(candidate["phaseC_candidate_pool_eligible_novel_count"]) == 2
    assert int(candidate["phaseC_candidate_pool_eligible_novel_row_count"]) == 2
    assert dict(candidate["phaseC_candidate_pool_eligible_novel_source_counts"]) == {
        "phaseA_selected": 2
    }
    assert int(control["phaseC_selected_novel_challenger_count"]) == 0
    assert int(candidate["phaseC_selected_novel_challenger_count"]) == 2
    assert int(control["phaseC_start_eligible_novel_count"]) == 1
    assert int(candidate["phaseC_start_eligible_novel_count"]) == 2
    assert int(control["phaseC_eligible_novel_not_selected_count"]) == 1
    assert int(candidate["phaseC_eligible_novel_not_selected_count"]) == 0
    assert list(candidate["phaseC_selected_novel_challenger_hashes"]) == [
        "novel1",
        "novel2",
    ]

    control_summaries = [dict(row) for row in control["phaseC_start_summaries"]]
    candidate_summaries = [dict(row) for row in candidate["phaseC_start_summaries"]]
    assert [str(row["candidate_hash"]) for row in control_summaries] == [
        "h-0,0,0,0,0,0",
        "tail1",
        "tail2",
        "novel1",
    ]
    assert [str(row["candidate_hash"]) for row in candidate_summaries] == [
        "h-0,0,0,0,0,0",
        "novel1",
        "novel2",
        "tail1",
    ]
    assert [str(row["selection_bucket"]) for row in candidate_summaries] == [
        "anchor",
        "novel_reserved",
        "novel_reserved",
        "legacy_fill",
    ]
    assert [int(row["selected_by_novel_policy"]) for row in candidate_summaries] == [
        0,
        1,
        1,
        0,
    ]
    assert [int(row["eligible_novel_challenger"]) for row in candidate_summaries] == [
        0,
        1,
        1,
        0,
    ]
    assert int(candidate_summaries[1]["novelty_distance_to_anchor"]) == 29
    assert int(candidate_summaries[2]["novelty_distance_to_anchor"]) == 29
    assert (
        int(candidate_summaries[2]["novelty_min_distance_to_selected_challenger"])
        == 29
    )

    text = capsys.readouterr().out
    assert "start_policy=novel_challenger_v1" in text
    assert "eligible_novel_pool=2" in text
    assert "selected_novel=2" in text


def test_stage3_phasec_anchor_family_reserved_policy_pulls_same_family_starts_from_pool(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def _fake_run(**kwargs):
        init_keys = list(kwargs.get("initial_keys", []))
        key = list(map(int, init_keys[0])) if init_keys else ([0] * 30)
        return SimpleNamespace(
            plaintext_idx=[0, 0, 0],
            key=key,
            score=0.0,
            meta={"work": {"evals": 4}, "telemetry": {"kaeding": {}}},
        )

    monkeypatch.setattr(phase2_mod, "run", _fake_run)

    def _rows_share_family(lhs, rhs, **_kwargs):
        lhs_hash = str(lhs.get("candidate_hash", "") or lhs.get("end_hash", ""))
        rhs_hash = str(rhs.get("candidate_hash", "") or rhs.get("end_hash", ""))
        if rhs_hash == "h-0,0,0,0,0,0" and lhs_hash in {
            "anchor_family_seed",
            "anchor_family_same1",
            "anchor_family_same2",
        }:
            return True
        return False

    monkeypatch.setattr(phase2_mod, "rows_share_family", _rows_share_family)

    empty_metrics = {
        "slip_count": 0,
        "slip_accept_count": 0,
        "slip_accept_rate": float("nan"),
        "accept_rate": float("nan"),
        "phase_attempts_total": 0,
        "phase_improves_total": 0,
        "phase_best_delta_max": float("nan"),
    }
    key_anchor = ([1] * 26) + ([0] * 4)
    key_same_1 = ([0] + ([1] * 25) + ([0] * 4))
    key_same_2 = ([1, 0] + ([1] * 24) + ([0] * 4))
    key_far_1 = [0] * 30
    key_far_2 = ([2] * 26) + ([0] * 4)
    phasea_rows = [
        dict(
            start_hash="sa",
            end_hash="anchor_family_seed",
            end_key=list(key_anchor),
            end_plaintext=[0, 1, 2, 0],
            start_score_pct=0.10,
            end_score_pct=0.95,
            end_match=0.10,
            best_delta_pct=0.85,
            end_score_raw=0.11,
            restart_idx=0,
            metrics=dict(empty_metrics),
        ),
        dict(
            start_hash="sb",
            end_hash="anchor_family_same1",
            end_key=list(key_same_1),
            end_plaintext=[0, 1, 2, 0],
            start_score_pct=0.10,
            end_score_pct=0.90,
            end_match=0.10,
            best_delta_pct=0.80,
            end_score_raw=0.10,
            restart_idx=1,
            metrics=dict(empty_metrics),
        ),
        dict(
            start_hash="sc",
            end_hash="anchor_family_same2",
            end_key=list(key_same_2),
            end_plaintext=[0, 1, 2, 0],
            start_score_pct=0.10,
            end_score_pct=0.89,
            end_match=0.10,
            best_delta_pct=0.79,
            end_score_raw=0.09,
            restart_idx=2,
            metrics=dict(empty_metrics),
        ),
        dict(
            start_hash="sd",
            end_hash="far1",
            end_key=list(key_far_1),
            end_plaintext=[0, 1, 2, 0],
            start_score_pct=0.10,
            end_score_pct=0.88,
            end_match=0.10,
            best_delta_pct=0.78,
            end_score_raw=0.08,
            restart_idx=3,
            metrics=dict(empty_metrics),
        ),
    ]
    injected_topk = [
        dict(
            rank=1,
            key_idx=list(key_far_1),
            plaintext_idx=[0, 1, 2, 0],
            end_hash="tail1",
            source="phaseB_topk",
        ),
        dict(
            rank=2,
            key_idx=list(key_far_2),
            plaintext_idx=[0, 1, 2, 0],
            end_hash="tail2",
            source="phaseB_topk",
        ),
    ]

    def _append_phaseb_topk(**kwargs) -> None:
        payload = kwargs["payload"]
        for row in injected_topk:
            payload.append(dict(row))

    common_kwargs = dict(
        tier_name="fixture_fixture_001_p3_c1_l3",
        tier_period=3,
        tier_columns=1,
        text_id=0,
        key_seed=411,
        key_len=30,
        ct_idx=np.asarray([0, 0, 0], dtype=np.uint8),
        pt_idx=np.asarray([0, 0, 0], dtype=np.uint8),
        order="col_then_sub",
        alphabet_size=10,
        direction=no_wli_runner.Direction.LTR,
        solve_match_threshold=0.9,
        oracle_assist_selection_effective=False,
        stage3_phaseA_experiment="a_baseline",
        stage3_phaseB_experiment="c_min_late",
        stage3_phaseB_char_pct_min_dynamic=0.4,
        stage3_phaseB_char_pct_min_source="test",
        phaseA_rows=phasea_rows,
        stage_rows=[],
        scorer_stage3_search_runtime=_ConstantScorer(),
        scorer_basin_judge_runtime=_ConstantScorer(),
        scorer_word_ngram_report_runtime=None,
        scorer_full_runtime=_ConstantScorer(),
        scorer_stage3_phaseB={},
        solver_stage3_cfg={"steps": 4, "restarts": 1, "col_batch": 4, "inner_batch": 8},
        stage3_phaseB_cfg={"steps": 4, "inner_batch": 8, "col_every": 0, "col_batch": 0},
        stage3_phaseB_top_n=32,
        stage3_phaseB_gate_delta=-1.0,
        stage3_phaseB_gate_end_gain=-1.0,
        stage3_scan_phaseA_only=False,
        stage3_span_basin_judge_k_cfg=3,
        stage3_span_basin_judge_require_span_active=False,
        stage3_span_basin_judge_dedupe_by_end_hash=True,
        stage3_span_basin_judge_tie_eps=0.0,
        stage3_span_basin_judge_tie_max_seeds=8,
        stage3_word_ngram_decision_influence=False,
        stage3_phasec_enabled=True,
        stage3_phasec_cfg={"steps": 2, "proposals_per_step": 2, "three_cycle_prob": 0.0},
        stage3_phasec_start_keys=4,
        stage3_phasec_seed_offset=0,
        stage3_phasec_word_ngram_tiebreak=False,
        batch_eval_chunk_size=32,
        require_batch_scoring=True,
        base_seed=2026,
        ev3_base=0,
        stage3_heartbeat_seconds=30.0,
        stage3_heartbeat_min_step=50,
        stage3_heartbeat_min_elapsed_seconds=5.0,
        stage3_hb_state={"last_emit_ts": float("-inf")},
        stage3_topk_payload=[],
        full_cipher=_SliceChangeCipher(
            base_key=list(key_anchor),
            period=3,
            alphabet_size=10,
        ),
        append_stage3_topk_from_phasea_fn=lambda **kwargs: None,
        append_stage3_topk_from_kaeding_fn=_append_phaseb_topk,
        is_better_stage3_candidate_preserving_solve_fn=_is_better,
        match_ratio_fn=_match_ratio,
        extract_kaeding_metrics_fn=lambda _obj: dict(empty_metrics),
        solution_span_counter_summary_fn=lambda _obj: dict(
            total=0.0,
            active=0.0,
            skipped=0.0,
            seconds_total=0.0,
            seconds_active=0.0,
        ),
        scorer_span_counter_summary_fn=lambda _obj: dict(
            total=0.0,
            active=0.0,
            skipped=0.0,
            seconds_total=0.0,
            seconds_active=0.0,
        ),
        span_counter_delta_fn=lambda **kwargs: dict(total=0.0, active=0.0, seconds_total=0.0),
        stage3_progress_logging_fn=lambda **kwargs: {},
        fmt_finite_float_fn=lambda v, digits=3: f"{float(v):.{int(digits)}f}"
        if np.isfinite(v)
        else "nan",
        key_hash_fn=lambda key_vals: f"h-{','.join(str(int(v)) for v in key_vals[:6])}",
    )

    control = phase2_mod.run_stage3_two_phase_followup(
        **common_kwargs,
        stage3_phasec_start_policy="source_order",
        stage3_phaseb_family_preservation_policy="off",
        stage3_phaseb_family_view_id="prefix_hamming_le_24",
        stage3_phaseb_family_reserved_slots=0,
    )
    candidate = phase2_mod.run_stage3_two_phase_followup(
        **common_kwargs,
        stage3_phasec_start_policy="anchor_family_reserved_v1",
        stage3_phaseb_family_preservation_policy="off",
        stage3_phaseb_family_view_id="prefix_hamming_le_24",
        stage3_phaseb_family_reserved_slots=0,
    )

    assert str(control["phaseC_start_policy"]) == "source_order"
    assert str(candidate["phaseC_start_policy"]) == "anchor_family_reserved_v1"
    control_summaries = [dict(row) for row in control["phaseC_start_summaries"]]
    candidate_summaries = [dict(row) for row in candidate["phaseC_start_summaries"]]
    assert str(control_summaries[0]["candidate_hash"]) == str(
        candidate_summaries[0]["candidate_hash"]
    )
    assert [str(row["candidate_hash"]) for row in control_summaries[1:]] == [
        "tail2",
        "anchor_family_seed",
        "anchor_family_same1",
    ]
    assert [str(row["selection_bucket"]) for row in candidate_summaries] == [
        "anchor",
        "anchor_family_reserved",
        "anchor_family_reserved",
        "legacy_fill",
    ]
    assert [str(row["source"]) for row in candidate_summaries[1:3]] == [
        "phaseA_selected",
        "phaseA_selected",
    ]
    assert {
        str(row["candidate_hash"]) for row in candidate_summaries[1:3]
    } == {
        "anchor_family_seed",
        "anchor_family_same1",
    }
    assert str(candidate_summaries[3]["candidate_hash"]) == "tail2"
    assert [str(row["selection_bucket"]) for row in candidate_summaries] == [
        "anchor",
        "anchor_family_reserved",
        "anchor_family_reserved",
        "legacy_fill",
    ]
    assert [int(row["selected_by_anchor_family_policy"]) for row in candidate_summaries] == [
        0,
        1,
        1,
        0,
    ]
    assert [int(row["selected_by_novel_policy"]) for row in candidate_summaries] == [
        0,
        0,
        0,
        0,
    ]
    text = capsys.readouterr().out
    assert "start_policy=anchor_family_reserved_v1" in text


def test_stage3_phasec_phaseb_topk_anchor_swap_policy_moves_first_topk_row_into_anchor_lane(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def _fake_run(**kwargs):
        init_keys = list(kwargs.get("initial_keys", []))
        key = list(map(int, init_keys[0])) if init_keys else ([0] * 30)
        return SimpleNamespace(
            plaintext_idx=[0, 0, 0],
            key=key,
            score=0.0,
            meta={"work": {"evals": 4}, "telemetry": {"kaeding": {}}},
        )

    monkeypatch.setattr(phase2_mod, "run", _fake_run)

    empty_metrics = {
        "slip_count": 0,
        "slip_accept_count": 0,
        "slip_accept_rate": float("nan"),
        "accept_rate": float("nan"),
        "phase_attempts_total": 0,
        "phase_improves_total": 0,
        "phase_best_delta_max": float("nan"),
    }
    key_anchor = [0] * 30
    key_phasea_1 = ([1] * 29) + [0]
    key_phasea_2 = ([2] * 29) + [0]
    key_topk_1 = ([3] * 29) + [0]
    key_topk_2 = ([4] * 29) + [0]
    phasea_rows = [
        dict(
            start_hash="sa",
            end_hash="anchor",
            end_key=list(key_anchor),
            end_plaintext=[0, 1, 2, 0],
            start_score_pct=0.10,
            end_score_pct=0.95,
            end_match=0.10,
            best_delta_pct=0.85,
            end_score_raw=0.11,
            restart_idx=0,
            metrics=dict(empty_metrics),
        ),
        dict(
            start_hash="sb",
            end_hash="phasea1",
            end_key=list(key_phasea_1),
            end_plaintext=[0, 1, 2, 0],
            start_score_pct=0.10,
            end_score_pct=0.90,
            end_match=0.10,
            best_delta_pct=0.80,
            end_score_raw=0.10,
            restart_idx=1,
            metrics=dict(empty_metrics),
        ),
        dict(
            start_hash="sc",
            end_hash="phasea2",
            end_key=list(key_phasea_2),
            end_plaintext=[0, 1, 2, 0],
            start_score_pct=0.10,
            end_score_pct=0.89,
            end_match=0.10,
            best_delta_pct=0.79,
            end_score_raw=0.09,
            restart_idx=2,
            metrics=dict(empty_metrics),
        ),
    ]
    injected_topk = [
        dict(
            rank=1,
            key_idx=list(key_topk_1),
            plaintext_idx=[0, 1, 2, 0],
            end_hash="topk1",
            source="phaseB_topk",
        ),
        dict(
            rank=2,
            key_idx=list(key_topk_2),
            plaintext_idx=[0, 1, 2, 0],
            end_hash="topk2",
            source="phaseB_topk",
        ),
    ]

    def _append_phaseb_topk(**kwargs) -> None:
        payload = kwargs["payload"]
        for row in injected_topk:
            payload.append(dict(row))

    common_kwargs = dict(
        tier_name="fixture_fixture_001_p3_c1_l3",
        tier_period=3,
        tier_columns=1,
        text_id=0,
        key_seed=411,
        key_len=30,
        ct_idx=np.asarray([0, 0, 0], dtype=np.uint8),
        pt_idx=np.asarray([0, 0, 0], dtype=np.uint8),
        order="col_then_sub",
        alphabet_size=10,
        direction=no_wli_runner.Direction.LTR,
        solve_match_threshold=0.9,
        oracle_assist_selection_effective=False,
        stage3_phaseA_experiment="a_baseline",
        stage3_phaseB_experiment="c_min_late",
        stage3_phaseB_char_pct_min_dynamic=0.4,
        stage3_phaseB_char_pct_min_source="test",
        phaseA_rows=phasea_rows,
        stage_rows=[],
        scorer_stage3_search_runtime=_ConstantScorer(),
        scorer_basin_judge_runtime=_ConstantScorer(),
        scorer_word_ngram_report_runtime=None,
        scorer_full_runtime=_ConstantScorer(),
        scorer_stage3_phaseB={},
        solver_stage3_cfg={"steps": 4, "restarts": 1, "col_batch": 4, "inner_batch": 8},
        stage3_phaseB_cfg={"steps": 4, "inner_batch": 8, "col_every": 0, "col_batch": 0},
        stage3_phaseB_top_n=32,
        stage3_phaseB_gate_delta=-1.0,
        stage3_phaseB_gate_end_gain=-1.0,
        stage3_scan_phaseA_only=False,
        stage3_span_basin_judge_k_cfg=3,
        stage3_span_basin_judge_require_span_active=False,
        stage3_span_basin_judge_dedupe_by_end_hash=True,
        stage3_span_basin_judge_tie_eps=0.0,
        stage3_span_basin_judge_tie_max_seeds=8,
        stage3_word_ngram_decision_influence=False,
        stage3_phasec_enabled=True,
        stage3_phasec_cfg={"steps": 2, "proposals_per_step": 2, "three_cycle_prob": 0.0},
        stage3_phasec_start_keys=4,
        stage3_phasec_seed_offset=0,
        stage3_phasec_word_ngram_tiebreak=False,
        batch_eval_chunk_size=32,
        require_batch_scoring=True,
        base_seed=2026,
        ev3_base=0,
        stage3_heartbeat_seconds=30.0,
        stage3_heartbeat_min_step=50,
        stage3_heartbeat_min_elapsed_seconds=5.0,
        stage3_hb_state={"last_emit_ts": float("-inf")},
        stage3_topk_payload=[],
        full_cipher=_SliceChangeCipher(
            base_key=list(key_anchor),
            period=3,
            alphabet_size=10,
        ),
        append_stage3_topk_from_phasea_fn=lambda **kwargs: None,
        append_stage3_topk_from_kaeding_fn=_append_phaseb_topk,
        is_better_stage3_candidate_preserving_solve_fn=_is_better,
        match_ratio_fn=_match_ratio,
        extract_kaeding_metrics_fn=lambda _obj: dict(empty_metrics),
        solution_span_counter_summary_fn=lambda _obj: dict(
            total=0.0,
            active=0.0,
            skipped=0.0,
            seconds_total=0.0,
            seconds_active=0.0,
        ),
        scorer_span_counter_summary_fn=lambda _obj: dict(
            total=0.0,
            active=0.0,
            skipped=0.0,
            seconds_total=0.0,
            seconds_active=0.0,
        ),
        span_counter_delta_fn=lambda **kwargs: dict(total=0.0, active=0.0, seconds_total=0.0),
        stage3_progress_logging_fn=lambda **kwargs: {},
        fmt_finite_float_fn=lambda v, digits=3: f"{float(v):.{int(digits)}f}"
        if np.isfinite(v)
        else "nan",
        key_hash_fn=lambda key_vals: f"h-{','.join(str(int(v)) for v in key_vals[:6])}",
    )

    control = phase2_mod.run_stage3_two_phase_followup(
        **common_kwargs,
        stage3_phasec_start_policy="source_order",
        stage3_phaseb_family_preservation_policy="off",
        stage3_phaseb_family_view_id="prefix_hamming_le_24",
        stage3_phaseb_family_reserved_slots=0,
    )
    candidate = phase2_mod.run_stage3_two_phase_followup(
        **common_kwargs,
        stage3_phasec_start_policy="phaseb_topk_anchor_swap_v1",
        stage3_phaseb_family_preservation_policy="off",
        stage3_phaseb_family_view_id="prefix_hamming_le_24",
        stage3_phaseb_family_reserved_slots=0,
    )

    assert str(control["phaseC_start_policy"]) == "source_order"
    assert str(candidate["phaseC_start_policy"]) == "phaseb_topk_anchor_swap_v1"
    control_summaries = [dict(row) for row in control["phaseC_start_summaries"]]
    candidate_summaries = [dict(row) for row in candidate["phaseC_start_summaries"]]
    assert [str(row["candidate_hash"]) for row in control_summaries] == [
        "h-0,0,0,0,0,0",
        "topk1",
        "topk2",
        "phasea1",
    ]
    assert [str(row["candidate_hash"]) for row in candidate_summaries] == [
        "topk1",
        "h-0,0,0,0,0,0",
        "topk2",
        "phasea1",
    ]
    assert [str(row["selection_bucket"]) for row in candidate_summaries] == [
        "phaseb_topk_anchor",
        "anchor_demoted",
        "legacy_fill",
        "legacy_fill",
    ]
    assert [int(row["selected_by_phaseb_topk_anchor_policy"]) for row in candidate_summaries] == [
        1,
        0,
        0,
        0,
    ]
    text = capsys.readouterr().out
    assert "start_policy=phaseb_topk_anchor_swap_v1" in text


def test_stage3_phaseb_family_preservation_changes_only_downstream_carry_forward(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def _fake_run(**kwargs):
        init_keys = list(kwargs.get("initial_keys", []))
        key = list(map(int, init_keys[0])) if init_keys else ([0] * 30)
        return SimpleNamespace(
            plaintext_idx=[0, 1, 2, 0],
            key=key,
            score=0.0,
            meta={"work": {"evals": 4}, "telemetry": {"kaeding": {}}},
        )

    monkeypatch.setattr(phase2_mod, "run", _fake_run)

    empty_metrics = {
        "slip_count": 0,
        "slip_accept_count": 0,
        "slip_accept_rate": float("nan"),
        "accept_rate": float("nan"),
        "phase_attempts_total": 0,
        "phase_improves_total": 0,
        "phase_best_delta_max": float("nan"),
    }
    key_a0 = [0] * 30
    key_a1 = ([1] + ([0] * 29))
    key_b0 = ([1] * 26) + ([0] * 4)
    phasea_rows = [
        dict(
            start_hash="s1",
            end_hash="e1",
            end_key=list(key_a0),
            end_plaintext=[0, 1, 2, 0],
            start_score_pct=0.10,
            end_score_pct=0.90,
            end_match=0.10,
            best_delta_pct=0.80,
            end_score_raw=0.11,
            restart_idx=0,
            metrics=dict(empty_metrics),
        ),
        dict(
            start_hash="s2",
            end_hash="e2",
            end_key=list(key_a1),
            end_plaintext=[0, 1, 2, 0],
            start_score_pct=0.10,
            end_score_pct=0.89,
            end_match=0.10,
            best_delta_pct=0.79,
            end_score_raw=0.10,
            restart_idx=1,
            metrics=dict(empty_metrics),
        ),
        dict(
            start_hash="s3",
            end_hash="e3",
            end_key=list(key_b0),
            end_plaintext=[0, 1, 2, 0],
            start_score_pct=0.10,
            end_score_pct=0.88,
            end_match=0.10,
            best_delta_pct=0.78,
            end_score_raw=0.09,
            restart_idx=2,
            metrics=dict(empty_metrics),
        ),
    ]

    common_kwargs = dict(
        tier_name="fixture_fixture_001_p9_c3_l1000",
        tier_period=9,
        tier_columns=3,
        text_id=0,
        key_seed=411,
        key_len=30,
        ct_idx=np.asarray([0, 1, 2, 0], dtype=np.uint8),
        pt_idx=np.asarray([0, 1, 2, 0], dtype=np.uint8),
        order="col_then_sub",
        alphabet_size=29,
        direction=no_wli_runner.Direction.LTR,
        solve_match_threshold=0.9,
        oracle_assist_selection_effective=False,
        stage3_phaseA_experiment="a_baseline",
        stage3_phaseB_experiment="c_min_late",
        stage3_phaseB_char_pct_min_dynamic=0.4,
        stage3_phaseB_char_pct_min_source="test",
        phaseA_rows=phasea_rows,
        stage_rows=[],
        scorer_stage3_search_runtime=_ConstantScorer(),
        scorer_basin_judge_runtime=_ConstantScorer(),
        scorer_word_ngram_report_runtime=None,
        scorer_full_runtime=_ConstantScorer(),
        scorer_stage3_phaseB={},
        solver_stage3_cfg={"steps": 4, "restarts": 1, "col_batch": 4, "inner_batch": 8},
        stage3_phaseB_cfg={"steps": 4, "inner_batch": 8, "col_every": 0, "col_batch": 0},
        stage3_phaseB_top_n=2,
        stage3_phaseB_gate_delta=-1.0,
        stage3_phaseB_gate_end_gain=-1.0,
        stage3_scan_phaseA_only=False,
        stage3_span_basin_judge_k_cfg=3,
        stage3_span_basin_judge_require_span_active=False,
        stage3_span_basin_judge_dedupe_by_end_hash=True,
        stage3_span_basin_judge_tie_eps=0.0,
        stage3_span_basin_judge_tie_max_seeds=2,
        stage3_word_ngram_decision_influence=False,
        stage3_phasec_enabled=False,
        stage3_phasec_cfg={"steps": 2, "proposals_per_step": 2, "three_cycle_prob": 0.0},
        stage3_phasec_start_keys=0,
        stage3_phasec_seed_offset=0,
        stage3_phasec_word_ngram_tiebreak=False,
        batch_eval_chunk_size=32,
        require_batch_scoring=True,
        base_seed=2026,
        ev3_base=0,
        stage3_heartbeat_seconds=30.0,
        stage3_heartbeat_min_step=50,
        stage3_heartbeat_min_elapsed_seconds=5.0,
        stage3_hb_state={"last_emit_ts": float("-inf")},
        stage3_topk_payload=[],
        full_cipher=_DummyCipher(),
        append_stage3_topk_from_phasea_fn=lambda **kwargs: None,
        append_stage3_topk_from_kaeding_fn=lambda **kwargs: None,
        is_better_stage3_candidate_preserving_solve_fn=_is_better,
        match_ratio_fn=_match_ratio,
        extract_kaeding_metrics_fn=lambda _obj: dict(
            slip_count=0,
            slip_accept_count=0,
            slip_accept_rate=float("nan"),
            accept_rate=float("nan"),
            phase_attempts_total=0,
            phase_improves_total=0,
            phase_best_delta_max=float("nan"),
        ),
        solution_span_counter_summary_fn=lambda _obj: dict(
            total=0.0,
            active=0.0,
            skipped=0.0,
            seconds_total=0.0,
            seconds_active=0.0,
        ),
        scorer_span_counter_summary_fn=lambda _obj: dict(
            total=0.0,
            active=0.0,
            skipped=0.0,
            seconds_total=0.0,
            seconds_active=0.0,
        ),
        span_counter_delta_fn=lambda **kwargs: dict(total=0.0, active=0.0, seconds_total=0.0),
        stage3_progress_logging_fn=lambda **kwargs: {},
        fmt_finite_float_fn=lambda v, digits=3: f"{float(v):.{int(digits)}f}"
        if np.isfinite(v)
        else "nan",
        key_hash_fn=lambda key_vals: f"h-{','.join(str(int(v)) for v in key_vals[:6])}",
        stage3_phasec_start_policy="source_order",
    )

    control = phase2_mod.run_stage3_two_phase_followup(
        **common_kwargs,
        stage3_phaseb_family_preservation_policy="off",
        stage3_phaseb_family_view_id="prefix_hamming_le_24",
        stage3_phaseb_family_reserved_slots=2,
    )
    candidate = phase2_mod.run_stage3_two_phase_followup(
        **common_kwargs,
        stage3_phaseb_family_preservation_policy="reserve_by_family_v1",
        stage3_phaseb_family_view_id="prefix_hamming_le_24",
        stage3_phaseb_family_reserved_slots=2,
    )

    assert int(control["phaseB_top_n_used"]) == 2
    assert int(candidate["phaseB_top_n_used"]) == 2
    assert int(control["phaseB_selected_unique_end_hash"]) == 2
    assert int(candidate["phaseB_selected_unique_end_hash"]) == 2
    assert int(control["phaseB_family_count_in_top_band"]) == 1
    assert int(candidate["phaseB_family_count_in_top_band"]) == 1
    assert int(control["phaseB_family_preserved_count"]) == 1
    assert int(candidate["phaseB_family_preserved_count"]) == 2
    assert int(control["phaseB_family_reservation_applied"]) == 0
    assert int(candidate["phaseB_family_reservation_applied"]) == 1
    assert [int(row["phaseb_rank"]) for row in control["phaseB_downstream_selected_summaries"]] == [
        1,
        2,
    ]
    assert [int(row["phaseb_rank"]) for row in candidate["phaseB_downstream_selected_summaries"]] == [
        1,
        3,
    ]
    assert int(candidate["phaseB_downstream_selected_count"]) == 2
    assert int(candidate["phaseB_downstream_selected_unique_end_hash"]) == 2
    text = capsys.readouterr().out
    assert "stage3-phaseB-family" in text
    assert "policy=reserve_by_family_v1" in text


def test_stage3_phaseb_top_family_reinforcement_can_reallocate_downstream_budget(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def _fake_run(**kwargs):
        init_keys = list(kwargs.get("initial_keys", []))
        key = list(map(int, init_keys[0])) if init_keys else ([0] * 30)
        return SimpleNamespace(
            plaintext_idx=[0, 1, 2, 0],
            key=key,
            score=0.0,
            meta={"work": {"evals": 4}, "telemetry": {"kaeding": {}}},
        )

    monkeypatch.setattr(phase2_mod, "run", _fake_run)

    empty_metrics = {
        "slip_count": 0,
        "slip_accept_count": 0,
        "slip_accept_rate": float("nan"),
        "accept_rate": float("nan"),
        "phase_attempts_total": 0,
        "phase_improves_total": 0,
        "phase_best_delta_max": float("nan"),
    }
    key_a0 = [0] * 30
    key_a1 = ([1] + ([0] * 29))
    key_b0 = ([1] * 26) + ([0] * 4)
    phasea_rows = [
        dict(
            start_hash="s1",
            end_hash="e1",
            end_key=list(key_a0),
            end_plaintext=[0, 1, 2, 0],
            start_score_pct=0.10,
            end_score_pct=0.90,
            end_match=0.10,
            best_delta_pct=0.80,
            end_score_raw=0.11,
            restart_idx=0,
            metrics=dict(empty_metrics),
        ),
        dict(
            start_hash="s2",
            end_hash="e2",
            end_key=list(key_b0),
            end_plaintext=[0, 1, 2, 0],
            start_score_pct=0.10,
            end_score_pct=0.89,
            end_match=0.10,
            best_delta_pct=0.79,
            end_score_raw=0.10,
            restart_idx=1,
            metrics=dict(empty_metrics),
        ),
        dict(
            start_hash="s3",
            end_hash="e3",
            end_key=list(key_a1),
            end_plaintext=[0, 1, 2, 0],
            start_score_pct=0.10,
            end_score_pct=0.88,
            end_match=0.10,
            best_delta_pct=0.78,
            end_score_raw=0.09,
            restart_idx=2,
            metrics=dict(empty_metrics),
        ),
    ]

    common_kwargs = dict(
        tier_name="fixture_fixture_001_p9_c3_l1000",
        tier_period=9,
        tier_columns=3,
        text_id=0,
        key_seed=411,
        key_len=30,
        ct_idx=np.asarray([0, 1, 2, 0], dtype=np.uint8),
        pt_idx=np.asarray([0, 1, 2, 0], dtype=np.uint8),
        order="col_then_sub",
        alphabet_size=29,
        direction=no_wli_runner.Direction.LTR,
        solve_match_threshold=0.9,
        oracle_assist_selection_effective=False,
        stage3_phaseA_experiment="a_baseline",
        stage3_phaseB_experiment="c_min_late",
        stage3_phaseB_char_pct_min_dynamic=0.4,
        stage3_phaseB_char_pct_min_source="test",
        phaseA_rows=phasea_rows,
        stage_rows=[],
        scorer_stage3_search_runtime=_ConstantScorer(),
        scorer_basin_judge_runtime=_ConstantScorer(),
        scorer_word_ngram_report_runtime=None,
        scorer_full_runtime=_ConstantScorer(),
        scorer_stage3_phaseB={},
        solver_stage3_cfg={"steps": 4, "restarts": 1, "col_batch": 4, "inner_batch": 8},
        stage3_phaseB_cfg={"steps": 4, "inner_batch": 8, "col_every": 0, "col_batch": 0},
        stage3_phaseB_top_n=2,
        stage3_phaseB_gate_delta=-1.0,
        stage3_phaseB_gate_end_gain=-1.0,
        stage3_scan_phaseA_only=False,
        stage3_span_basin_judge_k_cfg=3,
        stage3_span_basin_judge_require_span_active=False,
        stage3_span_basin_judge_dedupe_by_end_hash=True,
        stage3_span_basin_judge_tie_eps=0.0,
        stage3_span_basin_judge_tie_max_seeds=2,
        stage3_word_ngram_decision_influence=False,
        stage3_phasec_enabled=False,
        stage3_phasec_cfg={"steps": 2, "proposals_per_step": 2, "three_cycle_prob": 0.0},
        stage3_phasec_start_keys=0,
        stage3_phasec_seed_offset=0,
        stage3_phasec_word_ngram_tiebreak=False,
        batch_eval_chunk_size=32,
        require_batch_scoring=True,
        base_seed=2026,
        ev3_base=0,
        stage3_heartbeat_seconds=30.0,
        stage3_heartbeat_min_step=50,
        stage3_heartbeat_min_elapsed_seconds=5.0,
        stage3_hb_state={"last_emit_ts": float("-inf")},
        stage3_topk_payload=[],
        full_cipher=_DummyCipher(),
        append_stage3_topk_from_phasea_fn=lambda **kwargs: None,
        append_stage3_topk_from_kaeding_fn=lambda **kwargs: None,
        is_better_stage3_candidate_preserving_solve_fn=_is_better,
        match_ratio_fn=_match_ratio,
        extract_kaeding_metrics_fn=lambda _obj: dict(
            slip_count=0,
            slip_accept_count=0,
            slip_accept_rate=float("nan"),
            accept_rate=float("nan"),
            phase_attempts_total=0,
            phase_improves_total=0,
            phase_best_delta_max=float("nan"),
        ),
        solution_span_counter_summary_fn=lambda _obj: dict(
            total=0.0,
            active=0.0,
            skipped=0.0,
            seconds_total=0.0,
            seconds_active=0.0,
        ),
        scorer_span_counter_summary_fn=lambda _obj: dict(
            total=0.0,
            active=0.0,
            skipped=0.0,
            seconds_total=0.0,
            seconds_active=0.0,
        ),
        span_counter_delta_fn=lambda **kwargs: dict(total=0.0, active=0.0, seconds_total=0.0),
        stage3_progress_logging_fn=lambda **kwargs: {},
        fmt_finite_float_fn=lambda v, digits=3: f"{float(v):.{int(digits)}f}"
        if np.isfinite(v)
        else "nan",
        key_hash_fn=lambda key_vals: f"h-{','.join(str(int(v)) for v in key_vals[:6])}",
        stage3_phasec_start_policy="source_order",
    )

    control = phase2_mod.run_stage3_two_phase_followup(
        **common_kwargs,
        stage3_phaseb_family_preservation_policy="off",
        stage3_phaseb_family_view_id="prefix_hamming_le_24",
        stage3_phaseb_family_reserved_slots=1,
    )
    candidate = phase2_mod.run_stage3_two_phase_followup(
        **common_kwargs,
        stage3_phaseb_family_preservation_policy="reinforce_top_family_v1",
        stage3_phaseb_family_view_id="prefix_hamming_le_24",
        stage3_phaseb_family_reserved_slots=1,
    )

    assert int(control["phaseB_top_n_used"]) == 2
    assert int(candidate["phaseB_top_n_used"]) == 2
    assert int(control["phaseB_selected_unique_end_hash"]) == 2
    assert int(candidate["phaseB_selected_unique_end_hash"]) == 2
    assert int(control["phaseB_family_count_in_top_band"]) == 2
    assert int(candidate["phaseB_family_count_in_top_band"]) == 2
    assert int(control["phaseB_family_preserved_count"]) == 2
    assert int(candidate["phaseB_family_preserved_count"]) == 1
    assert int(control["phaseB_family_reservation_applied"]) == 0
    assert int(candidate["phaseB_family_reservation_applied"]) == 1
    assert [int(row["phaseb_rank"]) for row in control["phaseB_downstream_selected_summaries"]] == [
        1,
        2,
    ]
    assert [int(row["phaseb_rank"]) for row in candidate["phaseB_downstream_selected_summaries"]] == [
        1,
        3,
    ]
    assert [str(row["family_id"]) for row in candidate["phaseB_downstream_selected_summaries"]] == [
        "f0",
        "f0",
    ]
    assert int(candidate["phaseB_downstream_selected_count"]) == 2
    assert int(candidate["phaseB_downstream_selected_unique_end_hash"]) == 2
    text = capsys.readouterr().out
    assert "stage3-phaseB-family" in text
    assert "policy=reinforce_top_family_v1" in text


def test_stage3_phasec_lexical_threshold_can_engage_below_old_default(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def _fake_run(**kwargs):
        init_keys = list(kwargs.get("initial_keys", []))
        key = list(map(int, init_keys[0])) if init_keys else [1, 0, 2, 0, 1, 2, 0]
        pt = [int(key[0]), int(key[1]), int(key[2]), int(key[3])]
        return SimpleNamespace(
            plaintext_idx=pt,
            key=key,
            score=0.0,
            meta={"work": {"evals": 7}, "telemetry": {"kaeding": {}}},
        )

    def _constant_match(_lhs: list[int], _rhs: list[int]) -> float:
        return 0.70

    monkeypatch.setattr(phase2_mod, "run", _fake_run)

    target_pt = np.asarray([1, 0, 2, 0], dtype=np.uint8)
    seed_key = [1, 0, 2, 0, 1, 2, 0]
    lexical_scorer = _LexicalReportScorer()
    phasea_rows = [
        dict(
            start_hash="s0",
            end_hash="e0",
            restart_idx=0,
            start_key=list(seed_key),
            end_key=list(seed_key),
            start_plaintext=target_pt.astype(int).tolist(),
            end_plaintext=target_pt.astype(int).tolist(),
            end_match=0.70,
            end_score_raw=0.0,
            metrics=dict(
                slip_count=0,
                slip_accept_count=0,
                slip_accept_rate=float("nan"),
                accept_rate=float("nan"),
                phase_attempts_total=0,
                phase_improves_total=0,
                phase_best_delta_max=float("nan"),
            ),
        )
    ]

    out = phase2_mod.run_stage3_two_phase_followup(
        tier_name="fixture_fixture_001_p2_c1_l4",
        tier_period=2,
        tier_columns=1,
        text_id=0,
        key_seed=511,
        key_len=7,
        ct_idx=np.asarray([0, 0, 0, 0], dtype=np.uint8),
        pt_idx=target_pt,
        order="col_then_sub",
        alphabet_size=3,
        direction=None,
        solve_match_threshold=0.9,
        oracle_assist_selection_effective=False,
        stage3_phaseA_experiment="a_baseline",
        stage3_phaseB_experiment="c_min_late",
        stage3_phaseB_char_pct_min_dynamic=0.4,
        stage3_phaseB_char_pct_min_source="test",
        phaseA_rows=phasea_rows,
        stage_rows=[],
        scorer_stage3_search_runtime=_ConstantScorer(),
        scorer_basin_judge_runtime=_ConstantScorer(),
        scorer_word_ngram_report_runtime=lexical_scorer,
        scorer_full_runtime=_ConstantScorer(),
        scorer_stage3_phaseB={},
        solver_stage3_cfg={"steps": 8, "restarts": 1, "col_batch": 4, "inner_batch": 8},
        stage3_phaseB_cfg={"steps": 8, "inner_batch": 8, "col_every": 0, "col_batch": 0},
        stage3_phaseB_top_n=1,
        stage3_phaseB_gate_delta=-1.0,
        stage3_phaseB_gate_end_gain=-1.0,
        stage3_scan_phaseA_only=False,
        stage3_span_basin_judge_k_cfg=1,
        stage3_span_basin_judge_require_span_active=False,
        stage3_span_basin_judge_dedupe_by_end_hash=True,
        stage3_span_basin_judge_tie_eps=0.0,
        stage3_span_basin_judge_tie_max_seeds=4,
        stage3_word_ngram_decision_influence=False,
        stage3_phasec_enabled=True,
        stage3_phasec_cfg={
            "steps": 8,
            "proposals_per_step": 4,
            "three_cycle_prob": 0.0,
            "lexical_min_match": 0.65,
            "lexical_match_tie_eps": 0.0,
            "lexical_score_tie_eps": 0.0,
            "lexical_max_calls": 4,
        },
        stage3_phasec_start_keys=1,
        stage3_phasec_seed_offset=0,
        stage3_phasec_word_ngram_tiebreak=True,
        batch_eval_chunk_size=32,
        require_batch_scoring=True,
        base_seed=2026,
        ev3_base=0,
        stage3_heartbeat_seconds=30.0,
        stage3_heartbeat_min_step=50,
        stage3_heartbeat_min_elapsed_seconds=5.0,
        stage3_hb_state={"last_emit_ts": float("-inf")},
        stage3_topk_payload=[],
        full_cipher=_DummyCipher(),
        append_stage3_topk_from_phasea_fn=lambda **kwargs: None,
        append_stage3_topk_from_kaeding_fn=lambda **kwargs: None,
        is_better_stage3_candidate_preserving_solve_fn=_is_better,
        match_ratio_fn=_constant_match,
        extract_kaeding_metrics_fn=lambda _obj: dict(
            slip_count=0,
            slip_accept_count=0,
            slip_accept_rate=float("nan"),
            accept_rate=float("nan"),
            phase_attempts_total=0,
            phase_improves_total=0,
            phase_best_delta_max=float("nan"),
        ),
        solution_span_counter_summary_fn=lambda _obj: dict(
            total=0.0,
            active=0.0,
            skipped=0.0,
            seconds_total=0.0,
            seconds_active=0.0,
        ),
        scorer_span_counter_summary_fn=lambda _obj: dict(
            total=0.0,
            active=0.0,
            skipped=0.0,
            seconds_total=0.0,
            seconds_active=0.0,
        ),
        span_counter_delta_fn=lambda **kwargs: dict(total=0.0, active=0.0, seconds_total=0.0),
        stage3_progress_logging_fn=lambda **kwargs: {},
        fmt_finite_float_fn=lambda v, digits=3: f"{float(v):.{int(digits)}f}"
        if np.isfinite(v)
        else "nan",
    )

    assert int(out["phaseC_ran"]) == 1
    assert int(out["phaseC_lexical_requests"]) > 0
    assert int(out["phaseC_lexical_tiebreak_decisions"]) > 0
    assert int(out["phaseC_lexical_threshold_skips"]) == 0
    assert int(out["phaseC_lexical_cache_misses"]) > 0
    assert int(lexical_scorer.calls) > 0
    text = capsys.readouterr().out
    assert "lexical_min_match=0.650" in text
    assert "lex_threshold_skip=0" in text
