# Public API Boundary

Status: staged V1 draft

Owner paths:
- `src/rune_decrypter_prime/api/__init__.py`
- `src/rune_decrypter_prime/api/run.py`
- `src/rune_decrypter_prime/api/run_spec.py`
- `src/rune_decrypter_prime/api/specs.py`
- `src/rune_decrypter_prime/api/run_result.py`
- `src/rune_decrypter_prime/api/solver_report.py`
- `src/rune_decrypter_prime/api/display.py`
- `src/rune_decrypter_prime/api/printer.py`
- `src/rune_decrypter_prime/api/wrappers/by_name.py`
- `src/rune_decrypter_prime/scoring/scorer_report.py`
- `src/rune_decrypter_prime/api/run_artifact_manifest.py`
- `src/rdp/__init__.py`

Related tests:
- `tests/docs/test_v1_coder_docs_contract.py`
- `tests/api/`
- `tests/api_contract/`
- `tests/contracts/`
- `tests/scoring/`

Stability:
- Public V1 surface

## Purpose

This page defines the intended public support boundary for the first coder-docs
slice. It does not mean every importable helper in these modules is public.

Generated docs, if added later, should reflect this boundary rather than expose
every helper by accident.

## Stability Labels

| Label | Meaning |
| --- | --- |
| Public V1 surface | Intended for users, tutorials, reports, or stable integration. |
| Semi-stable contributor surface | Useful for contributors, but not a broad user promise. |
| Internal helper | Implementation detail; do not rely on it from outside the owning layer. |
| Test-only helper | Exists for tests or tutorial verification. |
| Legacy / transitional | Kept for compatibility or migration only. |

## Initial Public Surfaces

The machine-checkable allowlist lives in `reference/public_api_allowlist.md`.
This narrative explains why the first entries are included.

| Surface | Import path | Owning file | Purpose |
| --- | --- | --- | --- |
| Run API class | `rune_decrypter_prime.api.run.RunAPI` | `src/rune_decrypter_prime/api/run.py` | Canonical high-level run entry point. |
| Run API method | `rune_decrypter_prime.api.run.RunAPI.run` | `src/rune_decrypter_prime/api/run.py` | Runs one decryption attempt from explicit inputs or a `RunSpec`. |
| Run convenience function | `rune_decrypter_prime.api.run.run` | `src/rune_decrypter_prime/api/run.py` | Function wrapper around `RunAPI.run`. |
| Legacy solve alias | `rune_decrypter_prime.api.run.RunAPI.solve` | `src/rune_decrypter_prime/api/run.py` | Retained V1 compatibility alias; prefer `RunAPI.run`. |
| Raw text input | `rune_decrypter_prime.api.run_spec.RawTextInput` | `src/rune_decrypter_prime/api/run_spec.py` | Holds non-empty source text before runtime normalisation. |
| Normalised input | `rune_decrypter_prime.api.run_spec.NormalizedInput` | `src/rune_decrypter_prime/api/run_spec.py` | Holds validated rune-token indices and optional word-location information. |
| Source input reference | `rune_decrypter_prime.api.run_spec.SourceInputRef` | `src/rune_decrypter_prime/api/run_spec.py` | Refers to a built-in source such as Liber Primus without embedding raw text. |
| Run specification | `rune_decrypter_prime.api.run_spec.RunSpec` | `src/rune_decrypter_prime/api/run_spec.py` | Describes what RDP was asked to run. |
| Cipher specification | `rune_decrypter_prime.api.specs.CipherSpec` | `src/rune_decrypter_prime/api/specs.py` | Describes the cipher transform or wrapper choice. |
| Key specification | `rune_decrypter_prime.api.specs.KeySpec` | `src/rune_decrypter_prime/api/specs.py` | Describes the key shape or keystream plan. |
| Solver specification | `rune_decrypter_prime.api.specs.SolverSpec` | `src/rune_decrypter_prime/api/specs.py` | Describes the solver family, parameters, and seed. |
| Run result | `rune_decrypter_prime.api.run_result.RunResult` | `src/rune_decrypter_prime/api/run_result.py` | Pairs a solution object with a `SolverReport`. |
| Solver report | `rune_decrypter_prime.api.solver_report.SolverReport` | `src/rune_decrypter_prime/api/solver_report.py` | Records solver search evidence and reproducibility details. |
| Solver report builder | `rune_decrypter_prime.api.solver_report.build_solver_report` | `src/rune_decrypter_prime/api/solver_report.py` | Semi-stable contributor helper that builds a solver report with generated contract detail sections. |
| Scorer report | `rune_decrypter_prime.scoring.scorer_report.ScorerReport` | `src/rune_decrypter_prime/scoring/scorer_report.py` | Records scoring objective, score, metrics, telemetry, and details. |
| Run artifact manifest row | `rune_decrypter_prime.api.run_artifact_manifest.RunArtifactManifestRow` | `src/rune_decrypter_prime/api/run_artifact_manifest.py` | Describes one artifact row in the V1 run artifact manifest. |
| Run artifact manifest writer | `rune_decrypter_prime.api.run_artifact_manifest.write_run_artifacts_manifest` | `src/rune_decrypter_prime/api/run_artifact_manifest.py` | Semi-stable contributor/logging helper that writes the V1 run artifact manifest for a run directory. |
| Display options | `rune_decrypter_prime.api.display.RdpDisplayOptions` | `src/rune_decrypter_prime/api/display.py` | Controls the standard RDP display/share view. |
| Display summary | `rune_decrypter_prime.api.display.RdpDisplaySummary` | `src/rune_decrypter_prime/api/display.py` | JSON-safe standard display/share view of a run. |
| Display builder | `rune_decrypter_prime.api.display.build_rdp_summary` | `src/rune_decrypter_prime/api/display.py` | Builds a standard display summary without changing solver/scorer behaviour. |
| Display formatter | `rune_decrypter_prime.api.display.format_rdp_summary` | `src/rune_decrypter_prime/api/display.py` | Renders a standard display summary as text. |
| Display JSON writer | `rune_decrypter_prime.api.display.write_rdp_summary_json` | `src/rune_decrypter_prime/api/display.py` | Writes display-summary JSON and returns a display-safe relative path. |
| Printer options | `rune_decrypter_prime.api.printer.RdpPrintOptions` | `src/rune_decrypter_prime/api/printer.py` | Controls shared human console formatting. |
| Result printer | `rune_decrypter_prime.api.printer.print_rdp_result` | `src/rune_decrypter_prime/api/printer.py` | Builds, prints, and returns a standard display summary. |
| Summary renderer | `rune_decrypter_prime.api.printer.render_rdp_summary` | `src/rune_decrypter_prime/api/printer.py` | Renders an RDP display summary as text or JSON. |
| Summary artifact writer | `rune_decrypter_prime.api.printer.write_rdp_summary_artifact` | `src/rune_decrypter_prime/api/printer.py` | Writes the display summary under a run directory and returns a relative artifact path. |
| By-name wrapper facade | `rune_decrypter_prime.api.wrappers.by_name.by_name` | `src/rune_decrypter_prime/api/wrappers/by_name.py` | Friendly cipher wrapper/spec factory used by tutorials and examples. |
| Cipher instance helper | `rune_decrypter_prime.api.wrappers.by_name.cipher_instance` | `src/rune_decrypter_prime/api/wrappers/by_name.py` | Semi-stable contributor helper that materialises a cipher instance from a friendly name or spec. |

