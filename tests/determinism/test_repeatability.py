from rune_decrypter_prime.api import RunAPI, by_name, KeySpec, SolverSpec


def test_repeatability_minimal():
    # Tiny ciphertext snippet (indices or placeholder runes are fine)
    ct = "ᛗᛁᚩᚾᚪ"  # short and deterministic
    solver = SolverSpec.ga(pop_size=16, generations=5, seed=123, progress_pct=100)
    r1 = RunAPI.run(
        text=ct,
        cipher=by_name.cipher("vigenere", key_len=3),
        key=KeySpec.repeat(len=3),
        solver=solver,
        telemetry_on=True,
    )
    r2 = RunAPI.run(
        text=ct,
        cipher=by_name.cipher("vigenere", key_len=3),
        key=KeySpec.repeat(len=3),
        solver=solver,
        telemetry_on=True,
    )

    assert r1.score == r2.score
    assert getattr(r1, "plaintext_rune", r1.plaintext_str) == getattr(r2, "plaintext_rune", r2.plaintext_str)
