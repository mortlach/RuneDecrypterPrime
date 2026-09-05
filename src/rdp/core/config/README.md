# Runtime configuration

These objects carry validated settings into runtime components. They sit beneath the public request and are useful when following how a setting reaches the engine.

## Where to look

- [cipher.py](cipher.py) — Cipher materialisation and concrete-key validation.
- [solver.py](solver.py) — Runtime solver configuration.
- [scoring.py](scoring.py) — Scoring settings and validation.
- [interruptor.py](interruptor.py) — Exact and searched interruptor configuration.
- [hard_crib.py](hard_crib.py) — Hard constraints on candidate plaintext.
- [logging_config.py](logging_config.py) — Run-output settings and path resolution.
- [run.py](run.py) — Run-level runtime settings.
- [solution.py](solution.py) — Runtime solution representation.

## Choices and extension

For normal use, configure `api.RunSpec` and its typed components. A contributor adding a setting must trace it from validation to actual use and returned configuration; a field accepted but ignored is a defect.

Continue with the [guide](../../../../docs/guides/anatomy_of_a_run.md) or the [package map](../../README.md).
