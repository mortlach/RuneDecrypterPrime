# Tests Overview

| Tier | Purpose | Typical Command |
| --- | --- | --- |
| **Tier A** | < 5 s CPU checks (API determinism, telemetry, pipeline guardrails) | `pytest -m tier_a` |
| **Tutorial regressions** | Ensure Hands-on tutorials hit score thresholds | `pytest tests/tutorials -q` |
| **Full suite** | Solvers, ciphers, telemetry, tooling | `pytest tests -q` |

- All tests write artefacts into `output/tests/<timestamp>__tests__pytest__<git>/...`.
- Telemetry is always on; logs live under `logs/app.jsonl`, traces under `trace/`.
- See `docs/tests_docs/running_in_ide.md` for IDE instructions, `docs/tests_docs/tiering.md` for marker definitions, and `docs/tests_docs/tools.md` for docs lint + symbol tooling.

