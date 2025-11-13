# `ciphers/autokey_cipher.py`

> Purpose: production Autokey (additive) cipher where the solver searches only over the seed and plaintext drives the rest of the keystream.

## Key Facts
- **Key model:** `KeyOpsFamily.VECTOR`, length `seed_length`. The keystream is `[seed, plaintext_prefix]`.
- **Alphabet:** defaults to 29 (Runeglish); override via `alphabet_size` in the wrapper/config.
- **Config extras:** `seed_length` (required) and `alphabet_size` are stored on the `CipherConfig` so the runtime can derive key hints.
- **Helpers:** `_encrypt_single` and `_decrypt_single` implement the iterative keystream; batch hooks simply loop over rows.

## Usage
```python
from rune_decrypter_prime.api import run, by_name, KeySpec, SolverSpec

seed_len = 3
cipher = by_name.cipher("autokey", seed_len=seed_len)
key = KeySpec.repeat(len=seed_len)

solution = run(
    text="ᛋᚨᛚᛚᛋ…",
    cipher=cipher,
    key=key,
    solver=SolverSpec.ga(pop_size=64, generations=80, seed=1337),
    scorer="rune",
    scorer_params={"objective": "pct.logp.win10", "n_char": 2, "n_wli": 2},
    encoding_dir="rtl",
    telemetry_on=True,
)
print(solution.key)  # recovered seed
```

## Tests
- `tests/ciphers/test_autokey_cipher.py` – round-trip encrypt/decrypt, batch handling, and seed-length validation.
- `tests/tutorials/test_autokey_tutorial.py` – regression for the promoted tutorial (baseline vs crib-assisted solve, both ≥90 % match).

## Related Docs
- `docs/reference/tutorials/v1/Tutorial_Autokey.md` – walkthrough covering both solver modes in the tutorial.
- `docs/reference/api/wrappers/by_name.md` – explains how to request the `autokey` wrapper and configure the seed length.
