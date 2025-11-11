# Rune Decrypter Prime (v1) - README

**Rune Decrypter Prime (RDP)** is a framework for analysing and breaking symbolic ciphers on a 29-rune alphabet.
It defines stable interfaces for **Cipher**, **KeyOps**, **Optimiser**, **Scorer**, **Pipeline**, **Engine**, **Telemetry**, and **RNG** so new ideas can plug in without touching the rest of the system.

- **Deterministic** - one master seed per run; named child RNG streams per module.
- **Extensible** - add ciphers, key operations, scorers, and optimisers behind stable contracts.
- **Cross-platform** - runs on Python 3.11+ (CPU-first, Torch if present remains on CPU for parity).
- **Traceable** - JSONL telemetry captures what happened, when, and why.

> RDP is a reproducible lab for decryption methods: build, run, compare, and share results with consistent behaviour.

---

## Purpose and scope

RDP standardises decryption experiments:

- **Cipher** - reversible mapping (encrypt/decrypt) over the 29-rune alphabet.
- **KeyOps** - how keys are created, mutated, recombined, and normalised.
- **Optimiser** - how the key space is searched (SA, GA, Beam, Hybrid).
- **Scorer** - how "rune-English-likeness" is measured (WLI pairs).
- **Pipeline** - direction (`ltr`/`rtl`) and whole-text permutations (e.g. `reverse`), applied outside the cipher.
- **Engine** - orchestration (RNG, telemetry, budgets, common semantics).
- **Telemetry** - minimal, consistent schema; true on/off toggle.
- **RNG** - one seeded master per run; named child streams for isolation.

---

## How it works (one run)

```
Ciphertext
  -> Pipeline (direction/permutation)
        -> Cipher + Key
              -> Scorer (WLI pairs)
                    -> Optimiser (search over KeyOps)
                          -> Telemetry + Result (best key/plaintext/score)
```

1. The **Engine** builds the run: seeds RNG, sets pipeline, initialises cipher, keyops, scorer, optimiser.  
2. The **Optimiser** proposes keys via **KeyOps**; for each key: `decrypt -> score`.  
3. The **Scorer** returns **WLI** pairs (first value ranks candidates).  
4. The best solution and events are recorded to **Telemetry** (unless disabled).  
5. The **Pipeline** undoes any pre-transform so the plaintext is in the right order.

---

## Architecture (one screen)

- **Engine** - seeds RNG, wires everything, manages budgets, writes telemetry.  
- **Pipeline** - direction + permutation, cipher-agnostic, always round-trips.  
- **Cipher** - reversible map and key shape (KNF).  
- **KeyOps** - make/mutate/recombine keys, preserving invariants.  
- **Optimiser** - search strategy with shared semantics.  
- **Scorer** - returns WLI pairs; first value ranks candidates.  
- **RNG** - master seed + named child streams.  
- **Telemetry** - minimal schema, true toggle.

---

## Quick start (IDE-friendly)

Open a tutorial under `tutorials/v1/` and run as-is (fixed seeds). Inspect `output/tutorials/.../logs/app.jsonl`.

```python
from rune_decrypter_prime.api import run, KeySpec, SolverSpec, by_name
from rune_decrypter_prime.core.types import Direction

SEED = 1337
cipher = by_name.cipher("vigenere", key_len=6)
key = KeySpec.repeat(len=6)
solver = SolverSpec.ga(pop_size=64, generations=40, seed=SEED, progress_pct=1)

solution = run(
    text="ᚳᛈᚻᛁᛒᚳᚱᛉᛗ…",  # ciphertext runes or indices
    cipher=cipher,
    key=key,
    solver=solver,
    scorer="rune",
    scorer_params=dict(objective="pct.logp.win10", encoding_dir=Direction.LTR),
    telemetry_on=True,
)
print(solution.score, str(solution.plaintext_rune)[:120])
```

---

## Determinism checklist

- Fix `seed`.  
- Keep device on **CPU**.  
- No global RNG; use injected streams only.  
- Do not mix cipher logic with pipeline transforms.  
- Keep telemetry **on** while developing; switch **off** to measure exact speed.

---

## Extending

Additions follow a simple pattern:

- **New Cipher**: implement encrypt/decrypt; declare key KNF; register in the registry.  
- **New KeyOps**: enforce invariants (Permutation or Vector); use injected RNG only.  
- **New Optimiser**: honour shared fields (`evals`, `since_improve`, `eval_budget`, `time_budget_s`, `patience`); log standard telemetry.  
- **New Scorer**: return WLI pairs; keep CPU path the default.

**Next pages:**  
- [Engine & API](architecture/engine_api.md) · [Pipeline](architecture/pipeline.md) ·
  [Ciphers](architecture/ciphers.md) · [KeyOps](architecture/keyops.md) ·
  [Optimisers](architecture/optimisers.md) · [Telemetry](architecture/telemetry.md) ·
  [Data & Scoring](architecture/data.md) · [Tutorials](tutorials/index.md) · [Tests](tests/overview.md)
