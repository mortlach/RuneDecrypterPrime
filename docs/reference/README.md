# Reference Overview

> Purpose: provide module-by-module summaries that link guides/how-tos to the concrete files in `docs/reference/`.

This section lists modules, enums, and schemas with quick pointers back to the guides/how-to pages.

| Category | Description | Key Files | Related Guides |
| --- | --- | --- | --- |
| API | RunAPI, specs, normalization helpers | `api/run.py`, `api/specs.py`, `api/normalize.py` | `guides/architecture.md`, `howto/deterministic_run.md` |
| Core Problem/Engine | Materialise cipher/scorer/keyops, solver orchestration | `core/problem/*.py`, `core/engine/engine.py` | `guides/architecture.md` |
| Solvers | Beam/GA/SA/Hybrid implementations | `solvers/*.py` | `guides/extending_hands_on_to_experts.md`, `howto/add_solver.md` |
| Scoring | Backends, objectives, adapters, LM assets | `scoring/*.py`, `scoring/language_model/*.py` | `guides/scoring_deep.md` |
| Telemetry & IO | pipeline blocks, events, run/logger tooling | `telemetry/*.py`, `io/run_logger.py`, `io/logging_adapter.py` | `guides/telemetry.md`, `guides/outputs.md` |
| KeyOps | Permutation/vector key operations, registry | `keyops/*.py` | `howto/add_cipher.md`, mono tutorials |
| Ciphers | Production ciphers, registries, KNF helpers | `ciphers/*.py` | `guides/extending_hands_on_to_experts.md`, tutorials |
| Backends | Device/xp selection + cuda utilities | `backends/device.py`, `backends/xp.py` | `docs/tests_docs/tools.md`, scoring guide |
| Tutorials | Reference companions for v1 scripts | `tutorials/v1/*.md` | `docs/tutorials/*`, troubleshooting appendix |
| Utils | Pretty printers, telemetry helpers, seeds | `utils/*.py` | `guides/outputs.md`, `howto/read_telemetry.md` |

---

## Public imports you may rely on (v1)

Stable surface for end-users and tutorials:

- `from rune_decrypter_prime.api import RunAPI, SolverSpec, KeySpec, by_name, define_map, define_cipher, preview`
- `from rune_decrypter_prime.core.types import Direction, Device, SolverName`
- `from rune_decrypter_prime.io.run_logger import get_logger`

Notes:
- Internal solver implementations live under `solvers/`; the public API above is stable.
- Dev folders and experimental modules are not part of the stable surface.

Each subdirectory contains per-module files following the format:
```
# `<module>`
## What it represents
## Key functions/classes
## Related tests
```
When adding new modules, update both this table and the relevant guide/how-to.


