rune_decrypter_prime/utils
==========================

Shared utilities used across API/core/solvers.

Examples
--------
- `rdp/data/runeglish.py`: definition owner for bidirectional rune/index
  mapping and word-break inference helpers.
- `rng.py`: deterministic RNG helpers (namespaced seeds, child generators).
- `pretty.py`, `telemetry` helpers, etc.: presentation utilities for tutorials.

Guidelines
----------
- Keep this folder dependency-free so it can be imported anywhere (including
  tutorials and CLI helpers) without pulling in heavy modules.
- Prefer small, focused modules; if something grows into a subsystem it likely
  belongs under a more specific package (keyops, api, io, …).

Extending utilities
-------------------
1. **New helpers:** make them pure functions or very small classes so they can
   be reused by API/core without creating import cycles.
2. **Documentation:** include a docstring or module-level comment describing
   what the helper does—these utilities are the first stop for new contributors.
3. **Promotion:** if a helper gains config/state, consider moving it to a
   dedicated package (`io`, `telemetry`, `keyops`) so responsibilities stay clear.
