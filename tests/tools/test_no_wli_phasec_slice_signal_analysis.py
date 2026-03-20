from __future__ import annotations

import numpy as np

from tools.benchmarks.periodic_sub_trans.no_wli import (
    analyze_phasec_slice_signals as analysis_mod,
)


class _MixedSignalScorer:
    def batch_score(self, pts, _wli):
        arr = np.asarray(pts, dtype=np.uint8)
        out = []
        for row in arr:
            row = np.asarray(row, dtype=np.uint8).reshape(-1)
            if int(row.size) == 2:
                out.append(-10.0 if int(row[0]) == 0 else 5.0)
            else:
                out.append(10.0 * float(row[2]) - 2.0 * float(row[0]))
        return np.asarray(out, dtype=np.float64)


class _SliceChangeCipher:
    def __init__(self, *, base_key: list[int], period: int, alphabet_size: int):
        self.base_key = np.asarray(base_key, dtype=np.int16).reshape(-1)
        self.period = int(period)
        self.alphabet_size = int(alphabet_size)

    def decrypt(self, *, ciphertext, key, interrupt_idx=None, interrupt_sym=None):
        _ = interrupt_idx, interrupt_sym
        ct = np.asarray(ciphertext, dtype=np.uint8).reshape(-1)
        key_mat = np.asarray(key, dtype=np.int16)
        if key_mat.ndim == 1:
            key_mat = key_mat[None, :]
        rows = []
        for row in key_mat:
            flags: list[int] = []
            for slice_idx in range(int(self.period)):
                start = int(slice_idx * self.alphabet_size)
                stop = int(start + self.alphabet_size)
                changed = int(
                    not np.array_equal(
                        np.asarray(row[start:stop], dtype=np.int16),
                        self.base_key[start:stop],
                    )
                )
                flags.extend([changed, changed])
            rows.append(np.asarray(flags[: int(ct.size)], dtype=np.uint8))
        return np.asarray(rows, dtype=np.uint8)


def test_phasec_slice_signal_analysis_detects_probe_beating_legacy() -> None:
    seed_key = [0, 1, 2, 0, 1, 2, 0]
    out = analysis_mod.analyze_stage3_topk_candidate_row(
        artifact_relpath="output/tools/benchmarks/periodic_sub_trans/no_wli/example.json",
        run_id="run_example",
        topk_row=dict(
            rank=1,
            source="phaseB_topk",
            end_hash="hash1",
            match_ratio=0.50,
            score_judge=0.0,
            key_idx=list(seed_key),
            plaintext_idx=[0, 1, 0, 1],
        ),
        truth_row=dict(
            key_hamming_total=4,
            key_hamming_substitution=4,
            key_hamming_columns=0,
            worst_substitution_slice=1,
            worst_plaintext_period_residue=0,
        ),
        period=2,
        alphabet_size=3,
        scorer=_MixedSignalScorer(),
        cipher=_SliceChangeCipher(base_key=seed_key, period=2, alphabet_size=3),
        ciphertext_idx=np.asarray([0, 0, 0, 0], dtype=np.uint8),
        phase_seed=2026,
        rescue_slip_swaps=1,
        chunk_size=8,
        require_batch=True,
    )

    assert int(out["legacy_residue_target_slice"]) == 0
    assert int(out["legacy_residue_hit_truth"]) == 0
    assert int(out["oracle_period_residue_hit_truth"]) == 0
    assert int(out["slice_probe_target_slice"]) == 1
    assert int(out["slice_probe_hit_truth"]) == 1
    assert int(out["slice_probe_better_than_legacy"]) == 1
    assert float(out["slice_probe_score_gain"]) > 0.0


def test_phasec_slice_signal_analysis_summarizes_score_match_drift() -> None:
    rows = analysis_mod.build_phasec_start_rows(
        artifact_relpath="output/tools/benchmarks/periodic_sub_trans/no_wli/example.json",
        run_id="run_example",
        best_match_ratio=0.644,
        start_rows=[
            dict(
                start_idx=1,
                source="phaseB_topk",
                source_rank=1,
                init_match=0.40,
                final_match=0.39,
                match_gain=-0.01,
                init_score=0.10,
                final_score=0.20,
                score_gain=0.10,
                lexical_requests_delta=0,
                lexical_budget_skips_delta=1,
                lexical_threshold_skips_delta=1,
                rescue_attempted=1,
                rescue_applied=0,
            ),
            dict(
                start_idx=2,
                source="phaseA_selected",
                source_rank=2,
                init_match=0.40,
                final_match=0.40,
                match_gain=0.0,
                init_score=0.20,
                final_score=0.25,
                score_gain=0.05,
                lexical_requests_delta=1,
                lexical_budget_skips_delta=0,
                lexical_threshold_skips_delta=0,
                rescue_attempted=0,
                rescue_applied=0,
            ),
            dict(
                start_idx=3,
                source="stage3_best_phaseB",
                source_rank=1,
                init_match=0.40,
                final_match=0.42,
                match_gain=0.02,
                init_score=0.30,
                final_score=0.40,
                score_gain=0.10,
                lexical_requests_delta=0,
                lexical_budget_skips_delta=0,
                lexical_threshold_skips_delta=0,
                rescue_attempted=1,
                rescue_applied=1,
            ),
        ],
    )
    summary = analysis_mod.summarize_phasec_start_rows(rows)

    assert int(summary["phasec_start_count"]) == 3
    assert int(summary["score_up_count"]) == 3
    assert int(summary["match_up_count"]) == 1
    assert int(summary["match_down_count"]) == 1
    assert int(summary["score_up_match_not_up_count"]) == 2
    assert int(summary["score_up_match_down_count"]) == 1
    assert int(summary["lexical_requests_positive_count"]) == 1
    assert int(summary["rescue_attempted_count"]) == 2
    assert int(summary["rescue_applied_count"]) == 1