## Import Routes

Canonical import paths use the owning modules listed above. The package
`rune_decrypter_prime.api` also re-exports a friendly surface for tutorials and
examples.

Preferred examples:

```python
from rune_decrypter_prime.api import RunAPI, RunSpec, CipherSpec, KeySpec, SolverSpec
from rune_decrypter_prime.api import by_name, cipher_instance
from rune_decrypter_prime.api.display import build_rdp_summary
```

Short alias:

```python
from rdp import api
```

`src/rdp/` is a lightweight import alias. It should stay import-only and should
not gain solver, scorer, cipher, or filesystem behaviour.

### Specialised two-period crib route

`api.SolverSpec.two_period_cribs(...)` and `api.run(...)` provide the V1 public
route for additive two-period scheduled-stream problems. The friendly
`api.by_name.cipher_with_key("two_period_vigenere", ..., default_key=True)`
builder supplies the canonical A-then-B key shape. See
`docs/release_contracts/v1/WP7_TWO_PERIOD_CRIBS.md` for the complete supported
option boundary.

## Compatibility Surfaces

| Surface | Status | Rule |
| --- | --- | --- |
| `RunAPI.solve` | Legacy / transitional | Retained for V1 compatibility. Prefer `RunAPI.run`; removal requires deprecation-ledger and test updates. |
| `rune_decrypter_prime.api.run.solve` | Legacy / transitional | Free-function alias for compatibility. Prefer `rune_decrypter_prime.api.run.run`. |
| Friendly `rune_decrypter_prime.api` re-exports | Public V1 surface | Stable enough for tutorials, but canonical docs should still name owning modules. |
| Private helpers with leading underscore | Internal helper | Do not import from outside the owning module. |

## RunSpec Fields

These fields are documented here so a docs-contract test can detect drift.

| Field | Purpose |
| --- | --- |
| `problem_input` | Raw text, normalised token data, or a source reference. |
| `cipher` | Declarative cipher specification. |
| `key` | Declarative key specification, or a two-part key specification. |
| `solver` | Declarative solver specification. |
| `scorer` | Scorer family name. |
| `scorer_params` | JSON-primitive scorer parameter mapping. |
| `logging` | Optional logging configuration. |
| `encoding_dir` | Text encoding direction used when plaintext is interpreted. |
| `device` | Requested execution device. |
| `telemetry_on` | Whether runtime telemetry is enabled. |

## Boundary Notes

- Private helpers in the owning files are not public API.
- Exact console wording is not a public API.
- Test helpers are not public unless explicitly documented.
- Report-only diagnostics can explain a run but must not silently affect
  ranking, stopping, tie-breaks, or candidate selection.
