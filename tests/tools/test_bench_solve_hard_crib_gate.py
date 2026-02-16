from __future__ import annotations

import numpy as np
import pytest

from rune_decrypter_prime.core.types import Direction
from tools.benchmarks.bench_solve_periodic_columnar_kaeding import (
    _build_hard_crib_for_instance,
    _preflight_hard_crib_oracle,
)


def _wli_from_word_lengths(lengths: list[int]) -> list[list[int]]:
    out: list[list[int]] = []
    for L in lengths:
        for pos in range(int(L)):
            out.append([int(pos), int(L)])
    return out


def test_build_hard_crib_fixed_chars_profile_produces_effective_rules():
    pt = (np.arange(40, dtype=np.uint8) % 29).astype(np.uint8)
    wli = _wli_from_word_lengths([1] * int(pt.size))

    payload, meta = _build_hard_crib_for_instance(
        profile="fixed_chars_light",
        direction=Direction.LTR,
        pt_idx=pt,
        wli_list=wli,
    )

    assert payload is not None
    assert bool(payload.get("enabled", False))
    assert len(payload.get("fixed_chars", {})) > 0
    assert int(meta.get("hard_crib_enabled_requested", 0)) == 1
    assert int(meta.get("hard_crib_rule_fixed_chars", 0)) > 0


def test_preflight_hard_crib_oracle_passes_for_matching_fixed_chars():
    pt = (np.arange(30, dtype=np.uint8) % 29).astype(np.uint8)
    wli = _wli_from_word_lengths([1] * int(pt.size))
    payload, _meta = _build_hard_crib_for_instance(
        profile="fixed_chars_light",
        direction=Direction.LTR,
        pt_idx=pt,
        wli_list=wli,
    )

    out = _preflight_hard_crib_oracle(
        hard_crib=payload,
        pt_true=pt,
        wli_list=wli,
        force_no_wli=True,
        tier_name="unit",
        mode="seed_raw",
        text_id=0,
        key_seed=111,
    )
    assert int(out.get("hard_crib_oracle_ok", 0)) == 1


def test_preflight_hard_crib_word_rules_fail_fast_when_force_no_wli():
    pt = (np.arange(30, dtype=np.uint8) % 29).astype(np.uint8)
    wli = _wli_from_word_lengths([3, 3, 3, 3, 3, 3, 3, 3, 3, 3])
    payload, meta = _build_hard_crib_for_instance(
        profile="word_index_light",
        direction=Direction.LTR,
        pt_idx=pt,
        wli_list=wli,
    )
    assert int(meta.get("hard_crib_has_word_rules", 0)) == 1

    with pytest.raises(RuntimeError, match="force_no_wli=True"):
        _preflight_hard_crib_oracle(
            hard_crib=payload,
            pt_true=pt,
            wli_list=wli,
            force_no_wli=True,
            tier_name="unit",
            mode="seed_raw",
            text_id=0,
            key_seed=111,
        )
