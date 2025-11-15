# `ciphers/playfair_cipher.py`

> Purpose: production Playfair-29 cipher that collapses the 29-rune alphabet to a 5×5 grid (25 symbols) internally, while keeping solver/scorer contracts in 29-space.

## Key Facts
- **Reduction:** configurable `reduction_map` merges low-frequency runes into canonical representatives (default merges J→I, X→S, AE→A, IO→I).
- **Key model:** permutation of 25 indices (`KeyOpsFamily.PERMUTATION`). The permutation defines the row-major ordering of the reduced square.
- **Filler:** `filler_idx29` (default 0) is used when pairs contain duplicates or odd trailing runes.
- **I/O:** Ciphertext and plaintext remain 29-index streams, so scorers and tutorials don’t need to special-case the reduced alphabet.

## Usage
```python
from rune_decrypter_prime.api import run, by_name, KeySpec, SolverSpec

cipher = by_name.cipher("playfair29", filler_idx=0)
key = KeySpec.permutation(len=25)
solver = SolverSpec.hybrid(pop_size=180, generations=120, sa_iters=1800, seed=2025)

solution = run(
    text="ᚦᚺᛖᚱ...",
    cipher=cipher,
    key=key,
    solver=solver,
    scorer="rune",
    scorer_params={"objective": "pct.logp.win10", "use_word_breaks": False},
    force_no_wli=True,
    encoding_dir="rtl",
)
```

## Tests
- `tests/ciphers/test_playfair_cipher.py` – round-trip checks, seed validation, and filler handling.
- `tests/tutorials/test_playfair_tutorial.py` – exercises the promoted tutorial (baseline + crib modes).

## Related Docs
- `docs/reference/tutorials/v1/Tutorial_Playfair29.md` – walkthrough with solver settings and crib hints.
- `docs/howto/cipher_design_guide.md` – guidelines for implementing reduced-alphabet ciphers.
