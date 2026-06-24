# Outputs

Status: staged V1 draft

RDP writes human review output and generated run files under `output/` by
default. That folder is local runtime output. It is not source code and should
not be treated as documentation to commit.

## Beginner Output Folders

The simple V1 path uses these folders:

| Folder | What writes it |
| --- | --- |
| `output/install_logs/` | `python install.py` |
| `output/tutorial_pretty_print_logs/` | `python tutorials/v1/run_pretty_print_release.py` |
| `output/tutorial_pretty_print_output_review_logs/` | `python tutorials/v1/run_pretty_print_output_review.py` |

Install logs capture each installer step. Tutorial logs capture the complete
printout from each tutorial file.

## Console Output

The normal tutorial runner prints compact review lines:

```text
[RUN ] Tutorial_Autokey.py
[PASS] Tutorial_Autokey.py match_ratio=1.000 min=1.000 log=output/tutorial_pretty_print_logs/Tutorial_Autokey.txt
```

The final summary is the main beginner signal:

```text
Pretty-print summary
selected=21 run=21 passed=21 failed=0
```

For V1 release review, `failed=0` is the important part.

## Tutorial Logs

Tutorial logs are plain text. A good tutorial printout shows:

- what problem is being solved
- `encoding_dir`
- cipher and solver
- truth/oracle use when present
- match ratio or acceptance result
- recovered key or key preview
- warnings
- artifact or log paths when written

The output-review runner prints the same captured tutorial text to the console,
which makes it easier to compare formatting across tutorials.

## Standard RDP Summary

The API display layer can build a standard summary for a run. Its compact text
starts like this:

```text
RDP standard summary
====================
schema: api_display_summary.v1
encoding_dir: rtl
cipher: ...
solver: ...
```

The standard summary is meant for inspection, sharing, tutorials, examples, and
future GUI/report consumers. It is not a full solver-state save file.

## JSON Display Summary

When written, the display summary uses this run-relative path:

```text
artifacts/rdp_display_summary.json
```

It is JSON-safe and avoids absolute local paths in display output. It can
include problem, cipher, key, solver, scoring, result, report, telemetry, stop,
oracle, tutorial, LP evidence, artifacts, and warnings sections.

## Run Artifact Manifest

Some API runs can write a small manifest:

```text
artifacts/run_artifacts_manifest.json
```

The manifest records which known V1 artifacts are present. The current known
artifact paths are:

| Path | Kind | Required in manifest agreement |
| --- | --- | --- |
| `META.json` | run metadata | yes |
| `config/logging.json` | logging configuration | yes |
| `artifacts/solver_report.json` | solver report | no |
| `artifacts/rdp_display_summary.json` | display summary | no |
| `artifacts/run_artifacts_manifest.json` | manifest document | yes |

The manifest is for review/export hygiene. It does not make generated files part
of the source tree.

## Path Policy

Public docs and display output prefer repo-relative or run-relative
paths. Absolute machine paths are local details and should not appear in
committed documentation.
