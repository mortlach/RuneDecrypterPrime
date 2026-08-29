"""Pipeline telemetry coverage for permutations and interruptors."""
from __future__ import annotations
from rdp import api
import pytest
from rune_decrypter_prime.core.types import Direction
from rune_decrypter_prime.telemetry.pipeline import make_pipeline_block
from rune_decrypter_prime.utils.runeglish import Runeglish
pytestmark = pytest.mark.tier_a

def test_pipeline_block_tracks_custom_permutation_and_reinsertion():
    """Custom permutations should be reflected 1:1 in the pipeline telemetry block."""
    plaintext = 'rune prime telemetry'
    pt_idx, wli, _ = Runeglish.encode_english_to_runes(plaintext, direction='ltr')
    perm = list(reversed(range(len(pt_idx))))
    solver = api.SolverSpec.beam_search(width=2, seed=99, rounds=0)
    sol = api.run(
        api.RunSpec(
            problem_input=api.RuneIndexInput(
                indices=tuple(int(value) for value in pt_idx), word_lengths=wli
            ),
            cipher=api.CipherSpec.vigenere(alphabet_size=29),
            key_space=api.KeySpec.repeating(length=5),
            solver=solver,
            scoring=api.ScoringConfig(),
            telemetry_enabled=True,
            text_direction=api.TextDirection.LEFT_TO_RIGHT,
            text_permutation=tuple(perm),
            compute_device=api.ComputeDevice.CPU,
        )
    )
    telemetry = sol.telemetry
    pipeline = telemetry.get("pipeline")
    assert pipeline, "Pipeline block missing from telemetry"
    expected = make_pipeline_block(
        text_encoding_direction=Direction.LTR,
        ciphertext_len=len(pt_idx),
        text_permutation=perm,
    )
    assert pipeline == expected
    run_pipeline = telemetry.get('run', {}).get('pipeline', {})
    assert run_pipeline.get('input_permutation', {}) == expected['input_permutation']
