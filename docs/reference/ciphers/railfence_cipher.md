# `ciphers/railfence_cipher.py`

> Purpose: production zig-zag (railfence) transposition cipher with scalar key support, wired into the solver pipeline.

## Key Facts
- **Key model:** `KeyOpsFamily.VECTOR`, length 1. The value represents the number of rails in the inclusive range `[min_rails, max_rails]`.
- **Config knobs:** `min_rails`, `max_rails`, and optional `rails_fixed` are populated by the wrapper builder (`api/wrappers/registry.py`). When `rails_fixed` is supplied, the optimiser sees a single-value key space.
- **Helpers:** `_zigzag_order`, `_encrypt_single`, `_decrypt_single` handle the canonical zig-zag mapping. Both `encrypt` and `decrypt` accept scalars or batches.
- **KeyOps hints:** `self.keyops_hints = {"mod": max_rails - min_rails + 1}` so the vector KeyOps obey the allowed range automatically.

## Usage
```python
from rune_decrypter_prime.api import run, by_name, KeySpec, SolverSpec

cipher = by_name.cipher("railfence", min_rails=2, max_rails=6)
key = KeySpec.scalar(max_val=6)
solver = SolverSpec.beam(beam_width=64, seed=4242)

solution = run(
    text="ᚳᛁᛒᛟ…", cipher=cipher, key=key, solver=solver,
    scorer="rune", scorer_params={"use_word_breaks": False, "objective": "pct.logp.win10"},
    force_no_wli=True, encoding_dir="rtl",
)
print(int(solution.key[0]))  # rail count
```

## Tests
- `tests/ciphers/test_railfence_cipher.py` – round-trip encrypt/decrypt, scalar/batch handling, invalid rails guards.
- `tests/tutorials/test_railfence_tutorial.py` – regression harness that executes the promoted tutorial via RunAPI and asserts score/match criteria plus telemetry hygiene.

## Related Docs
- `docs/reference/api/wrappers/by_name.md` – describes the `railfence` wrapper arguments (`rails`, `min_rails`, `max_rails`).
- `docs/reference/tutorials/v1/Tutorial_Railfence.md` – walkthrough of the tutorial built on this cipher.
