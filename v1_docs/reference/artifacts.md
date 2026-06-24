# Artifacts Reference

Status: staged V1 draft

Owners:

```text
src/rune_decrypter_prime/api/artifact_agreement.py
src/rune_decrypter_prime/api/run_artifact_manifest.py
```

## Known Artifact Paths

| Path | Kind | Required |
| --- | --- | --- |
| `META.json` | `run_meta` | yes |
| `config/logging.json` | `logging_config` | yes |
| `artifacts/solver_report.json` | `solver_report` | no |
| `artifacts/rdp_display_summary.json` | `rdp_display_summary` | no |
| `artifacts/run_artifacts_manifest.json` | `run_artifacts_manifest` | yes |

Paths are run-relative and use POSIX separators.

## Classifications

Known classifications are:

| Classification | Meaning |
| --- | --- |
| `candidate` | Can be considered for review/export. |
| `not_candidate` | Should not be exported as a review artifact. |
| `needs_review` | Not known; a human must decide. |

Unregistered output under logs, traces, caches, assets, or output-style folders
is not a candidate by default.

## Manifest

The run artifact manifest schema is:

```text
api_run_artifacts.v1
```

The manifest records which known artifacts are present in one run. It does not
make generated output part of the source tree.

## Path Rules

Artifact paths must:

- be non-empty
- be run-relative
- stay under the run directory
- use `/` separators
- not contain `..`

These rules protect release bundles from leaking local machine paths.
