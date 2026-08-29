from rdp import api


def test_repeatability_minimal():
    ct = "ᛗᛁᚩᚾᚪ"
    solver = api.SolverSpec.genetic_algorithm(
        population_size=16, generations=5, seed=123
    )
    r1 = api.run(
        api.RunSpec(
            problem_input=api.RawTextInput(text=ct),
            cipher=api.CipherSpec.vigenere(alphabet_size=29),
            key_space=api.KeySpec.repeating(length=3),
            solver=solver,
            scoring=api.ScoringConfig(),
            telemetry_enabled=True,
        )
    )
    r2 = api.run(
        api.RunSpec(
            problem_input=api.RawTextInput(text=ct),
            cipher=api.CipherSpec.vigenere(alphabet_size=29),
            key_space=api.KeySpec.repeating(length=3),
            solver=solver,
            scoring=api.ScoringConfig(),
            telemetry_enabled=True,
        )
    )
    assert r1.score == r2.score
    assert (r1.plaintext_text or r1.plaintext_text) == (
        r2.plaintext_text or r2.plaintext_text
    )
