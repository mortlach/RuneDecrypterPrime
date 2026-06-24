# Runs, Reports, And Artifacts

Status: staged V1 draft

RDP separates the recipe for a run, the result of a run, the explanation of how
the solver behaved, and any files written for review.

That separation is one of the main V1 design choices.

## The Short Version

| Surface | What it is |
| --- | --- |
| `RunSpec` | The typed recipe for a run. |
| `RunResult` | The returned solution plus a `SolverReport`. |
| `SolverReport` | The solver's reproducibility, stop, key, timing, and truth/oracle report. |
| `ScorerReport` | A JSON-safe explanation of a scoring call. |
| RDP display summary | A compact human/share view of a run. |
| Run artifacts | Optional files written under a run directory for review. |

## RunSpec

`RunSpec` is the strict input contract for a run.

It contains:

- problem input
- cipher spec
- key spec
- solver spec
- scorer name and scorer parameters
- logging config
- encoding direction
- device
- telemetry flag

Problem input can be:

- `RawTextInput`
- `NormalizedInput`
- `SourceInputRef`

`RawTextInput` is a direct text input. `NormalizedInput` is already converted to
rune indices, with optional word-length index data. `SourceInputRef` points to a
known source such as a Liber Primus label, locator, or partition.

`RunSpec` is intentionally strict. It rejects unsupported types early so that
bad setup does not turn into a mysterious solver result later.

## RunResult

`RunResult` is deliberately small:

```text
solution
solver_report
```

It is not meant to duplicate the whole `RunSpec`, every scorer detail, or every
artifact path. When a display summary needs complete problem/cipher/key context,
the caller passes the original `RunSpec` into the display builder.

## SolverReport

`SolverReport` records how the solver run behaved.

It can include:

- solver name
- requested seed
- effective seed
- normalized solver parameters
- stop reason
- best score
- best key
- step/evaluation/token counts
- wall/decrypt/score timings
- JSON-safe details

The generated details section owns important V1 contract fields:

- `report_contract`
- `oracle_use`
- `truth_data_policy`
- `reproducibility`
- `execution_route`
- `scorer_lanes`

Callers cannot overwrite the generated contract sections. That protects the
report from quietly hiding truth-data use or reproducibility details.

## Truth And Oracle Data

Truth data can be useful in tutorials and tests. It must be reported.

For example, a tutorial may use a known key, a test key, or an oracle stop score
to teach a specific idea. That is allowed only when the report makes it visible.

The important rule:

```text
truth/oracle data may explain or stop a tutorial, but it must not quietly affect production ranking
```

## ScorerReport

`ScorerReport` explains one scoring result.

It contains:

- objective string
- objective spec
- score
- optional raw score
- telemetry
- metrics
- cost in milliseconds
- details

The report is JSON-safe. Non-finite numbers and unsafe path values are rejected
or normalised before export.

## RDP Display Summary

The display summary is the human/share layer.

It can show:

- schema
- problem summary
- `encoding_dir`
- cipher
- key
- solver
- scoring
- result preview
- solver report
- scorer report
- telemetry
- stop reason
- oracle/truth-data policy
- tutorial metadata
- LP evidence metadata
- artifacts
- warnings

This layer is for inspection and communication. It is not a persistence format
for resuming a solver search.

## Artifacts

Artifacts are optional files written for review. Known V1 paths include:

| Path | Meaning |
| --- | --- |
| `META.json` | run metadata |
| `config/logging.json` | logging configuration snapshot |
| `artifacts/solver_report.json` | solver report sidecar |
| `artifacts/rdp_display_summary.json` | display/share summary |
| `artifacts/run_artifacts_manifest.json` | manifest of known artifacts present |

The manifest records which known artifacts exist for a run and how they are
be reviewed or exported.

Generated output stays under `output/` or a run output directory. Do not
turn generated logs, caches, benchmark files, or local review bundles into
source documentation.

## What This Buys Us

This structure makes RDP easier to review:

- inputs are explicit
- output is small
- solver behavior is inspectable
- scoring can explain itself
- truth/oracle use is visible
- display is readable
- generated files have review rules

That is the core V1 promise: not that every solve is easy, but that RDP is
honest about what it did.
