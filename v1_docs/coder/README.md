# Core Coder Docs

Status: staged V1 draft

Owner paths:
- `src/rdp/`
- `tests/`
- `tutorials/v1/`

Related tests:
- `tests/docs/test_v1_coder_docs_contract.py`

Stability:
- Semi-stable contributor surface

## Purpose

This lane is for people reading, reviewing, or changing the RDP core code.

It explains the package map, public support boundary, run flow, extension
points, and the contract-backed behaviour that should not silently drift.

These pages do not replace beginner docs. The beginner path stays short and
runnable. These pages are allowed to be more exact.

## Pages

| Page | Purpose | Status |
| --- | --- | --- |
| `module_map.md` | Map the core packages and related tests. | Started. |
| `public_api.md` | Explain the intended public V1 boundary. | Started. |
| `docstring_policy.md` | Set the rule for future code annotations. | Started. |
| `run_flow.md` | Explain input to report lifecycle. | Started. |
| `config_objects.md` | Explain typed run/spec/config objects. | Started. |
| `cipher_pipeline.md` | Explain cipher layer ownership and extension points. | Started. |
| `key_pipeline.md` | Explain key/keyops ownership and extension points. | Started. |
| `solver_pipeline.md` | Explain solver search ownership and determinism risks. | Started. |
| `scoring_pipeline.md` | Explain ranking, diagnostics, and scorer contracts. | Started. |
| `telemetry_and_reports.md` | Explain runtime evidence surfaces. | Started. |
| `extension_points.md` | Summarise supported contributor extension points. | Started. |
| `stability_and_internals.md` | List what not to rely on. | Started. |

## Rules

- Do not document every importable helper as public API.
- Label support level explicitly.
- Mark uninspected packages as `Status: not yet assessed`.
- Use repo-relative paths.
- Keep generated docs output outside the repo.
- Prefer tested tables and exact import paths over broad prose.
