rune_decrypter_prime/backends
=============================

Central place for runtime backends (NumPy, Torch, CuPy) and low-level helpers.

Highlights
----------
- `xp.py`: unified “array backend” adapter. `select_backend(...)` returns an
  object that mirrors a tiny subset of NumPy so scorers/solvers can stay
  backend-agnostic. Also tracks whether CUDA/Torch is available.
- `xp_fastmath` / future helpers: small accelerators that depend on optional
  native extensions.

Guidelines
----------
- Avoid importing Torch/CuPy elsewhere; always go through `xp.py` so we can
  centralise availability probes and error messages.
- Keep APIs minimal: the backend layer exists purely to provide array creation
  and dtype helpers to scoring/solver code, not as a general math toolbox.

Extending the layer
-------------------
1. **New backend:** implement a class that mirrors the tiny NumPy API used in
   `xp.py` (asarray/arange/zeros/take/mod/to_numpy) and teach
   `select_backend(...)` how to discover it.
2. **Optional accelerators:** keep them behind feature flags or helper modules
   (`xp_fastmath.py`) so the core import path stays lightweight.
3. **Telemetry:** expose a friendly backend name (e.g., `"torch"` vs `"torch-cuda"`)
   so the scoring layer can report it without guessing.
