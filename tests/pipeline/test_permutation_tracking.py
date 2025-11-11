"""Pipeline telemetry coverage for permutations and interruptors."""
from __future__ import annotations

import numpy as np
import pytest

from rune_decrypter_prime.api import RunAPI, SolverSpec, KeySpec, by_name
from rune_decrypter_prime.core.types import Direction, Device
from rune_decrypter_prime.telemetry.pipeline import make_pipeline_block
from rune_decrypter_prime.utils.runeglish import Runeglish

pytestmark = pytest.mark.tier_a


def test_pipeline_block_tracks_custom_permutation_and_reinsertion():
    """Custom permutations should be reflected 1:1 in the pipeline telemetry block."""
    plaintext = "rune prime telemetry"
    pt_idx, wli, _ = Runeglish.encode_english_to_runes(plaintext, direction="ltr")
    perm = list(reversed(range(len(pt_idx))))

    solver = SolverSpec.beam(beam_width=2, seed=99, progress_pct=1)
    sol = RunAPI.run(
        text=pt_idx,
        cipher=by_name.cipher("vigenere"),
        key=KeySpec.repeat(len=5),
        solver=solver,
        device=Device.CPU,
        encoding_dir=Direction.LTR,
        wli_data=wli,
        telemetry_on=True,
        initial_text_permutation_indices=perm,
    )

    telemetry = sol.meta.get("telemetry", {})
    pipeline = telemetry.get("pipeline")
    assert pipeline, "Pipeline block missing from telemetry"

    expected = make_pipeline_block(
        text_encoding_direction=Direction.LTR,
        ciphertext_len=len(pt_idx),
        text_permutation=perm,
    )
    assert pipeline == expected

    run_pipeline = telemetry.get("run", {}).get("pipeline", {})
    assert run_pipeline.get("input_permutation", {}) == expected["input_permutation"]
