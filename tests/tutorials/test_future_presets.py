"""Regression tests for future Stage-2 presets (Hill, Columnar)."""

from __future__ import annotations
from rdp import api
import numpy as np
import pytest
from tests.tutorials._utils import plaintext_match_rate

pytestmark = pytest.mark.tier_a


def _encode_text(text: str, direction: api.TextDirection):
    from rune_decrypter_prime.utils.runeglish import Runeglish

    pt_idx, wli, _ = Runeglish.encode_english_to_runes(text, direction=direction.value)
    return (np.asarray(pt_idx, dtype=np.uint8), wli)


def test_hill_is_not_a_public_v1_preset():
    with pytest.raises(api.advanced.UnknownComponentError, match="unsupported cipher"):
        api.CipherSpec.from_name("hill", parameters={})


def test_columnar_preset_recovers_text_with_custom_map():
    text = "columnar presets need coverage for future docs"
    pt_idx, wli = _encode_text(text, api.TextDirection.LEFT_TO_RIGHT)
    perm = np.array([2, 0, 3, 1], dtype=np.uint8)
    columnar = api.CipherSpec.columnar(columns=len(perm), alphabet_size=29)
    ct_idx = api.encrypt(
        tuple(int(value) for value in pt_idx),
        cipher=columnar,
        key=tuple(int(value) for value in perm),
    )
    solver = api.SolverSpec.beam_search(width=6, seed=707, rounds=0)
    sol = api.run(
        api.RunSpec(
            problem_input=api.RuneIndexInput(indices=ct_idx, word_lengths=wli),
            cipher=api.CipherSpec.columnar(columns=len(perm), alphabet_size=29),
            key_space=api.KeySpec.permutation(length=len(perm)),
            solver=solver,
            scoring=api.ScoringConfig(),
            initial_keys=(tuple(int(value) for value in perm),),
            telemetry_enabled=False,
            text_direction=api.TextDirection.LEFT_TO_RIGHT,
        )
    )
    match = plaintext_match_rate(sol.plaintext, pt_idx)
    assert match >= 0.95
