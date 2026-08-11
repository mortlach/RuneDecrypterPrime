"""Regression tests for future Stage-2 presets (Hill, Columnar)."""
from __future__ import annotations

import numpy as np
import pytest

from rune_decrypter_prime.api import RunAPI, SolverSpec, KeySpec, by_name, cipher_instance, Direction
from tests.tutorials._utils import plaintext_match_rate

pytestmark = pytest.mark.tier_a


def _encode_text(text: str, direction: Direction):
    from rune_decrypter_prime.utils.runeglish import Runeglish
    pt_idx, wli, _ = Runeglish.encode_english_to_runes(text, direction=direction.value)
    return np.asarray(pt_idx, dtype=np.uint8), wli


def test_hill_is_not_a_public_v1_preset():
    with pytest.raises(NotImplementedError, match="not a supported RDP V1"):
        by_name.cipher("hill")


def test_columnar_preset_recovers_text_with_custom_map():
    text = "columnar presets need coverage for future docs"
    pt_idx, wli = _encode_text(text, Direction.LTR)
    perm = np.array([2, 0, 3, 1], dtype=np.uint8)
    columnar = cipher_instance(by_name.cipher("columnar", key_len=len(perm)))
    ct_idx = columnar.encrypt(plaintext=pt_idx, key=perm)

    solver = SolverSpec.beam(beam_width=6, seed=707, progress_pct=1)
    sol = RunAPI.run(
        text=ct_idx,
        cipher=by_name.cipher("columnar"),
        key=KeySpec.permutation(len=len(perm)),
        solver=solver,
        encoding_dir=Direction.LTR,
        telemetry_on=False,
        wli_data=wli,
        initial_keys=[perm.tolist()],
    )
    match = plaintext_match_rate(sol.plaintext_idx, pt_idx)
    assert match >= 0.95
