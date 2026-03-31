from __future__ import annotations

import pytest

from tools.benchmarks.periodic_sub_trans.no_wli.phasec_diagnostics_contract import (
    require_phasec_diagnostics_contract,
)


pytestmark = pytest.mark.tier_a


def _novel_phasec_payload() -> dict[str, object]:
    return {
        "phaseC_enabled_cfg": 1,
        "phaseC_enabled_effective": 1,
        "phaseC_ran": 1,
        "phaseC_start_keys_used": 6,
        "phaseC_start_policy": "novel_challenger_v1",
        "phaseC_candidate_pool_count": 34,
        "phaseC_candidate_pool_unique_keys": 34,
        "phaseC_candidate_pool_unique_end_hash": 32,
        "phaseC_candidate_pool_source_counts": {
            "stage3_best_phaseB": 1,
            "phaseB_topk": 1,
            "phaseA_selected": 32,
        },
        "phaseC_start_source_counts": {
            "stage3_best_phaseB": 1,
            "phaseA_selected": 3,
            "phaseB_topk": 2,
        },
        "phaseC_start_unique_end_hash": 6,
        "phaseC_checkpoint_jsonl_name": "phasec_start_checkpoints.jsonl",
        "phaseC_checkpoint_rows_written": 6,
        "phaseC_final_winner_lane": "challenger",
        "phaseC_final_winner_source": "phaseB_topk",
        "phaseC_novel_view_id": "prefix_hamming_le_24",
        "phaseC_anchor_candidate_hash": "anchor-hash",
        "phaseC_candidate_pool_eligible_novel_count": 4,
        "phaseC_candidate_pool_eligible_novel_row_count": 7,
        "phaseC_candidate_pool_eligible_novel_source_counts": {
            "phaseB_topk": 2,
            "phaseA_selected": 5,
        },
        "phaseC_start_eligible_novel_count": 2,
        "phaseC_selected_novel_challenger_count": 2,
        "phaseC_eligible_novel_not_selected_count": 2,
        "phaseC_selected_novel_challenger_hashes": ["cand-a", "cand-b"],
        "phaseC_start_summaries": [
            {
                "start_idx": 1,
                "candidate_hash": "anchor-hash",
                "init_key_idx": [1, 2],
                "init_plaintext_idx": [3, 4],
                "final_key_idx": [5, 6],
                "final_plaintext_idx": [7, 8],
                "selection_bucket": "anchor",
                "selected_by_novel_policy": 0,
                "eligible_novel_challenger": 0,
                "novelty_distance_to_anchor": 0,
                "novelty_min_distance_to_selected_challenger": None,
            },
            {
                "start_idx": 2,
                "candidate_hash": "cand-a",
                "init_key_idx": [9, 10],
                "init_plaintext_idx": [11, 12],
                "final_key_idx": [13, 14],
                "final_plaintext_idx": [15, 16],
                "selection_bucket": "novel_reserved",
                "selected_by_novel_policy": 1,
                "eligible_novel_challenger": 1,
                "novelty_distance_to_anchor": 7,
                "novelty_min_distance_to_selected_challenger": None,
            },
        ],
    }


def test_require_phasec_diagnostics_contract_accepts_complete_novel_payload() -> None:
    require_phasec_diagnostics_contract(
        _novel_phasec_payload(),
        context="test_phasec_payload",
    )


def test_require_phasec_diagnostics_contract_rejects_missing_novel_fields() -> None:
    payload = _novel_phasec_payload()
    del payload["phaseC_selected_novel_challenger_hashes"]

    with pytest.raises(KeyError, match="phaseC_selected_novel_challenger_hashes"):
        require_phasec_diagnostics_contract(
            payload,
            context="test_phasec_payload",
        )


def test_require_phasec_diagnostics_contract_rejects_missing_start_summary_fields() -> None:
    payload = _novel_phasec_payload()
    payload["phaseC_start_summaries"] = [
        {
            "start_idx": 1,
            "candidate_hash": "anchor-hash",
            "init_key_idx": [1, 2],
            "init_plaintext_idx": [3, 4],
            "final_key_idx": [5, 6],
            "final_plaintext_idx": [7, 8],
            "selection_bucket": "anchor",
            "selected_by_novel_policy": 0,
            "eligible_novel_challenger": 0,
            "novelty_distance_to_anchor": 0,
        }
    ]

    with pytest.raises(
        KeyError,
        match="novelty_min_distance_to_selected_challenger",
    ):
        require_phasec_diagnostics_contract(
            payload,
            context="test_phasec_payload",
        )
