from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from tools.benchmarks.periodic_sub_trans.no_wli import (
    stage3_iteration_flow as flow_mod,
    iteration_outcome as outcome_mod,
    replay_phasec_rescue_sweep as phasec_replay_mod,
    replay_stage35_substitution_solver as stage35_replay_mod,
    stage35_candidate_archive as archive_mod,
    stage35_substitution_solver as solver_mod,
)


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
        same = np.sum(arr[:, : self._target.size] == self._target.reshape(1, -1), axis=1)
        return same.astype(np.float64)


class _SearchSupportScorer:
    def __init__(self, *, target: list[int]) -> None:
        self._target = np.asarray(target, dtype=np.uint8).reshape(-1)

    def batch_score(self, plaintexts, _wli):
        arr = np.asarray(plaintexts, dtype=np.uint8)
        if arr.ndim == 1:
            arr = arr[None, :]
        same = np.sum(arr[:, : self._target.size] == self._target.reshape(1, -1), axis=1)
        penalties = np.sum(arr[:, : self._target.size] != self._target.reshape(1, -1), axis=1)
        return same.astype(np.float64) - (0.1 * penalties.astype(np.float64))


def _mock_artifact() -> dict[str, object]:
    target = [0, 1, 2, 0, 1, 2]
    baseline_key = [0, 1, 2, 1, 0, 2, 0]
    challenger_rank2 = [1, 0, 2, 0, 1, 2, 1]
    challenger_rank3 = [0, 1, 2, 2, 1, 0, 2]
    return {
        "period": 2,
        "columns": 1,
        "alphabet_size": 3,
        "length": 6,
        "ciphertext_idx": [0, 0, 0, 0, 0, 0],
        "target_plaintext_idx": target,
        "final_best_key_idx": baseline_key,
        "best_match_ratio": 4.0 / 6.0,
        "best_score": 4.0,
        "stage3_topk": [
            {
                "rank": 1,
                "source": "phaseB_topk",
                "end_hash": "h1",
                "key_idx": baseline_key,
                "plaintext_idx": [0, 1, 2, 1, 0, 2],
                "score_judge": 4.0,
            },
            {
                "rank": 2,
                "source": "phaseB_topk",
                "end_hash": "h2",
                "key_idx": challenger_rank2,
                "plaintext_idx": [1, 0, 2, 0, 1, 2],
                "score_judge": 4.0,
            },
            {
                "rank": 3,
                "source": "phaseB_topk",
                "end_hash": "h3",
                "key_idx": challenger_rank3,
                "plaintext_idx": [0, 1, 2, 2, 1, 0],
                "score_judge": 4.0,
            },
        ],
        "stage3_diagnostics": {
            "phaseC_final_winner_lane": "anchor",
            "phaseC_final_winner_source": "stage3_best_phaseB",
            "phaseC_start_summaries": [
                {
                    "start_idx": 1,
                    "lane": "anchor",
                    "source": "stage3_best_phaseB",
                    "source_rank": 1,
                    "candidate_hash": "h1",
                    "init_match": 4.0 / 6.0,
                    "final_match": 4.0 / 6.0,
                    "init_score": 4.0,
                    "final_score": 4.0,
                    "rescue_applied": 0,
                },
                {
                    "start_idx": 2,
                    "lane": "challenger",
                    "source": "phaseB_topk",
                    "source_rank": 2,
                    "candidate_hash": "h2",
                    "init_match": 4.0 / 6.0,
                    "final_match": 4.0 / 6.0,
                    "init_score": 4.0,
                    "final_score": 4.2,
                    "rescue_applied": 1,
                },
                {
                    "start_idx": 3,
                    "lane": "challenger",
                    "source": "phaseB_topk",
                    "source_rank": 3,
                    "candidate_hash": "h3",
                    "init_match": 4.0 / 6.0,
                    "final_match": 4.0 / 6.0,
                    "init_score": 4.0,
                    "final_score": 4.1,
                    "rescue_applied": 1,
                },
            ],
        },
    }


def test_build_stage35_seed_archive_prefers_final_best_and_challengers() -> None:
    artifact = _mock_artifact()

    out = archive_mod.build_stage35_seed_archive(artifact)

    seed_rows = list(out["seed_rows"])
    assert int(out["prefix_len"]) == 6
    assert list(out["frozen_tail"]) == [0]
    assert int(out["tail_mismatch_count"]) == 2
    assert str(seed_rows[0]["seed_source"]) == "final_best"
    assert {str(row["seed_source"]) for row in seed_rows} >= {
        "final_best",
        "phasec_phaseb_challenger",
    }
    assert int(len(seed_rows)) == 3
    assert all(list(row["key_idx"])[-1] == 0 for row in seed_rows)


def test_build_stage35_seed_archive_live_safe_order_ignores_final_match() -> None:
    artifact = _mock_artifact()
    summaries = list(artifact["stage3_diagnostics"]["phaseC_start_summaries"])
    summaries[1]["final_match"] = 0.99
    summaries[1]["final_score"] = 4.0
    summaries[2]["final_match"] = 0.10
    summaries[2]["final_score"] = 4.5
    artifact["stage3_diagnostics"]["phaseC_start_summaries"] = summaries

    out = archive_mod.build_stage35_seed_archive(artifact)

    challenger_rows = [
        dict(row)
        for row in list(out["seed_rows"])
        if str(row["seed_source"]) == "phasec_phaseb_challenger"
    ]
    assert [int(row["source_rank"]) for row in challenger_rows] == [3, 2]


def test_stage35_solver_is_deterministic_and_freezes_columns() -> None:
    artifact = _mock_artifact()
    seed_archive = archive_mod.build_stage35_seed_archive(artifact)
    target = list(artifact["target_plaintext_idx"])
    solver_cfg = dict(solver_mod.DEFAULT_STAGE35_SOLVER_CFG)
    solver_cfg.update(
        rounds=3,
        beam_width=4,
        archive_keep=12,
        seed_keep=4,
        mini_search_beam_width=3,
        mini_search_final_keep=2,
    )

    def _run_once():
        return solver_mod.solve_stage35_substitution_only(
            ciphertext_idx=np.asarray(artifact["ciphertext_idx"], dtype=np.uint8),
            seed_rows=list(seed_archive["seed_rows"]),
            period=int(artifact["period"]),
            alphabet_size=int(artifact["alphabet_size"]),
            cipher=_SlicePermutationCipher(period=2, alphabet_size=3),
            scorer_full=_PositionalMatchScorer(target=target),
            scorer_search=_SearchSupportScorer(target=target),
            cfg=solver_cfg,
            chunk_size=64,
            require_batch=True,
            fixed_tail=list(seed_archive["frozen_tail"]),
        )

    out_a = _run_once()
    out_b = _run_once()

    rows_a = list(out_a["archive_rows"])
    rows_b = list(out_b["archive_rows"])
    assert rows_a
    assert [list(row["key_idx"]) for row in rows_a] == [list(row["key_idx"]) for row in rows_b]
    assert [float(row["score"]) for row in rows_a] == [float(row["score"]) for row in rows_b]
    assert all(list(row["key_idx"])[-1] == 0 for row in rows_a)
    assert all("truth_match" not in row for row in rows_a)


