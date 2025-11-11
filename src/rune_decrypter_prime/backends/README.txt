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
