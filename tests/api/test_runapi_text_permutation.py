import pytest

from rune_decrypter_prime.api import RunAPI, by_name, KeySpec, SolverSpec, Direction


def test_runapi_rejects_bad_initial_text_permutation_length():
    cipher = by_name.cipher("vigenere", key_len=1)
    key = KeySpec.repeat(len=1)
    solver = SolverSpec.beam(beam_width=1, seed=7, progress_pct=1)

    with pytest.raises(ValueError):
        RunAPI.run(
            text=[0, 1, 2],
            cipher=cipher,
            key=key,
            solver=solver,
            encoding_dir=Direction.LTR,
            telemetry_on=False,
            initial_text_permutation_indices=[0, 1],
        )
