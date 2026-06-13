# Public v1 Repository Structure (proposed)

```
rune_decrypter_prime/
  api/
    wrappers/            # by_name.py, registry.py
    __init__.py
    run.py               # RunAPI public entry point
    specs.py             # CipherSpec, KeySpec, SolverSpec, ScoringConfig
    normalize.py         # user input -> canonical
    pipeline.py          # direction, permutation helpers
  backends/
    device.py            # Device selection (CPU surface for v1)
    xp.py                # NumPy/Torch adapters
  ciphers/
    substitution_cipher.py
    vigenere_cipher.py
    columnar_transposition_cipher.py
    generic_map_cipher.py
    registry.py
  core/
    types.py
    config/             # run, cipher, solver, scoring, solution
    engine/             # builders, engine
    problem/            # spec, instance, runtime
    telemetry.py
  keyops/
    permutation_ops.py
    vector.py
    registry.py
  solvers/
    solver_base.py
    beam.py
    ga.py
    sa.py
    hybrid.py
    progress/
      logger.py
      mixin.py
  scoring/
    base_scorer.py
    rune_scorer.py
    torch_rune_scorer.py
    scoring_adapter.py
    policy.py
    unified_tables.py
  telemetry/
    events.py
    pipeline.py
    schema.py
  io/
    run_logger.py
    logging_adapter.py
  tutorials/
    v1/
      Tutorial_Vigenere_GeneralMap.py
      Tutorial_ColumnarTransposition.py
      Tutorial_MonoSubstitution_*.py
  tests/                 # tiered; deterministic
  tools/                 # see below
docs/                    # this documentation site
README.md
CONTRIBUTING.md
CODE_OF_CONDUCT.md
LICENSE
```

**Out of scope for v1 public repo:** `dev/`, experimental ciphers, legacy docs.

