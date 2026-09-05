# Public API

This is the front door for an RDP experiment. It turns an explicit request into a result while retaining what was requested, how execution stopped and what was found.

## Where to look

- [specs.py](specs.py) — CipherSpec, KeySpec and SolverSpec constructors.
- [run_spec.py](run_spec.py) — Input types and the RunSpec request.
- [known_key.py](known_key.py) — Encrypt and decrypt using an actual key.
- [run.py](run.py) — Execute a search through api.run.
- [run_result.py](run_result.py) — The returned RunResult.
- [solver_report.py](solver_report.py) — Work counters, configuration, oracle and reproducibility records.
- [display.py](display.py) — Human-readable result summaries.
- [liber_primus.py](liber_primus.py) — Named Liber Primus sources and typed source helpers.
- [experimental.py](experimental.py) — User-defined cipher maps and lookup tables.
- [pipeline.py](pipeline.py) — Internal orchestration after public request binding.

## Choices and extension

Use `KeySpec.scalar(...)` for a bounded integer, `repeating(...)` for a fixed sequence or `permutation(...)` for an ordering. The cipher determines which shapes are valid. `SolverSpec.beam_search(...)`, `genetic_algorithm(...)`, `simulated_annealing(...)` and `hybrid(...)` supply different search recipes. `api.display.SummaryOptions.for_debug()` expands the result detail.

Start extensions in the existing cipher-development workspace. A new runtime capability and a new supported public constructor are separate decisions; do not add a second front door.

Continue with the [guide](../../../docs/guides/anatomy_of_a_run.md) or the [package map](../README.md).