def test_stage35_solver_can_improve_archive_above_mock_baseline() -> None:
    artifact = _mock_artifact()
    seed_archive = archive_mod.build_stage35_seed_archive(artifact)
    target = list(artifact["target_plaintext_idx"])
    out = solver_mod.solve_stage35_substitution_only(
        ciphertext_idx=np.asarray(artifact["ciphertext_idx"], dtype=np.uint8),
        seed_rows=list(seed_archive["seed_rows"]),
        period=int(artifact["period"]),
        alphabet_size=int(artifact["alphabet_size"]),
        cipher=_SlicePermutationCipher(period=2, alphabet_size=3),
        scorer_full=_PositionalMatchScorer(target=target),
        scorer_search=_SearchSupportScorer(target=target),
        cfg=dict(
            solver_mod.DEFAULT_STAGE35_SOLVER_CFG,
            rounds=4,
            beam_width=4,
            archive_keep=12,
            seed_keep=4,
            mini_search_beam_width=3,
            mini_search_final_keep=2,
        ),
        chunk_size=64,
        require_batch=True,
        fixed_tail=list(seed_archive["frozen_tail"]),
    )

    top_row = dict(list(out["archive_rows"])[0])
    truth_match = stage35_replay_mod._truth_match_ratio(
        top_row["plaintext_idx"],
        artifact["target_plaintext_idx"],
    )
    assert float(truth_match) > float(artifact["best_match_ratio"])
    assert int(out["rounds_completed"]) >= 1
    assert int(out["evals"]) > 0


def test_stage35_solver_emits_progress_events() -> None:
    artifact = _mock_artifact()
    seed_archive = archive_mod.build_stage35_seed_archive(artifact)
    target = list(artifact["target_plaintext_idx"])
    events: list[dict[str, object]] = []

    out = solver_mod.solve_stage35_substitution_only(
        ciphertext_idx=np.asarray(artifact["ciphertext_idx"], dtype=np.uint8),
        seed_rows=list(seed_archive["seed_rows"]),
        period=int(artifact["period"]),
        alphabet_size=int(artifact["alphabet_size"]),
        cipher=_SlicePermutationCipher(period=2, alphabet_size=3),
        scorer_full=_PositionalMatchScorer(target=target),
        scorer_search=_SearchSupportScorer(target=target),
        cfg=dict(
            solver_mod.DEFAULT_STAGE35_SOLVER_CFG,
            rounds=2,
            beam_width=3,
            archive_keep=8,
            seed_keep=3,
            mini_search_beam_width=2,
            mini_search_final_keep=1,
            mini_search_keep_all_rows=0,
        ),
        chunk_size=64,
        require_batch=True,
        fixed_tail=list(seed_archive["frozen_tail"]),
        progress_callback=lambda payload: events.append(dict(payload)),
    )

    assert int(out["evals"]) > 0
    event_names = [str(event.get("event", "")) for event in events]
    assert "seed_rows_scored" in event_names
    assert "mini_search_start" in event_names
    assert "round_progress" in event_names
    assert "round_archive_snapshot" in event_names
    assert event_names[-1] == "finish"
    archive_snapshot_event = next(
        dict(event)
        for event in events
        if str(event.get("event", "")) == "round_archive_snapshot"
    )
    assert isinstance(list(archive_snapshot_event.get("archive_preview_rows", [])), list)
    finish_event = dict(events[-1])
    assert str(finish_event["outcome_status"]) == "completed"
    assert int(finish_event["completed"]) == 1
    assert int(finish_event["capped"]) == 0
    telemetry_summary = dict(finish_event.get("telemetry_summary", {}) or {})
    assert int(telemetry_summary.get("mini_search_count", 0) or 0) >= 1
    assert float(telemetry_summary.get("row_scoring_seconds", 0.0) or 0.0) >= 0.0


def test_stage35_solver_reports_capped_eval_outcome() -> None:
    artifact = _mock_artifact()
    seed_archive = archive_mod.build_stage35_seed_archive(artifact)
    target = list(artifact["target_plaintext_idx"])
    events: list[dict[str, object]] = []

    out = solver_mod.solve_stage35_substitution_only(
        ciphertext_idx=np.asarray(artifact["ciphertext_idx"], dtype=np.uint8),
        seed_rows=list(seed_archive["seed_rows"]),
        period=int(artifact["period"]),
        alphabet_size=int(artifact["alphabet_size"]),
        cipher=_SlicePermutationCipher(period=2, alphabet_size=3),
        scorer_full=_PositionalMatchScorer(target=target),
        scorer_search=_SearchSupportScorer(target=target),
        cfg=dict(
            solver_mod.DEFAULT_STAGE35_SOLVER_CFG,
            rounds=2,
            beam_width=3,
            archive_keep=8,
            seed_keep=3,
            mini_search_beam_width=2,
            mini_search_final_keep=1,
            mini_search_keep_all_rows=0,
            max_evals=1,
        ),
        chunk_size=64,
        require_batch=True,
        fixed_tail=list(seed_archive["frozen_tail"]),
        progress_callback=lambda payload: events.append(dict(payload)),
    )

    assert str(out["outcome_status"]) == "capped_evals"
    assert str(out["outcome_reason"]) == "max_evals"
    assert int(out["completed"]) == 0
    assert int(out["capped"]) == 1
    assert int(out["evals"]) >= 1
    finish_event = dict(events[-1])
    assert str(finish_event["event"]) == "finish"
    assert str(finish_event["outcome_status"]) == "capped_evals"
    assert int(finish_event["completed"]) == 0
    assert int(finish_event["capped"]) == 1


def test_stage35_solver_reports_internal_telemetry() -> None:
    artifact = _mock_artifact()
    seed_archive = archive_mod.build_stage35_seed_archive(artifact)
    target = list(artifact["target_plaintext_idx"])

    out = solver_mod.solve_stage35_substitution_only(
        ciphertext_idx=np.asarray(artifact["ciphertext_idx"], dtype=np.uint8),
        seed_rows=list(seed_archive["seed_rows"]),
        period=int(artifact["period"]),
        alphabet_size=int(artifact["alphabet_size"]),
        cipher=_SlicePermutationCipher(period=2, alphabet_size=3),
        scorer_full=_PositionalMatchScorer(target=target),
        scorer_search=_SearchSupportScorer(target=target),
        cfg=dict(
            solver_mod.DEFAULT_STAGE35_SOLVER_CFG,
            rounds=2,
            beam_width=3,
            archive_keep=8,
            seed_keep=3,
            mini_search_beam_width=2,
            mini_search_final_keep=1,
            mini_search_keep_all_rows=0,
        ),
        chunk_size=64,
        require_batch=True,
        fixed_tail=list(seed_archive["frozen_tail"]),
    )

    telemetry = dict(out["telemetry"])
    assert int(telemetry["mini_search_count"]) >= 1
    assert float(telemetry["row_scoring_seconds"]) > 0.0
    assert float(telemetry["batch_score_seconds"]) >= 0.0
    assert int(telemetry["row_scoring_keys_total"]) >= int(len(seed_archive["seed_rows"]))
    assert float(telemetry["average_batch_size"]) > 0.0
    assert isinstance(list(telemetry["mini_search_summaries"]), list)
    assert list(telemetry["mini_search_summaries"])
    first_mini = dict(list(telemetry["mini_search_summaries"])[0])
    assert int(first_mini["proposals_generated"]) >= 0
    assert int(first_mini["archive_candidate_pool_size_after_mini"]) >= int(
        first_mini["archive_size_before_round"]
    )
    assert float(first_mini["total_seconds"]) >= 0.0


