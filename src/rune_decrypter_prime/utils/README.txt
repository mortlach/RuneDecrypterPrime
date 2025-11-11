rune_decrypter_prime/utils
==========================

Shared utilities used across API/core/solvers.

Examples
--------
- `runeglish.py`: bidirectional mapping between rune strings and index arrays,
  plus helpers for word-break inference.
- `rng.py`: deterministic RNG helpers (namespaced seeds, child generators).
- `pretty.py`, `telemetry` helpers, etc.: presentation utilities for tutorials.

Guidelines
----------
- Keep this folder dependency-free so it can be imported anywhere (including
  tutorials and CLI helpers) without pulling in heavy modules.
- Prefer small, focused modules; if something grows into a subsystem it likely
  belongs under a more specific package (keyops, api, io, …).
