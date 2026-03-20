from __future__ import annotations

import json
from pathlib import Path

from tools.benchmarks.periodic_sub_trans.no_wli import (
    profile_word_ngram_tiebreak as profile_mod,
)


def test_build_benchmark_scenarios_uses_expected_sources() -> None:
    payload = {
        "target_plaintext_idx": [1, 2, 3, 4, 5, 6],
        "final_best_plaintext_idx": [6, 5, 4, 3, 2, 1],
        "stage2_topk": [
            {"rank": 1, "plaintext_idx": [9, 8, 7, 6, 5, 4]},
        ],
    }

    scenarios = profile_mod.build_benchmark_scenarios(
        payload,
        prefix_lengths=(3, 6),
    )
    names = [scenario.name for scenario in scenarios]
    assert "target_full_6" in names
    assert "final_best_full_6" in names
    assert "stage2_rank1_full_6" in names
    assert "target_prefix_3" in names
    assert "final_best_prefix_3" in names
    target_prefix = next(s for s in scenarios if s.name == "target_prefix_3")
    assert target_prefix.length == 3
    assert target_prefix.plaintext_idx.tolist() == [1, 2, 3]


def test_estimate_phasec_budget_matches_current_preset_shape() -> None:
    preset = {
        "force_stage3_phasec_start_keys": 12,
        "force_stage3_phaseb_top_n": 8,
        "force_stage3_phasec_cfg": {
            "steps": 192,
            "proposals_per_step": 32,
        },
    }

    out = profile_mod.estimate_phasec_budget(preset=preset, per_call_ms=10.0)
    assert out["configured_lexical_calls"] == 73728
    assert out["realistic_lexical_calls"] == 55296
    assert out["configured_seconds"] == 737.28
    assert out["realistic_seconds"] == 552.96