def test_stage35_scoring_callback_dedupes_normalized_keys_and_preserves_row_order(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    telemetry = solver_mod._empty_solver_telemetry()
    calls: list[list[list[int]]] = []

    def _fake_score_rows_for_keys(**kwargs):
        key_rows = [list(map(int, key_vals)) for key_vals in list(kwargs["keys"])]
        calls.append(list(key_rows))
        return [
            {
                "key": list(key_vals),
                "key_idx": list(key_vals),
                "pt": [int(sum(key_vals))],
                "plaintext_idx": [int(sum(key_vals))],
                "score": float(sum(key_vals)),
                "search_score": float(sum(key_vals)) - 0.5,
                "candidate_hash": f"hash-{sum(key_vals)}",
            }
            for key_vals in key_rows
        ]

    monkeypatch.setattr(solver_mod, "_score_rows_for_keys", _fake_score_rows_for_keys)
    score_key_rows_fn = solver_mod._scoring_callback(
        ciphertext_idx=np.asarray([0, 1], dtype=np.uint8),
        cipher=object(),
        scorer_full=object(),
        scorer_search=object(),
        chunk_size=64,
        require_batch=True,
        fixed_tail=[8, 9],
        prefix_len=3,
        telemetry=telemetry,
    )

    rows = [
        dict(row)
        for row in score_key_rows_fn(
            [
                [1, 2, 3, 4, 5],
                [1, 2, 3, 6, 7],
                [2, 3, 4, 4, 5],
            ]
        )
    ]

    assert calls == [[[1, 2, 3, 8, 9], [2, 3, 4, 8, 9]]]
    assert [list(row["key_idx"]) for row in rows] == [
        [1, 2, 3, 8, 9],
        [1, 2, 3, 8, 9],
        [2, 3, 4, 8, 9],
    ]
    assert [str(row["candidate_hash"]) for row in rows] == [
        "hash-23",
        "hash-23",
        "hash-26",
    ]
    assert int(telemetry["row_scoring_input_keys_total"]) == 3
    assert int(telemetry["row_scoring_normalized_unique_keys_total"]) == 2
    assert int(telemetry["row_scoring_normalized_duplicate_keys_total"]) == 1


def test_stage35_live_followup_selects_better_candidate_without_truth_fields() -> None:
    artifact = _mock_artifact()
    target = list(artifact["target_plaintext_idx"])
    phasec_rows = list(artifact["stage3_diagnostics"]["phaseC_start_summaries"])
    baseline_summary_row = dict(phasec_rows[1])
    phasec_score_winner_summary_row = dict(phasec_rows[0])
    out = solver_mod.run_stage35_live_followup(
        period=int(artifact["period"]),
        columns=int(artifact["columns"]),
        alphabet_size=int(artifact["alphabet_size"]),
        ciphertext_idx=np.asarray(artifact["ciphertext_idx"], dtype=np.uint8),
        baseline_key=list(artifact["stage3_topk"][1]["key_idx"]),
        baseline_plaintext_idx=list(artifact["stage3_topk"][1]["plaintext_idx"]),
        baseline_score=float(artifact["stage3_diagnostics"]["phaseC_start_summaries"][1]["final_score"]),
        baseline_selector="score_plus_novelty",
        baseline_summary_row=baseline_summary_row,
        phasec_score_winner_summary_row=phasec_score_winner_summary_row,
        stage3_topk_rows=list(artifact["stage3_topk"]),
        phasec_start_summaries=list(
            artifact["stage3_diagnostics"]["phaseC_start_summaries"]
        ),
        phasec_final_winner_lane=str(
            artifact["stage3_diagnostics"]["phaseC_final_winner_lane"]
        ),
        phasec_final_winner_source=str(
            artifact["stage3_diagnostics"]["phaseC_final_winner_source"]
        ),
        cipher=_SlicePermutationCipher(period=2, alphabet_size=3),
        scorer_full=_PositionalMatchScorer(target=target),
        scorer_search=_SearchSupportScorer(target=target),
        cfg=dict(
            solver_mod.DEFAULT_STAGE35_SOLVER_CFG,
            rounds=3,
            beam_width=4,
            archive_keep=12,
            seed_keep=4,
            mini_search_beam_width=3,
            mini_search_final_keep=2,
        ),
        chunk_size=64,
        require_batch=True,
        target_plaintext_idx=list(target),
    )

    assert int(out["enabled_cfg"]) == 1
    assert int(out["ran"]) == 1
    assert int(out["selected"]) == 1
    assert int(out["seed_count"]) >= 3
    assert int(out["archive_count"]) >= 1
    assert float(out["best_score"]) > 4.0
    assert str(out["baseline_selector"]) == "score_plus_novelty"
    assert str(out["baseline_candidate_hash"]) == "h2"
    assert str(out["baseline_candidate_source"]) == "phaseB_topk"
    assert str(out["baseline_candidate_lane"]) == "challenger"
    assert int(out["baseline_differs_from_phasec_score_winner"]) == 1
    assert str(out["phasec_score_winner_candidate_hash"]) == "h1"
    assert float(out["best_match"]) > float(out["baseline_candidate_final_match"])
    assert float(out["truth_gain_vs_selected_row"]) > 0.0
    assert float(out["truth_gain_vs_phasec_score_winner"]) > 0.0
    assert list(out["archive_rows"])
    assert all("truth_match" not in row for row in list(out["archive_rows"]))
    assert int(out["archive_rows"][0]["archive_rank"]) == 1
    telemetry = dict(out["telemetry"])
    assert float(telemetry["baseline_search_score_seconds"]) >= 0.0
    assert float(telemetry["accept_check_seconds"]) >= 0.0
    assert int(telemetry["mini_search_count"]) >= 1


def test_stage35_live_followup_persists_partial_state_and_progress_files(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    artifact = _mock_artifact()
    target = list(artifact["target_plaintext_idx"])
    partial_state_path = tmp_path / "stage35_partial_state.json"
    progress_jsonl_path = tmp_path / "stage35_progress.jsonl"
    appended_rows: list[dict[str, object]] = []

    def _append_jsonl_row(path: Path, row: dict[str, object]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(row, sort_keys=True) + "\n")
        appended_rows.append(dict(row))

    def _fake_solve_stage35_substitution_only(**kwargs):
        progress_callback = kwargs["progress_callback"]
        progress_callback(
            dict(
                event="seed_rows_scored",
                seed_rows_scored_count=2,
                elapsed_seconds=0.1,
            )
        )
        progress_callback(
            dict(
                event="round_archive_snapshot",
                round_idx=1,
                rounds_total=1,
                beam_rows_count=1,
                archive_rows_count=1,
                total_evals=7,
                elapsed_seconds=0.2,
                outcome_status="completed",
                outcome_reason="",
                archive_preview_rows=[
                    {
                        "candidate_hash": "candidate-other",
                        "seed_source": "phasec_phaseb_challenger",
                        "stage3_source": "phaseB_topk",
                        "lane": "challenger",
                        "source_rank": 2,
                        "depth": 1,
                        "target_slice": 1,
                        "move_type": "slice_local_mini_search",
                        "score": 5.0,
                        "search_score": 4.0,
                    }
                ],
            )
        )
        progress_callback(
            dict(
                event="finish",
                rounds_completed=1,
                archive_rows_count=1,
                total_evals=7,
                elapsed_seconds=0.3,
                outcome_status="completed",
                outcome_reason="",
                completed=1,
                capped=0,
                telemetry_summary={
                    "mini_search_count": 1,
                    "row_scoring_seconds": 0.02,
                    "archive_update_seconds": 0.0,
                },
            )
        )
        return dict(
            archive_rows=[
                dict(
                    key_idx=[0, 1, 2, 0, 1, 2, 0],
                    plaintext_idx=list(target),
                    score=6.0,
                    search_score=5.0,
                    candidate_hash="candidate-other",
                    seed_source="phasec_phaseb_challenger",
                    stage3_source="phaseB_topk",
                    lane="challenger",
                    source_rank=2,
                    target_slice=1,
                    depth=1,
                    move_type="slice_local_mini_search",
                )
            ],
            seed_rows_scored=[
                dict(
                    key_idx=list(artifact["final_best_key_idx"]),
                    plaintext_idx=[0, 1, 2, 1, 0, 2],
                    score=4.0,
                    search_score=3.0,
                    candidate_hash="h1",
                )
            ],
            evals=7,
            rounds_completed=1,
            runtime_seconds=0.3,
            outcome_status="completed",
            outcome_reason="",
            completed=1,
            capped=0,
            diversity=dict(
                unique_keys=1,
                unique_seed_sources=1,
                unique_target_slices=1,
                mean_substitution_hamming=1.0,
                max_substitution_hamming=1,
            ),
            mini_search_keep_all_rows_cfg=1,
            mini_search_collected_rows=4,
            mini_search_rows_kept=1,
            telemetry=dict(
                solver_mod._empty_solver_telemetry(),
                mini_search_count=1,
            ),
        )

    monkeypatch.setattr(
        solver_mod,
        "solve_stage35_substitution_only",
        _fake_solve_stage35_substitution_only,
    )

    out = solver_mod.run_stage35_live_followup(
        period=int(artifact["period"]),
        columns=int(artifact["columns"]),
        alphabet_size=int(artifact["alphabet_size"]),
        ciphertext_idx=np.asarray(artifact["ciphertext_idx"], dtype=np.uint8),
        baseline_key=list(artifact["final_best_key_idx"]),
        baseline_plaintext_idx=[0, 1, 2, 1, 0, 2],
        baseline_score=4.0,
        stage3_topk_rows=list(artifact["stage3_topk"]),
        phasec_start_summaries=list(
            artifact["stage3_diagnostics"]["phaseC_start_summaries"]
        ),
        phasec_final_winner_lane=str(
            artifact["stage3_diagnostics"]["phaseC_final_winner_lane"]
        ),
        phasec_final_winner_source=str(
            artifact["stage3_diagnostics"]["phaseC_final_winner_source"]
        ),
        cipher=_SlicePermutationCipher(period=2, alphabet_size=3),
        scorer_full=_PositionalMatchScorer(target=target),
        scorer_search=_SearchSupportScorer(target=target),
        cfg=dict(solver_mod.DEFAULT_STAGE35_SOLVER_CFG),
        chunk_size=64,
        require_batch=True,
        target_plaintext_idx=list(target),
        partial_state_path=partial_state_path,
        progress_jsonl_path=progress_jsonl_path,
        append_jsonl_row_fn=_append_jsonl_row,
    )

    assert partial_state_path.is_file()
    assert progress_jsonl_path.is_file()
    assert str(out["partial_state_path_name"]) == "stage35_partial_state.json"
    assert str(out["progress_jsonl_path_name"]) == "stage35_progress.jsonl"
    assert int(out["progress_events_written"]) == 4
    assert int(out["partial_dump_write_count"]) == 4
    partial_state = json.loads(partial_state_path.read_text(encoding="utf-8"))
    assert str(partial_state["event"]) == "followup_finish"
    assert str(partial_state["outcome_status"]) == "completed"
    progress_rows = [
        json.loads(line)
        for line in progress_jsonl_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert [str(row["event"]) for row in progress_rows] == [
        "seed_rows_scored",
        "round_archive_snapshot",
        "finish",
        "followup_finish",
    ]
    assert all(str(row.get("ts", "")) for row in progress_rows)
    assert str(progress_rows[-1]["accept_reason"]) == "accepted"
    assert len(appended_rows) == 4


def test_stage3_iteration_flow_uses_score_plus_novelty_stage35_baseline_selector(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    def _fake_phasea_restarts(**kwargs):
        _ = kwargs
        return {
            "phaseA_rows": [],
            "stage_rows": [],
            "stage3_solve_hits_delta": 0,
            "dt3_delta": 0.0,
            "ev3_delta": 0,
            "span_phaseA_eval_total": 0.0,
            "span_phaseA_eval_active": 0.0,
            "span_phaseA_eval_skipped": 0.0,
            "span_phaseA_seconds_total": 0.0,
            "span_phaseA_seconds_active": 0.0,
        }

    def _fake_two_phase_followup(**kwargs):
        _ = kwargs
        return {
            "stage_rows": [],
            "dt3_delta": 0.01,
            "ev3_delta": 5,
            "stage3_solve_hits_delta": 0,
            "best3_match": 0.039,
            "best3_score": 0.19101667350788198,
            "best3_key": [7, 3, 14, 14, 14, 2, 11],
            "pt3": np.asarray([1, 2, 3, 4], dtype=np.uint8),
                "phaseC_enabled_cfg": 1,
                "phaseC_enabled_effective": 1,
                "phaseC_ran": 1,
                "phaseC_start_keys_used": 2,
                "phaseC_start_policy": "source_order",
                "phaseC_candidate_pool_count": 2,
                "phaseC_candidate_pool_unique_keys": 2,
                "phaseC_candidate_pool_unique_end_hash": 2,
                "phaseC_candidate_pool_source_counts": {
                    "stage3_best_phaseB": 1,
                    "phaseB_topk": 1,
                },
                "phaseC_start_source_counts": {
                    "stage3_best_phaseB": 1,
                    "phaseB_topk": 1,
                },
                "phaseC_start_unique_end_hash": 2,
                "phaseC_checkpoint_jsonl_name": "phasec_start_checkpoints.jsonl",
                "phaseC_checkpoint_rows_written": 2,
                "phaseC_final_winner_lane": "anchor",
                "phaseC_final_winner_source": "stage3_best_phaseB",
                "phaseC_start_summaries": [
                    {
                        "start_idx": 1,
                        "lane": "anchor",
                        "source": "stage3_best_phaseB",
                        "source_rank": 1,
                        "candidate_hash": "73eee2bf84b7c07f",
                        "init_key_idx": [7, 3, 14, 14, 14, 2, 11],
                        "init_plaintext_idx": [1, 2, 3, 4],
                        "final_key_idx": [7, 3, 14, 14, 14, 2, 11],
                        "final_plaintext_idx": [1, 2, 3, 4],
                        "final_score": 0.19101667350788198,
                        "final_match": 0.039,
                        "score_gain": 0.001,
                    "eligible_novel_challenger": 0,
                    "novelty_distance_to_anchor": 0,
                },
                    {
                        "start_idx": 2,
                        "lane": "challenger",
                        "source": "phaseB_topk",
                        "source_rank": 2,
                        "candidate_hash": "9002ee09917e5a0d",
                        "init_key_idx": [9, 1, 12, 4, 5, 6, 11],
                        "init_plaintext_idx": [1, 2, 3, 5],
                        "final_key_idx": [9, 1, 12, 4, 5, 6, 11],
                        "final_plaintext_idx": [1, 2, 3, 5],
                        "final_score": 0.17284542866740327,
                    "final_match": 0.418,
                    "score_gain": 0.02,
                    "eligible_novel_challenger": 1,
                    "novelty_distance_to_anchor": 164,
                },
            ],
        }

    def _fake_stage35_followup(**kwargs):
        captured.update(kwargs)
        return {
            "enabled_cfg": 1,
            "ran": 0,
            "selected": 0,
            "accept_reason": "no_seed_rows",
        }

    monkeypatch.setattr(flow_mod, "run_stage3_phasea_restarts_call", _fake_phasea_restarts)
    monkeypatch.setattr(flow_mod, "run_stage3_two_phase_followup_call", _fake_two_phase_followup)
    monkeypatch.setattr(flow_mod, "run_stage35_live_followup", _fake_stage35_followup)

    flow_mod.run_stage3_iteration_flow(
        state={
            "tier": SimpleNamespace(
                name="fixture_fixture_001_p9_c3_l1000",
                period=2,
                columns=1,
            ),
            "text_id": 0,
            "key_seed": 411,
            "t0_i": 0.0,
            "key_len": 7,
            "best2_match": 0.039,
            "best2_key": [7, 3, 14, 14, 14, 2, 11],
            "stage2_promoted": [],
            "stage2_entry_score": 0.19,
            "stage2_entry_score_judge": 0.19,
            "scorer_stage2": {},
            "scorer_full": {},
            "oracle_s3": 0.0,
            "oracle_decision_paths_enabled": False,
            "ct_idx": np.asarray([0, 0, 0, 0], dtype=np.uint8),
            "pt_idx": np.asarray([1, 2, 3, 4], dtype=np.uint8),
            "wli": [],
            "direction": None,
            "scorer_stage3_phaseA": {},
            "scorer_stage3_phaseB": {},
            "scorer_stage3_phaseA_runtime": object(),
            "scorer_stage3_search_runtime": _SearchSupportScorer(target=[1, 2, 3, 4]),
            "scorer_basin_judge_runtime": _SearchSupportScorer(target=[1, 2, 3, 4]),
            "scorer_full_runtime": _PositionalMatchScorer(target=[1, 2, 3, 4]),
            "full_cipher": _SlicePermutationCipher(period=2, alphabet_size=3),
            "stage2_evals_total": 5,
            "stage2_continue_to_gate": False,
            "stage2_continue_stop_reason": "",
            "stage3_phaseA_experiment": "a_baseline",
            "stage3_phaseB_experiment": "c_min_late",
            "stage3_phaseB_char_pct_min_dynamic": 0.35,
            "stage3_phaseB_char_pct_min_source": "static",
            "oracle_assist_selection_effective": False,
            "stages": [],
            "STAGE3_PHASEC_START_POLICY": "source_order",
            "STAGE35_ENABLED": True,
            "STAGE35_BASELINE_SELECTOR": "score_plus_novelty",
            "STAGE35_CFG": {},
        },
        stage3_runtime_call_ctx=SimpleNamespace(
            alphabet_size=3,
            batch_eval_chunk_size=64,
            require_batch_scoring=True,
        ),
        stage3_two_phase_enabled=True,
        stage3_continue_after_solve=False,
        stage3_phasea_cfg_default={},
        stage3_phaseb_cfg_default={},
        stage3_phaseb_top_n_default=8,
        stage3_phaseb_gate_delta_floor_default=0.01,
        stage3_phaseb_gate_end_gain_floor_default=0.01,
        solver_stage3_default_cfg={},
        stage3_span_basin_judge_k=8,
        tier_heartbeat_seconds=30.0,
        solve_match_threshold=0.95,
        stall_delta=1e-6,
        stall_stage_limit=2,
        evaluate_stage3_entry_policy_fn=lambda **kwargs: {
            "policy_branch": "continue",
            "stage3_band_name": "test",
            "stage3_scan_phaseA_only": False,
        },
        prepare_stage3_refine_inputs_fn=lambda **kwargs: {
            "c1_focus_enabled": False,
            "init3_n": 1,
            "init3": [[7, 3, 14, 14, 14, 2, 11]],
            "promoted_keys": [],
            "stage3_promoted_keys_count": 0,
            "stage3_period_init_mult": 1.0,
            "stage3_period_step_mult": 1.0,
            "stage3_period_restart_bonus": 0,
            "stage2_gap_to_oracle": 0.0,
            "stage2_gate_score": 0.19,
            "stage2_gate_source": "test",
            "promoted_best_match": 0.039,
            "oracle_used_for_stage3_band": False,
            "stage3_band_name": "test",
            "stage3_phaseA_cfg": {},
            "stage3_phaseB_cfg": {},
            "stage3_phaseB_top_n": 8,
            "stage3_phaseB_gate_delta": 0.01,
            "stage3_phaseB_gate_end_gain": 0.01,
            "solver_stage3_cfg": {},
        },
        summarize_stage3_span_fn=lambda **kwargs: {
            "span_eval_total": 0.0,
            "span_eval_active": 0.0,
            "span_eval_skipped": 0.0,
            "span_seconds_total": 0.0,
            "span_seconds_active": 0.0,
            "span_active_rate": 0.0,
            "span_active_rate_source": "test",
        },
        mark_oracle_decision_use_fn=lambda: None,
        print_stage_preview_fn=lambda **kwargs: None,
        fmt_finite_float_fn=lambda v, digits=3: f"{float(v):.{int(digits)}f}"
        if np.isfinite(v)
        else "nan",
    )

    assert str(captured["baseline_selector"]) == "score_plus_novelty"
    assert str(captured["baseline_summary_row"]["candidate_hash"]) == "9002ee09917e5a0d"
    assert str(captured["phasec_score_winner_summary_row"]["candidate_hash"]) == "73eee2bf84b7c07f"
    assert list(captured["baseline_key"]) == [9, 1, 12, 4, 5, 6, 11]


def test_stage35_live_followup_ignores_oracle_match_fields_in_seed_selection() -> None:
    artifact = _mock_artifact()
    target = list(artifact["target_plaintext_idx"])
    phasec_with_match = list(artifact["stage3_diagnostics"]["phaseC_start_summaries"])
    phasec_with_match[1]["final_match"] = 0.99
    phasec_with_match[2]["final_match"] = 0.01
    phasec_without_match = [
        {
            k: v
            for k, v in dict(row).items()
            if str(k) not in {"init_match", "final_match", "match_gain", "rescue_match_gain"}
        }
        for row in phasec_with_match
    ]

    common_kwargs = dict(
        period=int(artifact["period"]),
        columns=int(artifact["columns"]),
        alphabet_size=int(artifact["alphabet_size"]),
        ciphertext_idx=np.asarray(artifact["ciphertext_idx"], dtype=np.uint8),
        baseline_key=list(artifact["final_best_key_idx"]),
        baseline_plaintext_idx=[0, 1, 2, 1, 0, 2],
        baseline_score=4.0,
        stage3_topk_rows=list(artifact["stage3_topk"]),
        phasec_final_winner_lane=str(
            artifact["stage3_diagnostics"]["phaseC_final_winner_lane"]
        ),
        phasec_final_winner_source=str(
            artifact["stage3_diagnostics"]["phaseC_final_winner_source"]
        ),
        cipher=_SlicePermutationCipher(period=2, alphabet_size=3),
        scorer_full=_PositionalMatchScorer(target=target),
        scorer_search=_SearchSupportScorer(target=target),
        cfg=dict(
            solver_mod.DEFAULT_STAGE35_SOLVER_CFG,
            rounds=3,
            beam_width=4,
            archive_keep=12,
            seed_keep=4,
            mini_search_beam_width=3,
            mini_search_final_keep=2,
        ),
        chunk_size=64,
        require_batch=True,
    )
    out_with = solver_mod.run_stage35_live_followup(
        phasec_start_summaries=phasec_with_match,
        **common_kwargs,
    )
    out_without = solver_mod.run_stage35_live_followup(
        phasec_start_summaries=phasec_without_match,
        **common_kwargs,
    )

    assert str(out_with["best_candidate_hash"]) == str(out_without["best_candidate_hash"])
    assert [list(row["key_idx"]) for row in list(out_with["seed_rows_scored"])] == [
        list(row["key_idx"]) for row in list(out_without["seed_rows_scored"])
    ]
    assert all(
        np.isnan(float(row["checkpoint_final_match"]))
        for row in list(out_with["seed_rows_scored"])
    )


def test_stage35_live_followup_requires_acceptance_guard_before_selection(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    artifact = _mock_artifact()
    target = list(artifact["target_plaintext_idx"])

    def _fake_solve_stage35_substitution_only(**kwargs):
        _ = kwargs
        key_idx = [1, 0, 2, 0, 1, 2, 0]
        return dict(
            archive_rows=[
                dict(
                    key_idx=list(key_idx),
                    plaintext_idx=[1, 0, 2, 0, 1, 2],
                    score=4.0,
                    search_score=3.0,
                    candidate_hash="candidate-other",
                    seed_source="phasec_phaseb_challenger",
                    stage3_source="phaseB_topk",
                    lane="challenger",
                    source_rank=2,
                    target_slice=1,
                    depth=1,
                    move_type="slice_local_mini_search",
                )
            ],
            seed_rows_scored=[
                dict(
                    key_idx=list(artifact["final_best_key_idx"]),
                    checkpoint_final_match=float("nan"),
                )
            ],
            evals=1,
            rounds_completed=1,
            runtime_seconds=0.01,
            diversity=dict(
                unique_keys=1,
                unique_seed_sources=1,
                unique_target_slices=1,
                mean_substitution_hamming=1.0,
                max_substitution_hamming=1,
            ),
            mini_search_keep_all_rows_cfg=1,
            mini_search_collected_rows=8,
            mini_search_rows_kept=8,
        )

    monkeypatch.setattr(
        solver_mod,
        "solve_stage35_substitution_only",
        _fake_solve_stage35_substitution_only,
    )

    out = solver_mod.run_stage35_live_followup(
        period=int(artifact["period"]),
        columns=int(artifact["columns"]),
        alphabet_size=int(artifact["alphabet_size"]),
        ciphertext_idx=np.asarray(artifact["ciphertext_idx"], dtype=np.uint8),
        baseline_key=list(artifact["final_best_key_idx"]),
        baseline_plaintext_idx=[0, 1, 2, 1, 0, 2],
        baseline_score=4.0,
        stage3_topk_rows=list(artifact["stage3_topk"]),
        phasec_start_summaries=list(
            artifact["stage3_diagnostics"]["phaseC_start_summaries"]
        ),
        phasec_final_winner_lane=str(
            artifact["stage3_diagnostics"]["phaseC_final_winner_lane"]
        ),
        phasec_final_winner_source=str(
            artifact["stage3_diagnostics"]["phaseC_final_winner_source"]
        ),
        cipher=_SlicePermutationCipher(period=2, alphabet_size=3),
        scorer_full=_PositionalMatchScorer(target=target),
        scorer_search=_SearchSupportScorer(target=target),
        cfg=dict(solver_mod.DEFAULT_STAGE35_SOLVER_CFG),
        chunk_size=64,
        require_batch=True,
    )

    assert int(out["selected"]) == 0
    assert int(out["accept_passed"]) == 0
    assert str(out["accept_reason"]) == "score_gain_guard_failed"


def test_stage3_iteration_flow_marks_requested_stage35_not_run_as_invalid(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _fake_single_phase(**kwargs):
        _ = kwargs
        return {
            "dt3": 0.01,
            "ev3": 5,
            "pt3": np.asarray([0, 1, 2, 0], dtype=np.uint8),
            "best3_key": [0, 1, 2, 0, 1, 2, 0],
            "best3_match": 0.64,
            "best3_score": 4.0,
            "stage3_solve_hit": False,
            "span_total": 0.0,
            "span_active": 0.0,
            "span_skipped": 0.0,
            "span_seconds_total": 0.0,
            "span_seconds_active": 0.0,
            "kaeding3": {},
        }

    def _fake_stage35_followup(**kwargs):
        _ = kwargs
        return {
            "enabled_cfg": 1,
            "ran": 0,
            "selected": 0,
            "seed_count": 0,
            "tail_mismatch_count": 0,
            "seed_source_counts": {},
            "archive_count": 0,
            "rounds_completed": 0,
            "evals": 0,
            "runtime_seconds": 0.0,
            "archive_unique_keys": 0,
            "archive_unique_seed_sources": 0,
            "archive_unique_target_slices": 0,
            "archive_mean_substitution_hamming": 0.0,
            "archive_max_substitution_hamming": 0,
            "baseline_search_score": 1.0,
            "accept_score_min_gain_cfg": 0.0,
            "accept_search_score_max_drop_cfg": 0.0,
            "accept_passed": 0,
            "accept_reason": "no_seed_rows",
            "mini_search_keep_all_rows_cfg": 1,
            "mini_search_collected_rows": 0,
            "mini_search_rows_kept": 0,
            "best_score": 4.0,
            "best_search_score": 1.0,
            "best_seed_source": "",
            "best_stage3_source": "",
            "best_lane": "",
            "best_source_rank": 0,
            "best_target_slice": None,
            "best_depth": 0,
            "best_move_type": "baseline",
            "best_candidate_hash": "baseline",
            "best_key": [0, 1, 2, 0, 1, 2, 0],
            "best_plaintext_idx": [0, 1, 2, 0],
            "archive_rows": [],
            "seed_rows_scored": [],
        }

    monkeypatch.setattr(flow_mod, "run_stage3_single_phase_call", _fake_single_phase)
    monkeypatch.setattr(flow_mod, "run_stage35_live_followup", _fake_stage35_followup)

    out = flow_mod.run_stage3_iteration_flow(
        state={
            "tier": SimpleNamespace(
                name="fixture_fixture_001_p9_c3_l1000",
                period=2,
                columns=1,
            ),
            "text_id": 0,
            "key_seed": 511,
            "t0_i": 0.0,
            "key_len": 7,
            "best2_match": 0.60,
            "best2_key": [0, 1, 2, 0, 1, 2, 0],
            "stage2_promoted": [],
            "stage2_entry_score": 4.0,
            "stage2_entry_score_judge": 4.0,
            "scorer_stage2": {},
            "scorer_full": {},
            "oracle_s3": 0.0,
            "oracle_decision_paths_enabled": False,
            "ct_idx": np.asarray([0, 0, 0, 0], dtype=np.uint8),
            "pt_idx": np.asarray([0, 1, 2, 0], dtype=np.uint8),
            "wli": [],
            "direction": None,
            "scorer_stage3_phaseA": {},
            "scorer_stage3_phaseB": {},
            "scorer_stage3_phaseA_runtime": object(),
            "scorer_stage3_search_runtime": _SearchSupportScorer(target=[0, 1, 2, 0]),
            "scorer_basin_judge_runtime": _SearchSupportScorer(target=[0, 1, 2, 0]),
            "scorer_full_runtime": _PositionalMatchScorer(target=[0, 1, 2, 0]),
            "full_cipher": _SlicePermutationCipher(period=2, alphabet_size=3),
            "stage2_evals_total": 5,
            "stage2_continue_to_gate": False,
            "stage2_continue_stop_reason": "",
            "stage3_phaseA_experiment": "off",
            "stage3_phaseB_experiment": "off",
            "stage3_phaseB_char_pct_min_dynamic": 0.35,
            "stage3_phaseB_char_pct_min_source": "static",
            "oracle_assist_selection_effective": False,
            "stages": [],
            "STAGE3_PHASEC_START_POLICY": "source_order",
            "STAGE35_ENABLED": True,
            "STAGE35_CFG": {},
        },
        stage3_runtime_call_ctx=SimpleNamespace(
            alphabet_size=3,
            batch_eval_chunk_size=64,
            require_batch_scoring=True,
            append_stage3_topk_from_kaeding_fn=lambda **kwargs: None,
        ),
        stage3_two_phase_enabled=False,
        stage3_continue_after_solve=False,
        stage3_phasea_cfg_default={},
        stage3_phaseb_cfg_default={},
        stage3_phaseb_top_n_default=8,
        stage3_phaseb_gate_delta_floor_default=0.01,
        stage3_phaseb_gate_end_gain_floor_default=0.01,
        solver_stage3_default_cfg={},
        stage3_span_basin_judge_k=8,
        tier_heartbeat_seconds=30.0,
        solve_match_threshold=0.95,
        stall_delta=1e-6,
        stall_stage_limit=2,
        evaluate_stage3_entry_policy_fn=lambda **kwargs: {
            "policy_branch": "continue",
            "stage3_band_name": "test",
            "stage3_scan_phaseA_only": False,
        },
        prepare_stage3_refine_inputs_fn=lambda **kwargs: {
            "c1_focus_enabled": False,
            "init3_n": 1,
            "init3": [[0, 1, 2, 0, 1, 2, 0]],
            "promoted_keys": [],
            "stage3_promoted_keys_count": 0,
            "stage3_period_init_mult": 1.0,
            "stage3_period_step_mult": 1.0,
            "stage3_period_restart_bonus": 0,
            "stage2_gap_to_oracle": 0.0,
            "stage2_gate_score": 4.0,
            "stage2_gate_source": "test",
            "promoted_best_match": 0.60,
            "oracle_used_for_stage3_band": False,
            "stage3_band_name": "test",
            "stage3_phaseA_cfg": {},
            "stage3_phaseB_cfg": {},
            "stage3_phaseB_top_n": 8,
            "stage3_phaseB_gate_delta": 0.01,
            "stage3_phaseB_gate_end_gain": 0.01,
            "solver_stage3_cfg": {},
        },
        summarize_stage3_span_fn=lambda **kwargs: {
            "span_eval_total": 0.0,
            "span_eval_active": 0.0,
            "span_eval_skipped": 0.0,
            "span_seconds_total": 0.0,
            "span_seconds_active": 0.0,
            "span_active_rate": 0.0,
            "span_active_rate_source": "solver_run_telemetry_zero_total",
        },
        mark_oracle_decision_use_fn=lambda: None,
        print_stage_preview_fn=lambda **kwargs: None,
        fmt_finite_float_fn=lambda v, digits=3: f"{float(v):.{int(digits)}f}"
        if np.isfinite(v)
        else "nan",
        log_prefix="[test]",
    )

    assert int(out["stage35_requested_cfg"]) == 1
    assert int(out["stage35_enabled_cfg"]) == 1
    assert int(out["stage35_ran"]) == 0
    assert int(out["stage35_proof_valid"]) == 0
    assert str(out["stage35_proof_invalid_reason"]) == "requested_but_not_run:no_seed_rows"


def test_stage3_iteration_flow_propagates_phaseb_family_preservation_fields(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _fake_phasea_restarts(**kwargs):
        _ = kwargs
        return {
            "phaseA_rows": [],
            "stage_rows": [],
            "stage3_solve_hits_delta": 0,
            "dt3_delta": 0.0,
            "ev3_delta": 0,
            "span_phaseA_eval_total": 0.0,
            "span_phaseA_eval_active": 0.0,
            "span_phaseA_eval_skipped": 0.0,
            "span_phaseA_seconds_total": 0.0,
            "span_phaseA_seconds_active": 0.0,
        }

    def _fake_two_phase_followup(**kwargs):
        _ = kwargs
        return {
            "stage_rows": [],
            "dt3_delta": 0.01,
            "ev3_delta": 5,
            "stage3_solve_hits_delta": 0,
            "best3_match": 0.64,
            "best3_score": 4.0,
            "best3_key": [0, 1, 2, 0, 1, 2, 0],
            "pt3": np.asarray([0, 1, 2, 0], dtype=np.uint8),
            "phaseB_ran": 1,
            "phaseB_skipped": 0,
            "phaseB_top_n_used": 8,
            "phaseB_skip_reason": "",
            "phaseB_family_preservation_policy": "reserve_by_family_v1",
            "phaseB_family_view_id": "prefix_hamming_le_24",
            "phaseB_family_reserved_slots": 2,
            "phaseB_family_count_in_top_band": 3,
            "phaseB_family_preserved_count": 2,
            "phaseB_family_reservation_applied": 1,
            "phaseB_selected_unique_end_hash": 8,
            "phaseB_downstream_selected_count": 8,
            "phaseB_downstream_selected_unique_end_hash": 7,
            "phaseB_topk_saved_count": 1,
            "phaseB_topk_saved_unique_end_hash": 1,
            "phaseC_candidate_pool_count": 10,
            "phaseC_candidate_pool_unique_keys": 8,
            "phaseC_candidate_pool_unique_end_hash": 8,
            "phaseC_candidate_pool_source_counts": {
                "stage3_best_phaseB": 1,
                "phaseB_topk": 1,
                "phaseA_selected": 8,
            },
            "phaseC_start_keys_used": 6,
            "phaseC_start_unique_end_hash": 6,
            "phaseC_start_source_counts": {
                "stage3_best_phaseB": 1,
                "phaseA_selected": 5,
            },
            "phaseC_final_winner_source": "stage3_best_phaseB",
        }

    monkeypatch.setattr(
        flow_mod,
        "run_stage3_phasea_restarts_call",
        _fake_phasea_restarts,
    )
    monkeypatch.setattr(
        flow_mod,
        "run_stage3_two_phase_followup_call",
        _fake_two_phase_followup,
    )

    out = flow_mod.run_stage3_iteration_flow(
        state={
            "tier": SimpleNamespace(
                name="fixture_fixture_001_p9_c3_l1000",
                period=2,
                columns=1,
            ),
            "text_id": 0,
            "key_seed": 511,
            "t0_i": 0.0,
            "key_len": 7,
            "best2_match": 0.60,
            "best2_key": [0, 1, 2, 0, 1, 2, 0],
            "stage2_promoted": [],
            "stage2_entry_score": 4.0,
            "stage2_entry_score_judge": 4.0,
            "scorer_stage2": {},
            "scorer_full": {},
            "oracle_s3": 0.0,
            "oracle_decision_paths_enabled": False,
            "ct_idx": np.asarray([0, 0, 0, 0], dtype=np.uint8),
            "pt_idx": np.asarray([0, 1, 2, 0], dtype=np.uint8),
            "wli": [],
            "direction": None,
            "scorer_stage3_phaseA": {},
            "scorer_stage3_phaseB": {},
            "scorer_stage3_phaseA_runtime": object(),
            "scorer_stage3_search_runtime": _SearchSupportScorer(target=[0, 1, 2, 0]),
            "scorer_basin_judge_runtime": _SearchSupportScorer(target=[0, 1, 2, 0]),
            "scorer_full_runtime": _PositionalMatchScorer(target=[0, 1, 2, 0]),
            "full_cipher": _SlicePermutationCipher(period=2, alphabet_size=3),
            "stage2_evals_total": 5,
            "stage2_continue_to_gate": False,
            "stage2_continue_stop_reason": "",
            "stage3_phaseA_experiment": "a_baseline",
            "stage3_phaseB_experiment": "c_min_late",
            "stage3_phaseB_char_pct_min_dynamic": 0.35,
            "stage3_phaseB_char_pct_min_source": "static",
            "oracle_assist_selection_effective": False,
            "stages": [],
            "STAGE3_PHASEC_START_POLICY": "source_order",
            "STAGE35_ENABLED": False,
            "STAGE35_CFG": {},
        },
        stage3_runtime_call_ctx=SimpleNamespace(
            alphabet_size=3,
            batch_eval_chunk_size=64,
            require_batch_scoring=True,
        ),
        stage3_two_phase_enabled=True,
        stage3_continue_after_solve=False,
        stage3_phasea_cfg_default={},
        stage3_phaseb_cfg_default={},
        stage3_phaseb_top_n_default=8,
        stage3_phaseb_gate_delta_floor_default=0.01,
        stage3_phaseb_gate_end_gain_floor_default=0.01,
        solver_stage3_default_cfg={},
        stage3_span_basin_judge_k=8,
        tier_heartbeat_seconds=30.0,
        solve_match_threshold=0.95,
        stall_delta=1e-6,
        stall_stage_limit=2,
        evaluate_stage3_entry_policy_fn=lambda **kwargs: {
            "policy_branch": "continue",
            "stage3_band_name": "test",
            "stage3_scan_phaseA_only": False,
        },
        prepare_stage3_refine_inputs_fn=lambda **kwargs: {
            "c1_focus_enabled": False,
            "init3_n": 1,
            "init3": [[0, 1, 2, 0, 1, 2, 0]],
            "promoted_keys": [],
            "stage3_promoted_keys_count": 0,
            "stage3_period_init_mult": 1.0,
            "stage3_period_step_mult": 1.0,
            "stage3_period_restart_bonus": 0,
            "stage2_gap_to_oracle": 0.0,
            "stage2_gate_score": 4.0,
            "stage2_gate_source": "test",
            "promoted_best_match": 0.60,
            "oracle_used_for_stage3_band": False,
            "stage3_band_name": "test",
            "stage3_phaseA_cfg": {},
            "stage3_phaseB_cfg": {},
            "stage3_phaseB_top_n": 8,
            "stage3_phaseB_gate_delta": 0.01,
            "stage3_phaseB_gate_end_gain": 0.01,
            "solver_stage3_cfg": {},
        },
        summarize_stage3_span_fn=lambda **kwargs: {
            "span_eval_total": 0.0,
            "span_eval_active": 0.0,
            "span_eval_skipped": 0.0,
            "span_seconds_total": 0.0,
            "span_seconds_active": 0.0,
            "span_active_rate": 0.0,
            "span_active_rate_source": "test",
        },
        mark_oracle_decision_use_fn=lambda: None,
        print_stage_preview_fn=lambda **kwargs: None,
        fmt_finite_float_fn=lambda v, digits=3: f"{float(v):.{int(digits)}f}"
        if np.isfinite(v)
        else "nan",
    )

    assert str(out["phaseB_family_preservation_policy"]) == "reserve_by_family_v1"
    assert str(out["phaseB_family_view_id"]) == "prefix_hamming_le_24"
    assert int(out["phaseB_family_reserved_slots"]) == 2
    assert int(out["phaseB_family_count_in_top_band"]) == 3
    assert int(out["phaseB_family_preserved_count"]) == 2
    assert int(out["phaseB_family_reservation_applied"]) == 1
    assert int(out["phaseB_downstream_selected_count"]) == 8
    assert int(out["phaseB_downstream_selected_unique_end_hash"]) == 7


def test_stage35_replay_case_reports_win_against_baseline(monkeypatch) -> None:
    artifact = _mock_artifact()
    case = phasec_replay_mod.ArtifactCase(
        artifact_path=Path("output/mock/final_instances/mock.json"),
        run_dir=Path("output/mock/runid"),
        run_config_path=Path("output/mock/runid/run_config.json"),
        artifact=dict(artifact),
        run_config={},
    )

    monkeypatch.setattr(
        stage35_replay_mod.phasec_replay_mod,
        "_build_cipher",
        lambda _artifact: _SlicePermutationCipher(period=2, alphabet_size=3),
    )
    monkeypatch.setattr(
        stage35_replay_mod.phasec_replay_mod,
        "_build_stage3_scorer_runtime",
        lambda *, artifact, run_config, scorer_key: (
            _PositionalMatchScorer(target=list(artifact["target_plaintext_idx"]))
            if str(scorer_key) == "scorer"
            else _SearchSupportScorer(target=list(artifact["target_plaintext_idx"]))
        ),
    )
    monkeypatch.setattr(
        stage35_replay_mod.phasec_replay_mod,
        "_repo_rel",
        lambda path: str(path),
    )

    out = stage35_replay_mod.evaluate_stage35_case(case, chunk_size=64, require_batch=True)

    summary = dict(out["case_summary"])
    assert str(summary["outcome"]) == "win"
    assert float(summary["top_gain"]) > 0.0
    assert float(summary["best_truth_gain"]) > 0.0
    assert int(summary["seed_count"]) >= 3
    archive_rows = list(out["archive_rows"])
    assert archive_rows
    assert all(int(row["top_rank_live_visible_only"]) == 1 for row in archive_rows)


def test_stage35_replay_discovery_reports_empty_stage3_topk_cases(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case_empty = phasec_replay_mod.ArtifactCase(
        artifact_path=Path("output/mock/final_instances/empty.json"),
        run_dir=Path("output/mock/empty"),
        run_config_path=Path("output/mock/empty/run_config.json"),
        artifact={
            "period": 9,
            "columns": 3,
            "length": 1000,
            "stage3_topk": [],
            "final_best_key_idx": [0] * 30,
        },
        run_config={},
    )
    case_nonempty = phasec_replay_mod.ArtifactCase(
        artifact_path=Path("output/mock/final_instances/nonempty.json"),
        run_dir=Path("output/mock/nonempty"),
        run_config_path=Path("output/mock/nonempty/run_config.json"),
        artifact={
            "period": 9,
            "columns": 3,
            "length": 1000,
            "stage3_topk": [{"rank": 1, "source": "phaseB_topk"}],
            "final_best_key_idx": [0] * 30,
        },
        run_config={},
    )
    monkeypatch.setattr(
        stage35_replay_mod.phasec_replay_mod,
        "discover_artifact_cases",
        lambda: [case_empty, case_nonempty],
    )

    cases, stats = stage35_replay_mod._discover_stage35_cases_with_stats()

    assert int(len(cases)) == 2
    assert int(stats["filtered_case_count"]) == 2
    assert int(stats["empty_stage3_topk_case_count"]) == 1
    assert int(stats["nonempty_stage3_topk_case_count"]) == 1


def test_resolve_iteration_outcome_can_report_stage35_selected_result() -> None:
    out = outcome_mod.resolve_iteration_outcome(
        stop_reason="unsolved",
        solve_match_threshold=0.90,
        dt_i=1.0,
        ev1=1,
        stage2_evals_total=2,
        ev3=3,
        best2_match=0.60,
        best2_score=0.1,
        best2_key=[1, 2, 3],
        best2_pt=[0, 0, 0],
        best2_preview="old",
        best3_match=0.65,
        best3_score=0.2,
        best3_key=[4, 5, 6],
        pt3=np.asarray([0, 1, 0], dtype=np.uint8),
        target_plaintext_idx=[0, 1, 2],
        stage35_selected=True,
        stage35_best_score=0.3,
        stage35_best_key=[7, 8, 9],
        stage35_best_plaintext_idx=[0, 1, 2],
        wli=[],
        stage1_best_score=0.0,
        oracle_s1=0.0,
        oracle_s2=0.0,
        oracle_s3=0.0,
        derive_outcome_code_fn=lambda **_: "ok",
        safe_preview_latin_fn=lambda pt, _wli: "".join(chr(int(x) + 65) for x in pt),
    )

    assert str(out["best_stage"]) == "stage35_substitution_only"
    assert float(out["best_match"]) == pytest.approx(1.0)
    assert list(out["final_best_key_idx"]) == [7, 8, 9]
    assert list(out["final_best_plaintext_idx"]) == [0, 1, 2]


def test_stage35_replay_summary_counts_wins_losses_and_ties() -> None:
    out = stage35_replay_mod.summarize_case_summaries(
        [
            {"outcome": "win", "top_gain": 0.02, "best_truth_gain": 0.03, "runtime_seconds": 1.0},
            {"outcome": "loss", "top_gain": -0.01, "best_truth_gain": 0.00, "runtime_seconds": 3.0},
            {"outcome": "tie", "top_gain": 0.0, "best_truth_gain": 0.01, "runtime_seconds": 2.0},
        ]
    )

    assert int(out["case_count"]) == 3
    assert int(out["wins"]) == 1
    assert int(out["losses"]) == 1
    assert int(out["ties"]) == 1
    assert float(out["best_top_gain"]) == 0.02
    assert float(out["best_truth_gain"]) == 0.03
    assert float(out["average_runtime_seconds"]) == 2.0
