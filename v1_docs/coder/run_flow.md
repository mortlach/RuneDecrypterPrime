# Run Flow

Status: staged V1 draft

Owner paths:
- `src/rune_decrypter_prime/api/run.py`
- `src/rune_decrypter_prime/api/run_spec.py`
- `src/rune_decrypter_prime/api/run_spec_routing.py`
- `src/rune_decrypter_prime/api/pipeline.py`
- `src/rune_decrypter_prime/core/engine/engine.py`
- `src/rune_decrypter_prime/core/problem/runtime.py`

Related tests:
- `tests/api/`
- `tests/api_contract/`
- `tests/core/`
- `tests/pipeline/`
- `tests/smoke/`
- `tests/telemetry/`
- `tests/docs/test_v1_coder_docs_contract.py`

Stability:
- Public V1 surface for API inputs and reports
- Semi-stable contributor surface for pipeline extension points
- Internal helper surface for runtime details

## Purpose

This page explains how a normal RDP run moves from user input to solver result,
reports, and artifacts.

Short version:

```text
input
  -> RawTextInput / NormalizedInput / SourceInputRef
  -> RunSpec or direct RunAPI.run arguments
  -> CipherSpec / KeySpec / SolverSpec
  -> normalized ciphertext and WLI
  -> CipherConfig / ScoringConfig / SolverConfig
  -> ProblemSpec / ProblemInstance / DecryptionProblem
  -> solver candidate search
  -> cipher decrypt/evaluate
  -> scorer ranking
  -> Solution
  -> SolverReport / display summary / artifacts when requested
```

The solver searches. The cipher transforms. The scorer ranks. The report
explains.

## Main Objects

| Object | Owner | Job |
| --- | --- | --- |
| `RunAPI` | `src/rune_decrypter_prime/api/run.py` | Public front door for one run. |
| `RunSpec` | `src/rune_decrypter_prime/api/run_spec.py` | Durable description of what should run. |
| `CipherSpec` | `src/rune_decrypter_prime/api/specs.py` | Declarative cipher choice. |
| `KeySpec` | `src/rune_decrypter_prime/api/specs.py` | Declarative key shape or stream plan. |
| `SolverSpec` | `src/rune_decrypter_prime/api/specs.py` | Declarative solver choice, params, and seed. |
| `ProblemSpec` | `src/rune_decrypter_prime/core/problem/spec.py` | Stage-2 materialisation request. |
| `ProblemInstance` | `src/rune_decrypter_prime/core/problem/instance.py` | Materialised cipher/scorer/problem bundle. |
| `DecryptionProblem` | `src/rune_decrypter_prime/core/problem/runtime.py` | Solver-facing binding of cipher, scorer, keyops, ciphertext, WLI, and telemetry. |
| `EngineConfig` | `src/rune_decrypter_prime/core/engine/engine.py` | Solver kind, params, seed, and small engine knobs. |
| `Solution` | `src/rune_decrypter_prime/core/config/solution.py` | Solver result object returned from runtime. |
| `RunResult` | `src/rune_decrypter_prime/api/run_result.py` | Optional public wrapper pairing solution and `SolverReport`. |

## Entry Paths

RDP currently supports two public run-entry styles.

### Direct Arguments

Direct arguments are the friendly path used by tutorials and examples:

```python
from rune_decrypter_prime.api import RunAPI, by_name, KeySpec, SolverSpec

solution = RunAPI.run(
    text="...",
    cipher=by_name.cipher("vigenere", key_len=3),
    key=KeySpec.repeat(len=3),
    solver=SolverSpec.beam(seed=0, beam_width=4),
)
```

In this path, `RunAPI.run` normalises:

- device
- scorer params
- text encoding direction
- ciphertext and optional WLI
- text permutation
- logging input
- solver params

### RunSpec

`RunSpec` is the durable description path:

```python
from rune_decrypter_prime.api import RunAPI

result = RunAPI.run(spec=spec, return_solver_report=True)
```

When `spec=` is supplied, durable inputs must come from the `RunSpec`. The
runtime rejects mixed outside inputs such as a separate `cipher=...` or
`solver=...`. Only runtime logging controls such as progress callbacks may be
supplied outside the spec.

`run_spec_routing.py` materialises the input:

| Input object | Runtime materialisation |
| --- | --- |
| `RawTextInput` | Normalises text into ciphertext indices and WLI. |
| `NormalizedInput` | Converts already-validated indices to a contiguous array. |
| `SourceInputRef` | Resolves a built-in source reference, then converts to indices and WLI. |

## Pipeline Steps

### 1. API Normalisation

Owner:

- `src/rune_decrypter_prime/api/run.py`
- `src/rune_decrypter_prime/api/normalize.py`
- `src/rune_decrypter_prime/api/run_spec_routing.py`

Responsibilities:

- accept friendly user inputs
- reject mixed `RunSpec` and direct durable inputs
- canonicalise device and encoding direction
- normalise ciphertext and WLI
- normalise solver/scorer parameters
- route logging configuration

This layer should not do solver search or scoring.

### 2. API Pipeline

Owner:

- `src/rune_decrypter_prime/api/pipeline.py`

Responsibilities:

- initialise logging when requested
- try explicit known-key fast paths
- build canonical `CipherConfig`
- build `ProblemSpec`
- materialise `ProblemInstance`
- build `EngineConfig`
- call the Stage-2 engine
- finalise the outward-facing `Solution`

This layer bridges public API objects to core runtime objects.

### 3. Problem Materialisation

Owner:

- `src/rune_decrypter_prime/core/problem/`

Responsibilities:

- build the concrete cipher
- build the scorer
- bind ciphertext and WLI
- prepare pipeline metadata
- construct `DecryptionProblem`

`DecryptionProblem` is the object solvers interact with during search. It owns
the single keyops instance and exposes evaluation methods that combine cipher
decrypt plus scorer ranking.

### 4. Engine And Solver

Owner:

- `src/rune_decrypter_prime/core/engine/engine.py`
- `src/rune_decrypter_prime/solvers/`

Responsibilities:

- choose the solver from `SolverName`
- apply conservative early-stop defaults when omitted
- create the deterministic NumPy RNG
- emit run-start and run-end telemetry envelopes
- instantiate and run the selected solver
- clear scorer WLI caches after the run when supported

Solvers should not reach around the problem to call cipher/scorer internals
directly. They evaluate candidate keys through the problem boundary.

### 5. Evaluation

Owner:

- `src/rune_decrypter_prime/core/problem/runtime.py`

Responsibilities:

- resolve keyops family and fixed key length
- normalise/mutate/evaluate candidate keys through keyops
- decrypt candidate batches through the cipher
- score plaintext batches through the scorer
- track telemetry counters and timings
- handle supported degeneracy and hard-crib evaluation paths

The scorer returns ranking values. Report-only diagnostics may be attached to
metadata, but they must not silently change ranking, stopping, tie-breaks, or
candidate selection.

### 6. Result And Reports

Owner:

- `src/rune_decrypter_prime/api/pipeline_helpers.py`
- `src/rune_decrypter_prime/api/run.py`
- `src/rune_decrypter_prime/api/solver_report.py`
- `src/rune_decrypter_prime/api/display.py`
- `src/rune_decrypter_prime/api/run_artifact_manifest.py`

Responsibilities:

- finalise the outward-facing `Solution`
- optionally build `SolverReport`
- optionally return `RunResult`
- optionally write `artifacts/solver_report.json`
- optionally write `artifacts/run_artifacts_manifest.json`
- optionally build or write the RDP display summary

Console text is not the only evidence. Structured reports and artifacts are the
reviewable output surfaces.

## Contracts And Invariants

- `RunSpec` owns durable run inputs when supplied.
- Direct `RunAPI.run(...)` arguments are normalised before core runtime.
- Seed defaults are deterministic; omitted solver seed becomes an effective
  seed of `0` in the engine path.
- The solver searches candidate keys.
- The cipher transforms text for a supplied key.
- The scorer ranks candidate plaintext.
- Reports explain what happened.
- Known truth or oracle data must be visible when used.
- Diagnostic/report-only fields must not silently affect ranking or stopping.
- Paths exposed in reports/artifacts should be repo-relative, run-relative, or
  display-safe.

## Determinism Notes

- `RunAPI` and `EngineConfig` pass solver seeds into a NumPy generator.
- If a solver seed is not supplied, the engine uses `0` rather than entropy.
- Optional backends must report requested/effective behaviour clearly.
- Solver parameters are normalised before engine execution.
- Scorer caches are cleared after engine runs when the scorer supports it.

## Extension Notes

When adding a new runtime feature, decide which layer owns it:

| Change | Likely owner |
| --- | --- |
| New public run argument | `api/run.py`, plus docs and tests. |
| New durable run field | `RunSpec` and `run_spec_routing.py`. |
| New cipher option | `CipherSpec`, wrapper registry, `CipherConfig`, cipher tests. |
| New key family | `KeySpec`, `keyops/`, core enum/config, keyops tests. |
| New solver | `SolverSpec`, `solvers/`, engine solver table, solver/telemetry tests. |
| New scorer signal | `ScoringConfig`, scoring implementation, scorer report docs/tests. |
| New report artifact | artifact agreement, manifest writer, report docs/tests. |

## What Not To Rely On

- Private helpers such as `_run_normalized`.
- Exact console wording.
- Temporary output folder names.
- Test-only fixtures outside their documented boundary.
- `RunAPI.solve` as the preferred spelling; it is a retained compatibility
  alias for V1, not the canonical entry point.
