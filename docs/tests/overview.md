# Tests Overview

**Purpose**  
Give confidence that contracts hold and full solves remain reproducible.

## Tiers
| Tier | Focus | Examples |
|---|---|---|
| 1 Smoke | Determinism, telemetry toggle | same seed -> same events; off = zero writes |
| 2 Contract | Module invariants | pipeline round-trip; KeyOps invariants; WLI shape |
| 3 Solve | End-to-end runs | cipher x optimiser combos meet thresholds/budgets |
| 4 Ratchet | Regression/perf | telemetry snapshot lock; <= ~15% logging overhead gain |

## Documentation & schema checks
- **Docs lint:** run your docs linter through `tools/ci/validate_outputs.py` so reports stay under `output/`. It should report zero broken links and valid code fences.
- **Telemetry snapshot:** keep a small JSONL sample under `tests/assets/telemetry_snapshot.jsonl` and assert required events/fields remain stable between versions.

**See also**  
[Telemetry](../architecture/telemetry.md) · [Engine & API](../architecture/engine_api.md)

[<- Crib-Drag API](../tutorials/Tutorial_CribDrag_API.md) · [Next -> Home](../README.md)
