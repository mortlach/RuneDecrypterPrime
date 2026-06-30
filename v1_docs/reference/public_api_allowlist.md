# Public API Allowlist

Status: staged V1 draft

Owner paths:
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

Stability:
- Public V1 surface

## Purpose

This table is the first narrow public API allowlist for V1 coder docs. It is
intended to be machine-checkable and conservative. Expand it only after
inspection.

| Import path | Stability | Notes |
| --- | --- | --- |
| `rune_decrypter_prime.api.run.RunAPI` | Public V1 surface | Canonical high-level run entry point. |
| `rune_decrypter_prime.api.run.run` | Public V1 surface | Convenience wrapper around `RunAPI.run`. |
| `rune_decrypter_prime.api.run.solve` | Legacy / transitional | Compatibility alias; prefer `run`. |
| `rune_decrypter_prime.api.run_spec.RawTextInput` | Public V1 surface | Raw text input contract. |
| `rune_decrypter_prime.api.run_spec.NormalizedInput` | Public V1 surface | Validated rune-token input contract. |
| `rune_decrypter_prime.api.run_spec.SourceInputRef` | Public V1 surface | Built-in source reference contract. |
| `rune_decrypter_prime.api.run_spec.RunSpec` | Public V1 surface | Run request contract. |
| `rune_decrypter_prime.api.specs.CipherSpec` | Public V1 surface | Declarative cipher builder/specification. |
| `rune_decrypter_prime.api.specs.KeySpec` | Public V1 surface | Declarative key builder/specification. |
| `rune_decrypter_prime.api.specs.SolverSpec` | Public V1 surface | Declarative solver builder/specification. |
| `rune_decrypter_prime.api.run_result.RunResult` | Public V1 surface | Solution plus solver report result wrapper. |
| `rune_decrypter_prime.api.solver_report.SolverReport` | Public V1 surface | Solver evidence and reproducibility report. |
| `rune_decrypter_prime.api.solver_report.build_solver_report` | Public V1 surface | Solver report builder with generated contract details. |
| `rune_decrypter_prime.scoring.scorer_report.ScorerReport` | Public V1 surface | Scorer objective, score, telemetry, and details report. |
| `rune_decrypter_prime.api.run_artifact_manifest.RunArtifactManifestRow` | Public V1 surface | One V1 run artifact manifest row. |
| `rune_decrypter_prime.api.run_artifact_manifest.write_run_artifacts_manifest` | Public V1 surface | V1 run artifact manifest writer. |
| `rune_decrypter_prime.api.display.RdpDisplayOptions` | Public V1 surface | Controls standard display-summary content. |
| `rune_decrypter_prime.api.display.RdpDisplaySummary` | Public V1 surface | JSON-safe display/share view of a run. |
| `rune_decrypter_prime.api.display.build_rdp_summary` | Public V1 surface | Builds the standard display summary. |
| `rune_decrypter_prime.api.display.format_rdp_summary` | Public V1 surface | Renders the standard display summary as text. |
| `rune_decrypter_prime.api.display.write_rdp_summary_json` | Public V1 surface | Writes display-summary JSON and returns a relative path. |
| `rune_decrypter_prime.api.printer.RdpPrintOptions` | Public V1 surface | Controls shared console formatting. |
| `rune_decrypter_prime.api.printer.print_rdp_result` | Public V1 surface | Builds, prints, and returns a display summary. |
| `rune_decrypter_prime.api.printer.render_rdp_summary` | Public V1 surface | Renders a display summary as text or JSON. |
| `rune_decrypter_prime.api.printer.write_rdp_summary_artifact` | Public V1 surface | Writes the display summary artifact and returns a relative path. |
| `rune_decrypter_prime.api.wrappers.by_name.by_name` | Public V1 surface | Friendly by-name cipher wrapper facade. |
| `rune_decrypter_prime.api.wrappers.by_name.cipher_instance` | Public V1 surface | Materialises cipher instances from names/specs. |
| `rdp.api` | Public V1 surface | Lightweight short alias for `rune_decrypter_prime.api`. |

## Non-Goals

This file does not list every importable helper. Private validation helpers,
runtime builders, and test-only helpers remain internal unless they are added to
this table deliberately.
