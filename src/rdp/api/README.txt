rune_decrypter_prime/api
========================

High-level “front door” for the project. Everything that external users touch
flows through this package.

Key pieces
----------
- `run.py` / `RunAPI`: canonical entry point. Normalises ciphertext/WLI, builds
  `CipherConfig`, `ScoringConfig`, `SolverConfig`, seeds RNGs, and delegates to
  `api.pipeline.execute_run`.
- `specs.py`: declarative `CipherSpec`, `KeySpec`, `SolverSpec`. Tutorials and
  wrappers construct these instead of instantiating engines directly.
- `wrappers/`: UX helpers such as `by_name.cipher("vigenere")` that return
  ready-to-use specs or cipher+key pairs.
- `maps_api.py`: utilities for defining custom user maps/lookup tables and
  previewing them.
- `normalize.py` / `api_utils.py`: shared validation and shape helpers so RunAPI
  can accept strings, numpy arrays, or rune text.
- `pipeline.py`: Stage-1 orchestration (fast-paths, cipher config build,
  ProblemInstance materialisation, pipeline metadata/telemetry glue).

Design notes
------------
- Keep this layer dependency-light: it should only talk to configs, specs,
  and other API helpers, never directly to solvers or scorers.
- Every public API must remain deterministic. Seeds flow from `SolverSpec`
  down to the Stage-2 engine.
- All paths must record `LoggingConfig` information so outputs land under
  `output/<kind>/<run_id>/`.

How to extend
-------------
1. **Add a new wrapper:** implement a handler in `wrappers/by_name.py` that
   returns `(CipherSpec, KeySpec)` and register it in `_REG`.
2. **Expose a new option:** update the relevant dataclass in `specs.py`,
   add a normaliser in `normalize.py`, and add coverage in
   `tests/api/test_normalize.py`.
3. **Introduce a fast-path:** gate it inside `api/pipeline.py` so the main
   path stays single and telemetry continues to flow through one place.
