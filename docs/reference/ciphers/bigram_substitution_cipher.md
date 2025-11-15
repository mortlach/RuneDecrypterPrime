# `ciphers/bigram_substitution_cipher.py`

> Purpose: production-ready bigram substitution cipher operating on the 29-rune alphabet (841 digraphs) with crib-aware key space.

## Key Facts
- **Encoding:** Each rune pair `(x, y)` maps to code `x*29 + y`. Encryption is a permutation over these 841 codes; decryption applies the inverse permutation.
- **Key model:** `KeyOpsFamily.CRIBBED_PERMUTATION`, length 841. When cribs are supplied, the pinned `(cipher_code → plaintext_code)` entries are enforced by `CribbedPermutationKeyOps`; otherwise the family behaves like the classic permutation KeyOps.
- **Filler:** Optional `pad_value` (default: pass odd trailing symbol through). If provided, encryption pads odd-length plaintext before pairing so the pipeline length invariant is maintained.
- **Crib support:** `CipherConfig.bigram_crib = [(cipher_code, plaintext_code), ...]` pins permutation entries. The cipher stores the arrays and exposes them via `crib_ct_codes` / `crib_pt_codes`; KeyOps and the seed generator consume the same hints.
- **Crib seeding helper:** `BigramSubstitutionCipher.seed_key_from_crib(...)` builds a permutation consistent with aligning a known plaintext snippet (“crib”) at a given offset, filling unused positions randomly. Useful for deterministic fast-path demos.

## Usage
```python
from rune_decrypter_prime.api import run, by_name, KeySpec, SolverSpec
from rune_decrypter_prime.utils.bigram_seed_generator import (
    BigramSeedGenerator,
    build_wli_bigram_prior,
)

crib = [(12, 341), (278, 512)]  # optional crib pairs
cipher = by_name.cipher("bigram_sub", crib=crib)
key = KeySpec.permutation(len=29 * 29)

prior = build_wli_bigram_prior()
seed_gen = BigramSeedGenerator(
    alphabet_size=29,
    plaintext_prior=prior,
    crib_ct_codes=[ct for ct, _ in crib],
    crib_pt_codes=[pt for _, pt in crib],
)
seed_pool = seed_gen.generate_seeds(ciphertext_indices, n_seeds=48, seed=2027)

solver = SolverSpec.hybrid(
    ga=dict(pop_size=64, generations=80),
    sa=dict(sa_iters=300),
    seed=2027,
)

solution = run(
    text="ᚦᛖᛋᛏ…",
    cipher=cipher,
    key=key,
    solver=solver,
    scorer="rune",
    scorer_params={"objective": "pct.logp.win10", "n_char": 2, "n_wli": 2},
    encoding_dir="rtl",
    telemetry_on=True,
    initial_keys=seed_pool,
)
```

## Tests
- `tests/ciphers/test_bigram_substitution_cipher.py` – encrypt/decrypt round-trip, padding behaviour, crib parsing & seed helper.
- `tests/keyops/test_cribbed_permutation.py` – verifies the crib-aware KeyOps implementation.
- `tests/utils/test_bigram_seed_generator.py` – deterministic LM-driven seed generation.
- `tests/tutorials/test_bigram_substitution.py` – exercises the tutorial fast-path (known key) and the LM+crib seeded hybrid solve with `Recovered? Yes`.

## Related Docs
- `docs/reference/tutorials/v1/Tutorial_BigramSubstitution.md` – staged tutorial covering fast-path verification plus LM+crib seeded hybrid solving.
- `rune_decrypter_prime/utils/bigram_seed_generator.py` – LM-derived prior builder + crib-aware permutation seed generator.
