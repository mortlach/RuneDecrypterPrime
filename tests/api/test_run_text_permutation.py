from rdp import api
import pytest

def test_runapi_rejects_bad_initial_text_permutation_length():
    cipher = api.CipherSpec.vigenere(alphabet_size=29)
    key = api.KeySpec.repeating(length=1)
    solver = api.SolverSpec.beam_search(width=1, seed=7, rounds=0)
    with pytest.raises(ValueError):
        api.run(api.RunSpec(problem_input=api.RuneIndexInput(indices=[0, 1, 2]), cipher=cipher, key_space=key, solver=solver, scoring=api.ScoringConfig(), telemetry_enabled=False, text_direction=api.TextDirection.LEFT_TO_RIGHT, text_permutation=[0, 1]))
