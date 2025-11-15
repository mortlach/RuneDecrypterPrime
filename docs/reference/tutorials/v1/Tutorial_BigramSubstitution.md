# `tutorials/v1/Tutorial_BigramSubstitution.py`

> Purpose: promote the bigram substitution cipher into the supported stack with a staged solve – a deterministic fast-path followed by an LM+crib seeded hybrid run.

## Workflow
- Encode ~300 characters of Alice in Wonderland (RTL) via `Runeglish.encode_english_to_runes`.
- Generate a random permutation over the 841 bigram codes and encrypt using the promoted cipher.
- Extract a long crib (`THERE WAS A TABLE SET OUT UNDER A TREE IN …`), convert it to `(cipher_code, plaintext_code)` pairs, and pass it through the wrapper so the cipher/KeyOps know which positions are pinned.
- Build a WLI-LM bigram prior via `build_wli_bigram_prior()` and construct a `BigramSeedGenerator` that respects the crib.
- Produce a deterministic seed pool (`initial_keys`) for the solver and run:
  1. **Known key** – single `initial_key` that equals the ground-truth permutation (sanity/fact-check).
  2. **Hybrid LM seed** – `SolverSpec.hybrid` with the LM-derived seed pool, verifying `Recovered? Yes` and match ratio ≥ 0.9 end-to-end.
- Each stage emits `print_run_report(...)` plus a labelled `Match ratio (...)` line; regression tests assert both stages report success.

## Run Command
```bash
python tutorials/v1/Tutorial_BigramSubstitution.py
```

## Related Docs
- `docs/reference/ciphers/bigram_substitution_cipher.md` – cipher responsibilities, crib-aware KeyOps, and seed helper.
- `rune_decrypter_prime/utils/bigram_seed_generator.py` – LM prior builder + crib-aware permutation seed generator used by the tutorial.
- `tests/tutorials/test_bigram_substitution.py` – regression harness that executes both stages.
